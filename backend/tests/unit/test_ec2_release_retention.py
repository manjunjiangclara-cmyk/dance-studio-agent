"""Execute release.sh with real links and isolated fake host/Docker side effects."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def release_host(tmp_path):
    studio = tmp_path / "studio"
    for name in ("config", "policy", "postgres", "releases"):
        (studio / name).mkdir(parents=True)
    (studio / "host-ready").touch()
    (studio / "config/domain").write_text("initial.example.com\n")
    (studio / "policy/studio.yaml").write_text("version: fixture\n")
    state_path = tmp_path / "docker-state.json"
    state_path.write_text(json.dumps({"images": ["another-project:latest"], "removed": []}))
    binaries = tmp_path / "bin"
    binaries.mkdir()
    stub = (
        "#!"
        + sys.executable
        + "\n"
        + """
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
root = Path(os.environ["TEST_STUDIO_ROOT"])
state_path = Path(os.environ["TEST_DOCKER_STATE"])
state = json.loads(state_path.read_text())
if name == "studio-host":
    if args[0] == "current":
        current = root / "current"
        print(current.resolve() if current.is_symlink() and current.is_dir() else "")
    elif args[0] == "download":
        (root / "releases" / args[1]).mkdir(exist_ok=True)
elif name == "docker":
    if args[:2] == ["buildx", "build"]:
        image = args[args.index("--tag") + 1]
        if image not in state["images"]:
            state["images"].append(image)
    elif args[:2] == ["images", "studio-copilot"]:
        print("\\n".join(image for image in state["images"] if image.startswith("studio-copilot:")))
    elif args[:2] == ["image", "rm"]:
        state["images"].remove(args[2])
        state["removed"].append(args[2])
    elif args[0] == "inspect":
        print("healthy")
    elif args[0] == "run" and "-c" in args and "printf" in args[-1]:
        print(f"{os.getuid()}:{os.getgid()}")
    elif args[0] == "compose" and "ps" in args:
        print("fixture-database")
    elif args[0] == "compose" and "exec" in args:
        sys.stdin.read()  # The real smoke body is passed, but no application/provider is run.
        if os.environ.get("FAIL_RELEASE_SMOKE") == "1":
            raise SystemExit(1)
state_path.write_text(json.dumps(state))
"""
    )
    for name in ("docker", "studio-host", "studio-backup", "mountpoint", "chown"):
        path = binaries / name
        path.write_text(stub)
        path.chmod(0o755)
    script = tmp_path / "release.sh"
    script.write_text(
        (ROOT / "deployment/ec2/release.sh").read_text().replace("/srv/studio", str(studio))
    )

    def deploy(sha, *, fail=False):
        return subprocess.run(
            ["bash", str(script), sha, "0" * 64],
            env={
                **os.environ,
                "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
                "TEST_STUDIO_ROOT": str(studio),
                "TEST_DOCKER_STATE": str(state_path),
                "STUDIO_RELEASE_LOCKED": "1",
                "STUDIO_RELEASE_HELPERS": sha,
                "FAIL_RELEASE_SMOKE": "1" if fail else "0",
            },
            text=True,
            capture_output=True,
            timeout=30,
        )

    return studio, state_path, deploy


def test_redeploy_preserves_distinct_rollback_until_next_release(release_host):
    studio, state_path, deploy = release_host
    a, b, c = "a" * 40, "b" * 40, "c" * 40
    for _ in range(2):
        result = deploy(a)
        assert result.returncode == 0, result.stderr
        assert (studio / "current").resolve() == studio / "releases" / a
        assert not (studio / "previous").is_symlink()  # Never manufacture a self rollback.

    assert deploy(b).returncode == 0
    prior_link = os.readlink(studio / "previous")
    assert Path(prior_link) == studio / "releases" / a
    (studio / "config/domain").write_text("updated.example.com\n")
    assert deploy(b).returncode == 0
    assert os.readlink(studio / "previous") == prior_link
    assert set(json.loads(state_path.read_text())["images"]) == {
        "another-project:latest",
        f"studio-copilot:{a}",
        f"studio-copilot:{b}",
    }

    assert deploy(c).returncode == 0
    assert (studio / "current").resolve() == studio / "releases" / c
    assert (studio / "previous").resolve() == studio / "releases" / b
    state = json.loads(state_path.read_text())
    assert set(state["images"]) == {
        "another-project:latest",
        f"studio-copilot:{b}",
        f"studio-copilot:{c}",
    }
    assert state["removed"] == [f"studio-copilot:{a}"]


def test_failed_candidate_does_not_promote_or_prune_rollback(release_host):
    studio, state_path, deploy = release_host
    a, b, c = "a" * 40, "b" * 40, "c" * 40
    assert deploy(a).returncode == 0
    assert deploy(b).returncode == 0
    result = deploy(c, fail=True)
    assert result.returncode != 0
    assert (studio / "current").resolve() == studio / "releases" / b
    assert (studio / "previous").resolve() == studio / "releases" / a
    state = json.loads(state_path.read_text())
    assert state["removed"] == []
    assert {f"studio-copilot:{a}", f"studio-copilot:{b}"} <= set(state["images"])
