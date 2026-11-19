import os
import tempfile
from pathlib import Path

import yaml
from pydantic import Field, StrictBool, field_validator

from studio_copilot.agent.contracts import StrictModel


class Policy(StrictModel):
    version: str = Field(min_length=1, max_length=100)
    absence_notice_before_start: StrictBool
    explanation: str = Field(default="", max_length=10_000)
    level_order: list[str] = Field(default_factory=list)

    @field_validator("level_order")
    @classmethod
    def valid_levels(cls, levels):
        levels = [level.strip() for level in levels]
        if any(not level or len(level) > 100 for level in levels):
            raise ValueError("Levels must be non-empty and at most 100 characters.")
        if len({level.casefold() for level in levels}) != len(levels):
            raise ValueError("Each level must appear only once.")
        return levels


def policy_path(path: Path | None = None) -> Path:
    return path or Path(os.environ.get("STUDIO_POLICY_PATH", "policies/studio.yaml"))


def load_policy(path: Path | None = None) -> dict:
    configured = policy_path(path)
    return Policy.model_validate(yaml.safe_load(configured.read_text())).model_dump()


def save_policy(policy: Policy, path: Path | None = None) -> dict:
    """Replace the resource atomically so new runs never read a partial policy."""
    configured = policy_path(path).resolve()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=configured.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            yaml.safe_dump(
                policy.model_dump(exclude={"explanation"}),
                stream,
                sort_keys=False,
                allow_unicode=True,
            )
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(configured)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return policy.model_dump(exclude={"explanation"}) | {"explanation": ""}
