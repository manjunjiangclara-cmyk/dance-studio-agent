"""Owner-editable policy uses the same resource as new agent runs."""

from fastapi import APIRouter, Request
from yaml import YAMLError

from studio_copilot.administration.service import AdministrationError
from studio_copilot.agent.policy import Policy, load_policy, save_policy

router = APIRouter(tags=["Policy"])


def configured_path(request: Request):
    service = request.app.state.agent_service
    return service.policy_path if service is not None else None


@router.get("/policy", response_model=Policy)
def read_policy(request: Request):
    try:
        return load_policy(configured_path(request))
    except (OSError, ValueError, YAMLError) as error:
        raise AdministrationError(
            503, "policy_unavailable", "The policy resource is invalid or unavailable."
        ) from error


@router.put("/policy", response_model=Policy)
def update_policy(body: Policy, request: Request):
    try:
        return save_policy(body, configured_path(request))
    except OSError as error:
        raise AdministrationError(
            503, "policy_save_failed", "The policy could not be saved. Please try again."
        ) from error
