"""Task-local, thread-safe reservations. Estimates are not a billing guarantee."""

from dataclasses import asdict, dataclass
from threading import Lock


class OperationsError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def nonnegative(value):
    return type(value) is int and value >= 0


@dataclass(frozen=True)
class Limits:
    max_api_requests: int = 1000
    max_estimated_input_tokens: int = 10_000_000
    max_output_tokens_total: int = 4_000_000

    def __post_init__(self):
        if not all(nonnegative(v) for v in asdict(self).values()):
            raise OperationsError("invalid_limits", "Budgets must be nonnegative integers.")


class Ticket:
    def __init__(self, budget):
        self.budget = budget
        self.finished = False

    def finish(self, input_tokens=None, output_tokens=None):
        with self.budget.lock:
            if self.finished:
                return
            self.finished = True
            if nonnegative(input_tokens) and nonnegative(output_tokens):
                self.budget.input_tokens += input_tokens
                self.budget.output_tokens += output_tokens
                self.budget.unknown_usage_calls -= 1


class Budget:
    def __init__(self, limits=None):
        self.limits = limits or Limits()
        self.lock = Lock()
        self.attempts = self.reserved_input_tokens = self.reserved_output_tokens = 0
        self.input_tokens = self.output_tokens = self.unknown_usage_calls = 0
        self.exhausted = False

    def _check(self, requests, input_tokens, output_tokens):
        if not all(nonnegative(v) for v in (requests, input_tokens, output_tokens)):
            raise OperationsError("invalid_limits", "Reservation must be nonnegative integers.")
        if (
            self.attempts + requests > self.limits.max_api_requests
            or self.reserved_input_tokens + input_tokens > self.limits.max_estimated_input_tokens
            or self.reserved_output_tokens + output_tokens > self.limits.max_output_tokens_total
        ):
            raise OperationsError("budget_exceeded", "The task API budget is exhausted.")

    def check_plan(self, requests, input_tokens, output_tokens=0):
        with self.lock:
            self._check(requests, input_tokens, output_tokens)

    def reserve(self, input_tokens, output_tokens=0):
        with self.lock:
            if self.exhausted:
                raise OperationsError("budget_exceeded", "The task API budget is exhausted.")
            try:
                self._check(1, input_tokens, output_tokens)
            except OperationsError:
                self.exhausted = True
                raise
            self.attempts += 1
            self.reserved_input_tokens += input_tokens
            self.reserved_output_tokens += output_tokens
            self.unknown_usage_calls += 1
        return Ticket(self)

    def snapshot(self):
        with self.lock:
            return dict(
                limits=asdict(self.limits),
                attempts=self.attempts,
                reserved_input_tokens=self.reserved_input_tokens,
                reserved_output_tokens=self.reserved_output_tokens,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                unknown_usage_calls=self.unknown_usage_calls,
                exhausted=self.exhausted,
            )
