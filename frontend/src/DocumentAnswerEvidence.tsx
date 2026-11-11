import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function documentCitations(result: unknown) {
  const claims = record(result).claims;
  if (!Array.isArray(claims)) return [];
  return claims.flatMap((claim) => {
    const citations = record(claim).citations;
    return Array.isArray(citations) ? citations.map(record) : [];
  });
}

export function documentCitationUrl(value: unknown) {
  const citation = record(value);
  const id = text(citation.document_id);
  const revision = citation.revision;
  const offset = citation.start;
  if (
    !id ||
    !Number.isSafeInteger(revision) ||
    Number(revision) < 1 ||
    !Number.isSafeInteger(offset) ||
    Number(offset) < 0
  )
    return undefined;
  const query = new URLSearchParams({
    document: id,
    revision: String(revision),
    offset: String(offset),
  });
  return `/workspace/knowledge/documents?${query}#revision-preview`;
}

export function DocumentAnswerEvidence({
  result,
  workspace,
}: {
  result: unknown;
  workspace: boolean;
}) {
  const value = record(result);
  const claims = Array.isArray(value.claims) ? value.claims : [];
  return (
    <section aria-label="Document answer and citations">
      <p>
        <strong>
          Document answer: {text(value.status).replaceAll("_", " ")}
        </strong>
        {text(value.as_of) && ` · Policy date ${text(value.as_of)}`}
      </p>
      {value.status === "failed" && (
        <p>
          Document lookup could not be completed. Teacher verification is
          required.
        </p>
      )}
      {text(value.answer) && (
        <p style={{ whiteSpace: "pre-wrap" }}>{text(value.answer)}</p>
      )}
      {claims.map((raw, index) => {
        const claim = record(raw);
        const citations = Array.isArray(claim.citations) ? claim.citations : [];
        return (
          <div key={index}>
            <p>{text(claim.text)}</p>
            {citations.map((rawCitation, citationIndex) => {
              const citation = record(rawCitation);
              const url = workspace ? documentCitationUrl(citation) : undefined;
              return (
                <div key={citationIndex}>
                  <p>
                    {url ? (
                      <Link className="inline-link" to={url}>
                        <strong>{text(citation.title)}</strong>
                        <ArrowUpRight size={13} />
                      </Link>
                    ) : (
                      <strong>{text(citation.title)}</strong>
                    )}
                    {` · Revision ${Number(citation.revision)} · Characters ${Number(citation.start)}–${Number(citation.end)}`}
                  </p>
                  <blockquote style={{ whiteSpace: "pre-wrap" }}>
                    {text(citation.quote)}
                  </blockquote>
                  <p className="muted">
                    {`[${text(citation.evidence_id)}] · Document ${text(citation.document_id)}`}
                    {text(citation.effective_from) &&
                      ` · From ${text(citation.effective_from)}`}
                    {text(citation.effective_to) &&
                      ` · Through ${text(citation.effective_to)}`}
                  </p>
                </div>
              );
            })}
          </div>
        );
      })}
      {Array.isArray(value.missing_information) &&
        value.missing_information.length > 0 && (
          <p>Unresolved: {value.missing_information.map(text).join("; ")}</p>
        )}
    </section>
  );
}
