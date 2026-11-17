"""Deployment boundary tests: private configuration, archives and durable demo state."""

import hashlib
import importlib.util
import io
import json
import sqlite3
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("ec2_host", ROOT / "deployment/ec2/host.py")
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


def payload():
    return {key: "x" * 40 for key in host.REQUIRED}


@pytest.mark.parametrize(
    "value", ["line\nbreak", "line\rbreak", "null\0byte", "a'quote", "a\\slash"]
)
def test_environment_rejects_control_or_quote_injection(value):
    with pytest.raises(ValueError):
        host.env_text({"OPENAI_API_KEY": value})


def test_environment_preserves_literal_dollars_and_private_atomic_mode(tmp_path):
    target = tmp_path / "app.env"
    host.atomic_write(target, host.env_text({"OPENAI_API_KEY": "literal$not_interpolated"}))
    assert target.read_text() == "OPENAI_API_KEY='literal$not_interpolated'\n"
    assert target.stat().st_mode & 0o777 == 0o600
    host.atomic_write(target, "replacement")
    assert target.read_text() == "replacement"
    assert list(tmp_path.iterdir()) == [target]


def test_configure_uses_fixed_origin_keeps_password_and_rejects_rotation(tmp_path, monkeypatch):
    monkeypatch.setattr(host, "ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    settings = payload()
    client = SimpleNamespace(get_secret_value=lambda **_: {"SecretString": json.dumps(settings)})
    config = {"secret_arn": "secret", "domain": "studio.example.com"}
    host.configure(config, client)
    first = (tmp_path / "config/app.env").read_text()
    assert "PUBLIC_BASE_URL='https://studio.example.com'" in first
    assert "STUDIO_DOCUMENT_ANSWERS='true'" in first
    host.configure(config, client)
    assert (tmp_path / "config/app.env").read_text() == first
    settings["POSTGRES_PASSWORD"] = "y" * 40
    with pytest.raises(ValueError, match="explicit database rotation"):
        host.configure(config, client)
    assert (tmp_path / "config/app.env").read_text() == first


def test_bad_secret_does_not_replace_existing_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr(host, "ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/app.env").write_text("previous")
    client = SimpleNamespace(get_secret_value=lambda **_: {"SecretString": "{}"})
    with pytest.raises(ValueError):
        host.configure({"secret_arn": "secret", "domain": "demo.example"}, client)
    assert (tmp_path / "config/app.env").read_text() == "previous"


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", tarfile.REGTYPE),
        ("/absolute", tarfile.REGTYPE),
        ("link", tarfile.SYMTYPE),
        ("hard", tarfile.LNKTYPE),
        ("device", tarfile.CHRTYPE),
    ],
)
def test_release_rejects_archive_traversal_links_and_devices(tmp_path, name, kind):
    archive = tmp_path / "release.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.linkname = "outside"
        stream.addfile(member)
    target = tmp_path / "target"
    target.mkdir()
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Unsafe release"):
        host.extract_release(archive, target, checksum)
    assert list(target.iterdir()) == []


def test_release_checks_archive_identity_before_extracting(tmp_path):
    archive = tmp_path / "release.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo("README.md")
        member.size = 4
        stream.addfile(member, io.BytesIO(b"safe"))
    target = tmp_path / "source"
    target.mkdir()
    with pytest.raises(ValueError, match="checksum"):
        host.extract_release(archive, target, "0" * 64)
    assert not list(target.iterdir())
    host.extract_release(archive, target, hashlib.sha256(archive.read_bytes()).hexdigest())
    assert (target / "README.md").read_text() == "safe"


def test_backup_keeps_edited_policy_and_consistent_sqlite_in_wal_mode(tmp_path, monkeypatch):
    root = tmp_path / "persistent"
    (root / "policy").mkdir(parents=True)
    (root / "public-demo").mkdir()
    (root / "policy/studio.yaml").write_text("version: owner-edited\n")
    ledger = sqlite3.connect(root / "public-demo/ledger.sqlite3")
    ledger.execute("PRAGMA journal_mode=WAL")
    ledger.execute("CREATE TABLE runs(id integer primary key)")
    ledger.execute("INSERT INTO runs VALUES(1)")
    ledger.commit()
    monkeypatch.setattr(host, "ROOT", root)
    backup = tmp_path / "backup"
    backup.mkdir()
    host.snapshot_files(backup)
    with sqlite3.connect(backup / "public-demo/ledger.sqlite3") as restored:
        assert restored.execute("SELECT count(*) FROM runs").fetchone()[0] == 1
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert (backup / "policy/studio.yaml").read_text() == "version: owner-edited\n"
    checksums = json.loads((backup / "checksums.json").read_text())
    assert set(checksums) == {"policy/studio.yaml", "public-demo/ledger.sqlite3"}
    for name, checksum in checksums.items():
        assert hashlib.sha256((backup / name).read_bytes()).hexdigest() == checksum
    ledger.close()


