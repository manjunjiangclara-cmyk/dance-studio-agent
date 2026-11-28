"""CI release gates fail closed before dispatching commands to EC2."""

import importlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError

import pytest
import yaml

SHA = "a" * 40
OTHER_SHA = "b" * 40
REPO = "manjunjiangclara-cmyk/dance-studio-agent"


def test_workflow_requires_successful_tests_and_master_push():
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load((root / ".github/workflows/tests.yml").read_text())
    job = workflow["jobs"]["deploy"]
    assert job["needs"] == "test"
    assert "github.event_name == 'push'" in job["if"]
    assert "github.ref == 'refs/heads/master'" in job["if"]
    assert REPO in job["if"]
    assert job["concurrency"]["cancel-in-progress"] is False
    assert job["concurrency"]["queue"] == "max"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    assert "concurrency" not in workflow


@pytest.fixture
def ci(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "deployment/ec2"))
    return importlib.import_module("ci_release")


@pytest.fixture
def trusted_event(monkeypatch, ci):
    for key, value in {
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_REF": "refs/heads/master",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_SHA": SHA,
        "GH_TOKEN": "test-token",
        "STUDIO_DEPLOY_INSTANCE_ID": "i-test",
        "STUDIO_DEPLOY_BUCKET": "release-bucket",
        "STUDIO_DEPLOY_ORIGIN": "https://studio.example.test",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(ci.subprocess, "check_output", lambda *args, **kwargs: SHA + "\n")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("GITHUB_REPOSITORY", "other/project"),
        ("GITHUB_REF", "refs/heads/feature"),
        ("GITHUB_REF", "refs/pull/1/merge"),
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_EVENT_NAME", "workflow_dispatch"),
        ("GITHUB_SHA", OTHER_SHA.upper()),
        ("GITHUB_SHA", "abc"),
        ("GITHUB_SHA", "a" * 39 + ";"),
    ],
)
def test_untrusted_event_is_rejected_before_aws(ci, trusted_event, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    monkeypatch.setattr(ci.boto3, "Session", lambda **kwargs: pytest.fail("AWS must not be called"))
    with pytest.raises(ValueError, match="exact tested master"):
        ci.main()


def test_checkout_must_match_tested_sha(ci, trusted_event, monkeypatch):
    monkeypatch.setattr(ci.subprocess, "check_output", lambda *args, **kwargs: OTHER_SHA + "\n")
    monkeypatch.setattr(ci.boto3, "Session", lambda **kwargs: pytest.fail("AWS must not be called"))
    with pytest.raises(ValueError, match="exact tested master"):
        ci.main()


@pytest.mark.parametrize("head, expected", [(SHA, True), (OTHER_SHA, False)])
def test_master_check_compares_authenticated_github_ref(
    ci, trusted_event, monkeypatch, head, expected
):
    def fake_urlopen(request, timeout):
        assert request.full_url == f"https://api.github.com/repos/{REPO}/git/ref/heads/master"
        assert request.get_header("Authorization") == "Bearer test-token"
        assert timeout == 20
        return io.BytesIO(json.dumps({"object": {"sha": head}}).encode())

    monkeypatch.setattr(ci, "urlopen", fake_urlopen)
    assert ci.master_is_current(SHA) is expected


def test_master_api_failure_is_not_treated_as_current(ci, trusted_event, monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("GitHub unavailable")

    monkeypatch.setattr(ci, "urlopen", fail)
    with pytest.raises(URLError):
        ci.master_is_current(SHA)


def fake_release_clients(monkeypatch, ci):
    calls = []

    def check_output(args, **kwargs):
        return "" if args[1] == "status" else SHA + "\n"

    def archive(args, **kwargs):
        kwargs["stdout"].write(b"fake immutable archive")

    monkeypatch.setattr(ci.deploy.subprocess, "check_output", check_output)
    monkeypatch.setattr(ci.deploy.subprocess, "run", archive)

    def client(name):
        if name == "s3":
            return SimpleNamespace(upload_file=lambda *args, **kwargs: calls.append("upload"))
        if name == "ssm":
            pytest.fail("SSM must not be called for stale or unverifiable master")
        pytest.fail(f"Unexpected AWS client: {name}")

    return SimpleNamespace(client=client), calls


def test_master_advanced_after_upload_does_not_dispatch_ssm(ci, trusted_event, monkeypatch):
    clients, calls = fake_release_clients(monkeypatch, ci)
    seen = []
    result = ci.deploy.release(
        clients,
        {"bucket": "release-bucket", "instance_id": "i-test"},
        before_dispatch=lambda sha: seen.append(sha) or False,
    )
    assert result is False
    assert calls == ["upload"]
    assert seen == [SHA]


def test_github_failure_after_upload_does_not_dispatch_ssm(ci, trusted_event, monkeypatch):
    clients, calls = fake_release_clients(monkeypatch, ci)

    def fail(*args, **kwargs):
        raise URLError("GitHub unavailable")

    monkeypatch.setattr(ci, "urlopen", fail)
    with pytest.raises(URLError):
        ci.deploy.release(
            clients,
            {"bucket": "release-bucket", "instance_id": "i-test"},
            before_dispatch=ci.master_is_current,
        )
    assert calls == ["upload"]


def test_ci_release_dispatches_only_fixed_document_with_validated_ids(
    ci, trusted_event, monkeypatch
):
    captured = {}

    def check_output(args, **kwargs):
        return "" if args[1] == "status" else SHA + "\n"

    def archive(args, **kwargs):
        kwargs["stdout"].write(b"immutable archive")

    monkeypatch.setattr(ci.deploy.subprocess, "check_output", check_output)
    monkeypatch.setattr(ci.deploy.subprocess, "run", archive)

    def send_command(**kwargs):
        captured.update(kwargs)
        return {"Command": {"CommandId": "command-id"}}

    ssm = SimpleNamespace(
        send_command=send_command,
        get_command_invocation=lambda **kwargs: {"Status": "Success"},
        exceptions=SimpleNamespace(InvocationDoesNotExist=type("Missing", (Exception,), {})),
    )
    clients = SimpleNamespace(
        client=lambda name: (
            SimpleNamespace(upload_file=lambda *args, **kwargs: None) if name == "s3" else ssm
        )
    )
    assert ci.deploy.release(
        clients,
        {"bucket": "release-bucket", "instance_id": "i-test"},
        before_dispatch=lambda sha: sha == SHA,
        document_name="DanceStudioDeploy",
    )
    assert captured["DocumentName"] == "DanceStudioDeploy"
    assert captured["Parameters"]["ReleaseSha"] == [SHA]
    assert len(captured["Parameters"]["Checksum"][0]) == 64
    assert "commands" not in captured["Parameters"]


@pytest.mark.parametrize("released", [True, False])
def test_ci_smokes_only_successful_release(ci, trusted_event, monkeypatch, released):
    calls = []
    clients = object()
    monkeypatch.setattr(ci.boto3, "Session", lambda **kwargs: clients)
    monkeypatch.setattr(
        ci.deploy,
        "validate_target",
        lambda client, config: calls.append(("validate", client, config)),
    )

    def release(client, config, *, before_dispatch, document_name):
        calls.append(("release", client, config, before_dispatch, document_name))
        return released

    monkeypatch.setattr(ci.deploy, "release", release)
    monkeypatch.setattr(ci.deploy, "smoke", lambda origin: calls.append(("smoke", origin)))
    ci.main()
    assert [call[0] for call in calls] == (
        ["validate", "release", "smoke"] if released else ["validate", "release"]
    )
    assert calls[1][3] is ci.master_is_current
    assert calls[1][4] == "DanceStudioDeploy"
    assert calls[0][1] is clients
    if released:
        assert calls[-1][1] == "https://studio.example.test"
