"""Frozen offline evaluation. Lexical diagnostics are never semantic support scores."""

import hashlib
import html
import json
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from studio_copilot.documents.operations import current, instrument
from studio_copilot.documents.operations.runtime import generation_estimate, preflight, submit

from .contracts import Candidate, GenerationError, Verification
from .engine import answer, paired, require_api
from .evidence import hash_value, load_artifact
from .prepare import CASES_SHA256, load_cases
from .provider import GENERATE, PROMPT_VERSION, VERIFY


def markdown_text(value):
    """Show source/model text as text, without executable HTML or Markdown links."""
    escaped = html.escape(str(value), quote=False).replace("\\", "\\\\")
    return re.sub(r"([`*_{}\[\]()#+!|])", r"\\\1", escaped)


def readable_answer(result):
    lines = [
        markdown_text(result["answer"] or "Technical failure; no answer released."),
        "",
        "Metadata reason: " + markdown_text(result.get("reason_code")),
        "Metadata missing_information (not part of answer): "
        + markdown_text(json.dumps(result.get("missing_information", []), ensure_ascii=False)),
        "",
    ]
    for claim in result["claims"]:
        for citation in claim["citations"]:
            lines.append(
                "- "
                + markdown_text(
                    f"{citation['evidence_id']}: {citation['document_id']} "
                    f"revision {citation['revision']} "
                    f"chunk {citation['chunk_id']} [{citation['start']}, {citation['end']}); "
                    f"valid {citation['effective_from']} through {citation['effective_to']}; "
                    f"SHA-256 {citation['sha256']}; quote: {citation['quote']}"
                )
            )
    return "\n".join(lines) + "\n"


def save(path, value):
    if (
        current()
        and isinstance(value, dict)
        and Path(path).name in {"manifest.json", "plan.json", "comparison.json", "selection.json"}
    ):
        if Path(path).name != "plan.json" or "operations" not in value:
            value["operations"] = current().budget.snapshot()
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected_inputs(evidence_dir, tokenizer, *, split=None, limit=None):
    directory = Path(evidence_dir)
    manifest = json.loads((directory / "manifest.json").read_text())
    labels = load_cases()
    cases = {c["id"]: c for c in labels["cases"]}
    index = manifest["artifacts"]
    if (
        not manifest.get("complete")
        or manifest.get("cases_sha256") != CASES_SHA256
        or manifest.get("index_sha256") != hash_value(index)
    ):
        raise GenerationError("invalid_evidence_set", "Evidence manifest or frozen labels differ.")
    identities = {(item["case_id"], item["variant"]) for item in index}
    if len(index) != 2 * len(cases) or identities != {
        (identifier, variant) for identifier in cases for variant in ("actual", "standard")
    }:
        raise GenerationError("invalid_evidence_set", "Evidence set is incomplete or duplicated.")
    if split not in {None, "tuning", "held_out"} or (limit is not None and limit < 1):
        raise GenerationError("invalid_selection", "Invalid split or positive case limit.")
    identifiers = [c["id"] for c in labels["cases"] if split is None or c["split"] == split]
    if limit is not None:
        identifiers = identifiers[:limit]
    selected = set(identifiers)
    output = []
    for item in index:
        filename = item["file"]
        if Path(filename).name != filename:
            raise GenerationError("invalid_evidence_set", "Evidence filename must be local.")
        # Validate every artifact before any model call, including unselected records.
        artifact = load_artifact(directory / filename, tokenizer)
        case = cases[item["case_id"]]
        if (
            artifact["case_id"] != item["case_id"]
            or artifact["variant"] != item["variant"]
            or artifact["artifact_sha256"] != item["artifact_sha256"]
            or artifact["question"] != case["question"]
            or artifact["as_of"] != case["as_of"]
        ):
            raise GenerationError(
                "invalid_evidence_set", "Evidence question/source identity differs."
            )
        if case["id"] in selected:
            output.append((case, artifact))
    return output