def test_first_release_does_not_treat_missing_current_as_previous(tmp_path, monkeypatch):
    monkeypatch.setattr(host, "ROOT", tmp_path)
    assert host.current_release() == ""
    releases = tmp_path / "releases"
    releases.mkdir()
    candidate = releases / ("a" * 40)
    (tmp_path / "current").symlink_to(candidate)
    assert host.current_release() == ""
    candidate.mkdir()
    assert host.current_release() == str(candidate.resolve())


def test_current_release_cannot_target_an_unrelated_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(host, "ROOT", tmp_path)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (tmp_path / "current").symlink_to(unrelated)
    with pytest.raises(ValueError, match="outside"):
        host.current_release()


@pytest.fixture
def deployment_cli(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "deployment/ec2"))
    spec = importlib.util.spec_from_file_location("ec2_deploy", ROOT / "deployment/ec2/deploy.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configuration_preserves_existing_secrets_and_optional_provider_settings(
    deployment_cli, tmp_path, capsys
):
    values = payload()
    values["OPENAI_BASE_URL"] = "https://provider.example/v1"
    written = []
    client = SimpleNamespace(
        get_secret_value=lambda **_: {"SecretString": json.dumps(values)},
        put_secret_value=lambda **kwargs: written.append(json.loads(kwargs["SecretString"])),
    )
    clients = SimpleNamespace(client=lambda _: client)
    source = tmp_path / "private.env"
    source.write_text(
        "OPENAI_MODEL=updated-model\nDATABASE_URL=not-for-cloud\nADMIN_API_TOKEN=local-token\n"
    )
    deployment_cli.configure(
        clients,
        {
            "secret_arn": "secret",
            "callback": "https://demo.example/auth/callback",
            "origin": "https://demo.example",
        },
        source,
    )
    assert written[0]["OPENAI_BASE_URL"] == values["OPENAI_BASE_URL"]
    assert written[0]["SESSION_SECRET"] == values["SESSION_SECRET"]
    assert written[0]["ADMIN_API_TOKEN"] == values["ADMIN_API_TOKEN"]
    assert written[0]["POSTGRES_PASSWORD"] == values["POSTGRES_PASSWORD"]
    assert written[0]["OPENAI_MODEL"] == "updated-model"
    assert "DATABASE_URL" not in written[0]
    assert values["OPENAI_API_KEY"] not in capsys.readouterr().out


def test_missing_configuration_is_rejected_before_upload(deployment_cli, tmp_path):
    client = SimpleNamespace(
        get_secret_value=lambda **_: {"SecretString": "{}"},
        put_secret_value=lambda **_: pytest.fail("Invalid configuration must not be uploaded"),
    )
    source = tmp_path / "missing.env"
    source.write_text("OPENAI_MODEL=only-a-model\n")
    with pytest.raises(ValueError):
        deployment_cli.configure(
            SimpleNamespace(client=lambda _: client),
            {"secret_arn": "secret", "origin": "https://demo.example"},
            source,
        )


def test_cloud_origin_can_change_without_replacing_database_or_session(tmp_path, monkeypatch):
    monkeypatch.setattr(host, "ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    settings = payload()
    settings["PUBLIC_BASE_URL"] = "https://new.example.com"
    client = SimpleNamespace(get_secret_value=lambda **_: {"SecretString": json.dumps(settings)})
    host.configure({"secret_arn": "secret", "domain": "initial.example.com"}, client)
    assert (tmp_path / "config/domain").read_text() == "new.example.com\n"
    assert "PUBLIC_BASE_URL='https://new.example.com'" in (tmp_path / "config/app.env").read_text()
