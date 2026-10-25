import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import AgentRun

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "policy_text",
    [
        "invalid: [",
        "version: x\nabsence_notice_before_start: true\nexplanation: x\ninvented_credit_limit: 2\n",
    ],
)
def test_invalid_policy_has_safe_error_and_creates_no_run(
    rig, scenario, tmp_path, policy_text, db_engine
):
    client, _, service, _ = rig
    path = tmp_path / "bad-policy.yaml"
    path.write_text(policy_text)
    service.policy_path = path
    result = client.post(
        f"/api/v1/conversations/{scenario['conversation']}/agent-runs",
        json={"source_message_id": str(scenario["source"])},
    )
    assert result.status_code == 503, result.text
    assert result.json()["error"]["code"] == "policy_unavailable"
    with Session(db_engine) as db:
        assert db.scalar(select(func.count()).select_from(AgentRun)) == 0