@instrument("generation")
def plan(evidence_dir, tokenizer, *, split=None, limit=None, compare_verification=False):
    inputs = selected_inputs(evidence_dir, tokenizer, split=split, limit=limit)
    active = [(c, a) for c, a in inputs if a["blocks"]]
    from .evidence import model_payload

    tokens = sum(generation_estimate(GENERATE, model_payload(a), Candidate) for _, a in active)

    return dict(
        artifacts=len(inputs),
        questions=len({c["id"] for c, _ in inputs}),
        no_evidence=len(inputs) - len(active),
        generation_requests=len(active),
        verification_requests_max=len(active) if compare_verification else 0,
        estimated_generation_input_tokens=tokens,
        verification_input_tokens_note="Evidence plus generated candidate; known after generation.",
        output_tokens_limit_per_request=4000,
        split=split,
        limit=limit,
        model_requests=False,
        operations=preflight(
            len(active) * (2 if compare_verification else 1),
            tokens,
            4000 * len(active) * (2 if compare_verification else 1),
        ),
        prompt_version=PROMPT_VERSION,
        prompt_sha256=hash_value([GENERATE, VERIFY]),
    )


def diagnostic(case, result, variant):
    completed = result["execution_status"] == "completed"
    expected = (
        case.get("expected_actual_status", case["expected_standard_status"])
        if variant == "actual"
        else case["expected_standard_status"]
    )
    text = "\n".join(c["text"] for c in result["claims"])
    facts = case["required_facts"]
    matched = sum(
        all(
            any(re.search(pattern, text, re.I) for pattern in alternatives)
            for alternatives in fact["patterns"]
        )
        for fact in facts
    )
    forbidden = [pattern for pattern in case["forbidden_patterns"] if re.search(pattern, text)]
    return dict(
        expected_status=expected,
        status_matches_label=completed and result["status"] == expected,
        lexical_fact_matches=matched,
        required_facts=len(facts),
        required_fact_ids=[fact.get("id", f"f{index + 1}") for index, fact in enumerate(facts)],
        lexical_fact_coverage=matched / len(facts) if facts else None,
        forbidden_pattern_matches=forbidden,
        semantic_support=None,
        semantic_review_status="unreviewed",
    )


