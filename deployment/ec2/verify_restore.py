#!/usr/bin/python3
"""Restore a backup into an isolated disposable database, never the running application."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from uuid import uuid4

POSTGRES = "pgvector/pgvector:0.8.7-pg18-trixie"


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs)


def unpack(archive, directory):
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if sum(member.size for member in members) > 20 * 1024**3:
            raise ValueError("Backup exceeds the restore verification disk budget")
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe backup member")
        source.extractall(directory, filter="data")
    manifest = json.loads((directory / "checksums.json").read_text())
    if "database.dump" not in manifest or "policy/studio.yaml" not in manifest:
        raise ValueError("Backup is missing database or policy checksums")
    for name, expected in manifest.items():
        path = directory / name
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("Unsafe checksum path")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError("Backup checksum mismatch")
    ledger = directory / "public-demo/ledger.sqlite3"
    if ledger.exists():
        with sqlite3.connect(f"file:{ledger}?mode=ro", uri=True) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Invalid quota ledger")
    return manifest


def verify(archive):
    name = "studio-restore-check-" + uuid4().hex
    with tempfile.TemporaryDirectory(prefix="studio-restore-") as temporary:
        directory = Path(temporary)
        manifest = unpack(archive, directory)
        run(
            "docker",
            "run",
            "--detach",
            "--name",
            name,
            "--network",
            "none",
            "--memory",
            "768m",
            "--env",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "--env",
            "POSTGRES_USER=copilot",
            "--env",
            "POSTGRES_DB=restore_check",
            POSTGRES,
        )
        try:
            for _ in range(60):
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        name,
                        "pg_isready",
                        "-h",
                        "127.0.0.1",
                        "-U",
                        "copilot",
                        "-d",
                        "restore_check",
                    ],
                    capture_output=True,
                )
                if result.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Restore database did not become ready")
            with (directory / "database.dump").open("rb") as stream:
                run(
                    "docker",
                    "exec",
                    "-i",
                    name,
                    "pg_restore",
                    "--exit-on-error",
                    "--no-owner",
                    "--username=copilot",
                    "--dbname=restore_check",
                    stdin=stream,
                )
            sql = """SELECT json_build_object(
                'revision', (SELECT version_num FROM alembic_version),
                'vector', (SELECT extversion FROM pg_extension WHERE extname='vector'),
                'documents', (SELECT count(*) FROM documents),
                'students', (SELECT count(*) FROM students),
                'checkpoints', (SELECT count(*) FROM checkpoints),
                'messages', (SELECT count(*) FROM messages));"""
            result = run(
                "docker",
                "exec",
                name,
                "psql",
                "-U",
                "copilot",
                "-d",
                "restore_check",
                "-At",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                sql,
                text=True,
            )
            summary = json.loads(result.stdout)
            if not summary["revision"] or not summary["vector"]:
                raise ValueError("Restored schema or vector extension is missing")
            return {"status": "passed", "restored": summary, "checksummed_files": len(manifest)}
        finally:
            # The exact randomly named isolated container is the only deletion target.
            subprocess.run(["docker", "rm", "--force", "--volumes", name], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.archive)))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Isolated restore verification failed ({type(error).__name__}).")
