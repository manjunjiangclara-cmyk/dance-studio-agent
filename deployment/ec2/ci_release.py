#!/usr/bin/env python3
"""Deploy only the tested, still-current master commit with GitHub OIDC credentials."""

import json
import os
import re
import subprocess
from urllib.request import Request, urlopen

import boto3
import deploy

REPOSITORY = "manjunjiangclara-cmyk/dance-studio-agent"


def master_is_current(sha):
    token = os.environ["GH_TOKEN"]
    request = Request(
        f"https://api.github.com/repos/{REPOSITORY}/git/ref/heads/master",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "dance-studio-ci-deployment",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)["object"]["sha"] == sha


def main():
    sha = os.environ.get("GITHUB_SHA", "")
    if (
        os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/master"
        or os.environ.get("GITHUB_EVENT_NAME") != "push"
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=deploy.ROOT, text=True).strip()
        != sha
    ):
        raise ValueError("Only the exact tested master push may be deployed")
    config = {
        "instance_id": os.environ["STUDIO_DEPLOY_INSTANCE_ID"],
        "bucket": os.environ["STUDIO_DEPLOY_BUCKET"],
        "origin": os.environ["STUDIO_DEPLOY_ORIGIN"],
    }
    clients = boto3.Session(region_name=deploy.REGION)
    deploy.validate_target(clients, config)
    if deploy.release(
        clients, config, before_dispatch=master_is_current, document_name="DanceStudioDeploy"
    ):
        deploy.smoke(config["origin"])


if __name__ == "__main__":
    main()