def summarize(records, *, adjudication=None, results_sha256=None):
    reviews = {}
    if adjudication is not None:
        if adjudication.get("results_sha256") != results_sha256 or not adjudication.get("reviewer"):
            raise GenerationError(
                "invalid_review", "Review must identify its reviewer and exact results hash."
            )
        for item in adjudication["reviews"]:
            identity = (item["case_id"], item["variant"], item["path"])
            if identity in reviews:
                raise GenerationError("invalid_review", "Duplicate independent review.")
            reviews[identity] = item
        expected = {(r["case_id"], r["variant"], r["path"]) for r in records}
        if set(reviews) != expected:
            raise GenerationError("invalid_review", "Review must cover every result exactly once.")
    groups = {}
    for record in records:
        key = f"{record['split']}/{record['variant']}/{record['path']}"
        groups.setdefault(key, []).append(record)
    output = {}
    for key, rows in groups.items():
        completed = [r for r in rows if r["result"]["execution_status"] == "completed"]
        factual = [r for r in rows if r["diagnostic"]["required_facts"]]
        citations = [r["result"].get("citation_counts", dict(valid=0, total=0)) for r in rows]
        total_quotes = sum(c["total"] for c in citations)
        retained_quotes = sum(
            len(claim.get("citations", [])) for row in rows for claim in row["result"]["claims"]
        )
        answerable = [r for r in rows if r["diagnostic"]["expected_status"] == "answered"]
        refusals = [r for r in rows if r["diagnostic"]["expected_status"] == "abstained"]
        metrics = dict(
            cases=len(rows),
            technical_failures=len(rows) - len(completed),
            citation_validity=sum(c["valid"] for c in citations) / total_quotes
            if total_quotes
            else None,
            citation_counts=dict(valid=sum(c["valid"] for c in citations), total=total_quotes),
            generated_citation_validity=sum(c["valid"] for c in citations) / total_quotes
            if total_quotes
            else None,
            generated_citation_counts=dict(
                valid=sum(c["valid"] for c in citations), total=total_quotes
            ),
            final_citation_validity=1.0 if retained_quotes else None,
            final_citation_counts=dict(valid=retained_quotes, total=retained_quotes, invalid=0),
            citation_metric_note=(
                "citation_validity is the generated-before-pruning legacy alias. "
                "Final retained quotes are valid by deterministic construction; "
                "semantic support is separate."
            ),
            diagnostic_status_accuracy=sum(r["diagnostic"]["status_matches_label"] for r in rows)
            / len(rows),
            diagnostic_required_fact_coverage=sum(
                r["diagnostic"]["lexical_fact_matches"] for r in factual
            )
            / sum(r["diagnostic"]["required_facts"] for r in factual)
            if factual
            else None,
            diagnostic_correct_abstention=sum(
                r["diagnostic"]["status_matches_label"] for r in refusals
            )
            / len(refusals)
            if refusals
            else None,
            diagnostic_false_abstention=sum(
                r["result"]["status"] == "abstained" for r in answerable
            )
            / len(answerable)
            if answerable
            else None,
            diagnostic_complete_answer=sum(
                r["diagnostic"]["status_matches_label"] for r in answerable
            )
            / len(answerable)
            if answerable
            else None,
            forbidden_pattern_cases=sum(
                bool(r["diagnostic"]["forbidden_pattern_matches"]) for r in rows
            ),
            semantic_support_rate=None,
            semantic_required_fact_coverage=None,
            semantic_complete_answer_rate=None,
            semantic_appropriate_status_rate=None,
            semantic_review_status="unreviewed",
        )
        if adjudication is not None:
            supported = total = complete_answers = appropriate = correct_refusals = (
                wrong_refusals
            ) = 0
            facts_supported = facts_total = factual_complete = 0
            all_facts_reviewed = True
            for row in rows:
                review = reviews[(row["case_id"], row["variant"], row["path"])]
                claims = {c["id"] for c in row["result"]["claims"]}
                if (
                    set(review["claims"]) != claims
                    or any(type(v) is not bool for v in review["claims"].values())
                    or type(review["complete_answer"]) is not bool
                    or type(review["appropriate_status"]) is not bool
                ):
                    raise GenerationError(
                        "invalid_review", "Review claim identities or boolean judgments differ."
                    )
                if row["result"]["execution_status"] != "completed" and (
                    review["complete_answer"]
                    or review["appropriate_status"]
                    or any(review.get("required_facts", {}).values())
                ):
                    raise GenerationError(
                        "invalid_review", "Technical failure cannot be graded as successful."
                    )
                fact_ids = set(
                    row["diagnostic"].get(
                        "required_fact_ids",
                        [f"f{i + 1}" for i in range(row["diagnostic"]["required_facts"])],
                    )
                )
                if "required_facts" in review:
                    if set(review["required_facts"]) != fact_ids or any(
                        type(v) is not bool for v in review["required_facts"].values()
                    ):
                        raise GenerationError(
                            "invalid_review", "Required fact judgments differ from frozen labels."
                        )
                    facts_supported += sum(review["required_facts"].values())
                elif fact_ids:
                    all_facts_reviewed = False
                facts_total += len(fact_ids)
                supported += sum(review["claims"].values())
                total += len(claims)
                okay = row["result"]["execution_status"] == "completed"
                appropriate += okay and review["appropriate_status"]
                if row in answerable:
                    factual = (
                        okay
                        and review["complete_answer"]
                        and all(review["claims"].values())
                        and (not fact_ids or "required_facts" in review)
                        and all(review.get("required_facts", {}).values())
                    )
                    factual_complete += factual
                    complete_answers += (
                        factual
                        and row["result"]["status"] == "answered"
                        and review["appropriate_status"]
                    )
                    wrong_refusals += (
                        okay
                        and row["result"]["status"] == "abstained"
                        and not review["appropriate_status"]
                    )
                if row in refusals:
                    correct_refusals += (
                        okay
                        and row["result"]["status"] == "abstained"
                        and review["appropriate_status"]
                    )
            metrics.update(
                semantic_support_rate=supported / total if total else None,
                semantic_support_counts=dict(supported=supported, total=total),
                semantic_complete_answer_counts=dict(
                    complete=complete_answers, total=len(answerable)
                ),
                semantic_correct_abstention_rate=correct_refusals / len(refusals)
                if refusals
                else None,
                semantic_correct_abstention_counts=dict(
                    correct=correct_refusals, total=len(refusals)
                ),
                semantic_false_abstention_rate=wrong_refusals / len(answerable)
                if answerable
                else None,
                semantic_false_abstention_counts=dict(wrong=wrong_refusals, total=len(answerable)),
                semantic_factual_completeness_rate=factual_complete / len(answerable)
                if answerable
                else None,
                semantic_complete_answer_rate=complete_answers / len(answerable)
                if answerable
                else None,
                semantic_appropriate_status_rate=appropriate / len(rows),
                semantic_review_status="independently_reviewed",
                semantic_required_fact_coverage=facts_supported / facts_total
                if all_facts_reviewed and facts_total
                else None,
                semantic_required_fact_counts=dict(
                    covered=facts_supported, total=facts_total, complete_review=all_facts_reviewed
                ),
            )
        criteria = dict(
            no_technical_failures=metrics["technical_failures"] == 0,
            semantic_support=metrics["semantic_support_rate"] >= 0.95
            if metrics["semantic_support_rate"] is not None
            else None,
            complete_answer=metrics["semantic_complete_answer_rate"] >= 0.9
            if "/standard/" in key and metrics["semantic_complete_answer_rate"] is not None
            else None,
            correct_abstention=metrics.get("semantic_correct_abstention_rate") >= 0.95
            if metrics.get("semantic_correct_abstention_rate") is not None
            else None,
            false_abstention=metrics.get("semantic_false_abstention_rate") <= 0.1
            if metrics.get("semantic_false_abstention_rate") is not None
            else None,
        )
        applicable = [
            value
            for name, value in criteria.items()
            if name != "complete_answer" or "/standard/" in key
        ]
        metrics["quality_targets"] = dict(
            criteria=criteria,
            passed=all(applicable) if all(v is not None for v in applicable) else None,
        )
        output[key] = metrics
    return output


