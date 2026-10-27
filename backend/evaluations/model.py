"""Measured live adapter; application fallbacks cannot hide evaluation failures."""

from time import monotonic

from studio_copilot.agent.contracts import ModelError
from studio_copilot.agent.openai_model import OpenAIModel


class MeasuredModel(OpenAIModel):
    """Bound adapter requests and retain usage, without retaining provider exceptions."""

    def __init__(self, max_calls: int):
        super().__init__()
        self.max_calls = max_calls
        self.calls = []
        self.failures = []
        self.exhausted = False

    def _step(self, name, operation, *args):
        try:
            return operation(*args)
        except ModelError:
            self.failures.append(name)
            raise

    def route(self, context):
        return self._step("route", super().route, context)

    def interpret_makeup(self, context):
        return self._step("interpret_makeup", super().interpret_makeup, context)

    def choose_tools(self, context, transcript):
        return self._step("choose_tools", super().choose_tools, context, transcript)

    def draft(self, context):
        return self._step("draft", super().draft, context)

    def reconcile(self, context):
        return self._step("reconcile", super().reconcile, context)

    def _request(self, operation, **kwargs):
        if len(self.calls) >= self.max_calls:
            self.exhausted = True
            raise ModelError("The evaluation model-call budget was exhausted.")
        call = {"operation": operation.__name__, "completed": False}
        self.calls.append(call)
        started = monotonic()
        try:
            response = super()._request(operation, **kwargs)
            call["completed"] = True
            if response.usage:
                call["input_tokens"] = response.usage.input_tokens
                call["output_tokens"] = response.usage.output_tokens
            return response
        except ModelError as error:
            cause = error.__cause__ or error
            call["error_type"] = type(cause).__name__
            status = getattr(cause, "status_code", None)
            if isinstance(status, int):
                call["http_status"] = status
            raise
        finally:
            call["latency_ms"] = round((monotonic() - started) * 1000)
