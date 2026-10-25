import os
from pathlib import Path

import yaml
from pydantic import Field, StrictBool

from studio_copilot.agent.contracts import StrictModel


class Policy(StrictModel):
    version: str = Field(min_length=1, max_length=100)
    absence_notice_before_start: StrictBool
    explanation: str = Field(min_length=1, max_length=10_000)


def load_policy(path: Path | None = None) -> dict:
    configured = path or Path(os.environ.get("STUDIO_POLICY_PATH", "policies/studio.yaml"))
    return Policy.model_validate(yaml.safe_load(configured.read_text())).model_dump()