def _write_report(directory, records, manifest):
    path = directory / "results.jsonl"
    if not path.exists():
        with path.open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    manifest["results_sha256"] = digest(path)
    manifest["summaries"] = summarize(records)
    manifest["technical_failures"] = sum(
        r["result"]["execution_status"] == "failed" for r in records
    )
    manifest["execution_status"] = "failed" if manifest["technical_failures"] else "completed"
    save(directory / "manifest.json", manifest)
    lines = [
        "# Offline generation evaluation",
        "",
        "Lexical metrics are diagnostic. Semantic support requires independent adjudication.",
        "",
    ]
    for row in records:
        result = row["result"]
        lines += [
            f"## {row['case_id']} / {row['variant']} / {row['path']}",
            "",
            f"Status: {result['status']}; execution: {result['execution_status']}",
            "",
            readable_answer(result),
            "",
        ]
    (directory / "report.md").write_text("\n".join(lines), encoding="utf-8")


def atomic_export(output_dir, callback, *, preserve_failure=False):
    output = Path(output_dir)
    if output.exists():
        raise GenerationError("output_exists", "Output already exists; choose a new directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".generation-", dir=output.parent))
    try:
        result = callback(temporary)
        if output.exists():
            raise GenerationError(
                "output_exists", "Output appeared during export; refusing overwrite."
            )
        temporary.rename(output)
        return result
    except BaseException:
        if preserve_failure and temporary.exists() and not output.exists():
            manifest_path = temporary / "manifest.json"
            try:
                interrupted = (
                    json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
                )
            except (OSError, ValueError):
                interrupted = {}
            interrupted["complete"] = False
            save(manifest_path, interrupted)
            save(
                temporary / "incomplete.json",
                dict(
                    complete=False,
                    reason="Interrupted or failed; completed records and usage are retained.",
                ),
            )
            temporary.rename(output)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


@instrument("generation")
def evaluate_directory(
    evidence_dir,
    output_dir,
    tokenizer,
    *,
    allow_api=False,
    compare_verification=False,
    split=None,
    limit=None,
    workers=1,
    provider_factory=None,
):
    require_api(allow_api)
    if type(workers) is not int or not 1 <= workers <= 8:
        raise GenerationError("invalid_workers", "Use between one and eight workers.")
    if Path(output_dir).exists():
        raise GenerationError("output_exists", "Output already exists; choose a new directory.")
    inputs = selected_inputs(evidence_dir, tokenizer, split=split, limit=limit)
    # Known one-shot lower bound; retries remain charged at the provider boundary.
    from .evidence import model_payload

    active = sum(bool(a["blocks"]) for _, a in inputs)
    estimated_input = sum(
        generation_estimate(GENERATE, model_payload(a), Candidate) for _, a in inputs if a["blocks"]
    )
    preflight(
        active * (2 if compare_verification else 1),
        estimated_input,
        active * (2 if compare_verification else 1) * 4000,
    )

    def run(item):
        case, artifact = item
        provider = provider_factory() if provider_factory else None
        if compare_verification:
            report = paired(artifact, tokenizer, allow_api=True, provider=provider)
        else:
            result = answer(artifact, tokenizer, allow_api=True, provider=provider)
            report = dict(
                baseline=result,
                calls=result["calls"],
                model=result["model"],
                seconds=result["seconds"],
                real_provider=provider is None and bool(artifact["blocks"]),
            )
        rows = []
        for branch in ("baseline", "verified") if compare_verification else ("baseline",):
            result = report[branch]
            rows.append(
                dict(
                    case_id=case["id"],
                    split=case["split"],
                    variant=artifact["variant"],
                    path=branch,
                    question=case["question"],
                    artifact_sha256=artifact["artifact_sha256"],
                    result=result,
                    provenance=artifact.get("provenance", {}),
                    diagnostic=diagnostic(case, result, artifact["variant"]),
                )
            )
        return rows, report

    def export(directory):
        records, reports = [], []
        save(
            directory / "manifest.json",
            dict(
                complete=False,
                cases_sha256=CASES_SHA256,
                prompt_sha256=hash_value([GENERATE, VERIFY]),
                schema_sha256=hash_value(
                    [Candidate.model_json_schema(), Verification.model_json_schema()]
                ),
            ),
        )
        with (
            (directory / "results.jsonl").open("w", encoding="utf-8") as result_stream,
            (directory / "reports.jsonl").open("w", encoding="utf-8") as report_stream,
        ):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [submit(pool, run, item) for item in inputs]
                written = set()

                def persist(future):
                    rows, report = future.result()
                    for row in rows:
                        result_stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    result_stream.flush()
                    report_stream.write(json.dumps(report, ensure_ascii=False) + "\n")
                    report_stream.flush()
                    records.extend(rows)
                    reports.append(report)
                    written.add(future)

                try:
                    for future in as_completed(futures):
                        persist(future)
                except BaseException:
                    # Stop unstarted paid work, let bounded in-flight calls finish,
                    # and retain their outcomes before propagating interruption.
                    for future in futures:
                        future.cancel()
                    pool.shutdown(wait=True, cancel_futures=True)
                    for future in futures:
                        if future not in written and not future.cancelled():
                            try:
                                persist(future)
                            except Exception:
                                pass
                    raise
        calls = [call for report in reports for call in report["calls"]]
        changes = dict(
            removed_claims=0, additional_abstentions=0, changed_cases=0, status_only_downgrades=0
        )
        if compare_verification:
            for report in reports:
                first, second = report["baseline"], report["verified"]
                changes["removed_claims"] += max(0, len(first["claims"]) - len(second["claims"]))
                changes["additional_abstentions"] += (
                    first["status"] != "abstained" and second["status"] == "abstained"
                )
                changes["changed_cases"] += (
                    first["status"] != second["status"] or first["claims"] != second["claims"]
                )
                changes["status_only_downgrades"] += (
                    first["status"] != second["status"]
                    and first["claims"] == second["claims"]
                    and second["execution_status"] == "completed"
                )
        operations = {}
        for operation in ("generate", "verify"):
            selected = [c for c in calls if c["operation"] == operation]
            durations = sorted(c["seconds"] for c in selected)
            operations[operation] = dict(
                requests=len(selected),
                failed=sum(not c["succeeded"] for c in selected),
                input_tokens=sum(c["input_tokens"] or 0 for c in selected),
                output_tokens=sum(c["output_tokens"] or 0 for c in selected),
                unknown_usage_calls=sum(c["input_tokens"] is None for c in selected),
                seconds=sum(durations),
                p50_seconds=durations[(len(durations) - 1) // 2] if durations else None,
                p95_seconds=durations[max(0, (95 * len(durations) + 99) // 100 - 1)]
                if durations
                else None,
            )
        manifest = dict(
            version="generation-evaluation-v1",
            complete=not current().budget.exhausted,
            cases_sha256=CASES_SHA256,
            prompt_version=PROMPT_VERSION,
            prompt_sha256=hash_value([GENERATE, VERIFY]),
            schema_sha256=hash_value(
                [Candidate.model_json_schema(), Verification.model_json_schema()]
            ),
            evidence_manifest_sha256=digest(Path(evidence_dir) / "manifest.json"),
            reports_sha256=digest(directory / "reports.jsonl"),
            split=split,
            limit=limit,
            workers=workers,
            compare_verification=compare_verification,
            real_provider=any(r["real_provider"] for r in reports),
            models=sorted({r["model"] for r in reports if r["model"]}),
            returned_models=sorted({c["returned_model"] for c in calls if c.get("returned_model")}),
            requests=len(calls),
            usage=dict(
                input_tokens=sum(c["input_tokens"] or 0 for c in calls),
                output_tokens=sum(c["output_tokens"] or 0 for c in calls),
                unknown_usage_calls=sum(c["input_tokens"] is None for c in calls),
            ),
            model_seconds=sum(c["seconds"] for c in calls),
            operation_usage=operations,
            paired_changes=changes,
            semantic_review_status="unreviewed",
            operations=current().budget.snapshot(),
            api_cost_note="Reported tokens; monetary pricing is not inferred.",
        )
        _write_report(directory, records, manifest)
        return manifest

    return atomic_export(output_dir, export, preserve_failure=True)


@instrument("generation")
def answer_directory(evidence_file, output_dir, tokenizer, *, allow_api=False, verify=False):
    require_api(allow_api)
    if Path(output_dir).exists():
        raise GenerationError("output_exists", "Output already exists; choose a new directory.")
    artifact = load_artifact(evidence_file, tokenizer)

    def export(directory):
        result = answer(artifact, tokenizer, allow_api=True, verify=verify)
        save(directory / "answer.json", result)
        (directory / "answer.md").write_text(readable_answer(result), encoding="utf-8")
        manifest = dict(
            complete=True,
            artifact_sha256=artifact["artifact_sha256"],
            verify=verify,
            execution_status=result["execution_status"],
            technical_failures=int(result["execution_status"] == "failed"),
            error_code=result.get("error_code"),
            answer_sha256=digest(directory / "answer.json"),
            prompt_version=PROMPT_VERSION,
        )
        save(directory / "manifest.json", manifest)
        return manifest

    return atomic_export(output_dir, export, preserve_failure=True)


def review_directory(results_dir, adjudication_file, output_dir):
    directory = Path(results_dir)
    manifest = json.loads((directory / "manifest.json").read_text())
    results_hash = digest(directory / "results.jsonl")
    if not manifest.get("complete") or manifest["results_sha256"] != results_hash:
        raise GenerationError("invalid_results", "Results are incomplete or changed.")
    records = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()]
    review = json.loads(Path(adjudication_file).read_text())
    summaries = summarize(records, adjudication=review, results_sha256=results_hash)
    by_identity = {(r["case_id"], r["variant"], r["path"]): r for r in records}
    judgments = {(r["case_id"], r["variant"], r["path"]): r for r in review["reviews"]}
    effects = dict(
        unsupported_claims_removed=0,
        supported_claims_removed=0,
        unnecessary_status_downgrades=0,
        status_errors_corrected=0,
    )
    for identity, baseline in by_identity.items():
        if identity[2] != "baseline":
            continue
        second_identity = (*identity[:2], "verified")
        if second_identity not in by_identity:
            continue
        second = by_identity[second_identity]
        first_review, second_review = judgments[identity], judgments[second_identity]
        removed = set(first_review["claims"]) - set(second_review["claims"])
        effects["unsupported_claims_removed"] += sum(
            not first_review["claims"][claim] for claim in removed
        )
        effects["supported_claims_removed"] += sum(
            first_review["claims"][claim] for claim in removed
        )
        effects["unnecessary_status_downgrades"] += (
            baseline["result"]["status"] != second["result"]["status"]
            and first_review["appropriate_status"]
            and not second_review["appropriate_status"]
        )
        effects["status_errors_corrected"] += (
            not first_review["appropriate_status"] and second_review["appropriate_status"]
        )

    def export(output):
        result = dict(
            results_sha256=results_hash,
            adjudication_sha256=digest(adjudication_file),
            reviewer=review["reviewer"],
            paired_semantic_changes=effects,
            summaries=summaries,
        )
        save(output / "review.json", result)
        return result

    return atomic_export(output_dir, export)
