"""One task shares reservations, cache and opaque correlation across worker calls."""

import inspect
import time
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from functools import wraps
from uuid import uuid4

from .budget import Budget, Limits, OperationsError
from .cache import QueryEmbeddingCache
from .telemetry import EventSink

_current = ContextVar("document_operations", default=None)


class Task:
    def __init__(self, limits=None, events_file=None, sink=None):
        self.operation_id = str(uuid4())
        self.budget = Budget(limits)
        self.cache = QueryEmbeddingCache()
        self.sink = sink or EventSink(events_file)
        self.tokenizer = None

    def event(self, operation, stage, status="success", **fields):
        self.sink.emit(self.operation_id, operation, stage, status, **fields)


def current():
    return _current.get()


@contextmanager
def task(limits=None, events_file=None, *, control=None):
    from studio_copilot.agent.tracing import _suppress_automatic_tracing

    control = control or Task(limits, events_file)
    token = _current.set(control)
    try:
        with _suppress_automatic_tracing():
            yield control
    finally:
        _current.reset(token)
        control.sink.close()


def instrument(operation):
    def decorate(function):
        def start():
            return time.perf_counter()

        def finish(control, started, error=None):
            code = getattr(error, "code", "operation_failed")
            control.event(
                operation,
                "operation",
                "failure" if error else "success",
                seconds=time.perf_counter() - started,
                **({"error_code": code} if error else {}),
            )

        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def async_call(*args, **kwargs):
                if current() is None:
                    with task():
                        return await async_call(*args, **kwargs)
                started = start()
                try:
                    result = await function(*args, **kwargs)
                except BaseException as error:
                    finish(current(), started, error)
                    raise
                finish(current(), started)
                return result

            return async_call

        @wraps(function)
        def call(*args, **kwargs):
            if current() is None:
                with task():
                    return call(*args, **kwargs)
            started = start()
            try:
                result = function(*args, **kwargs)
            except BaseException as error:
                finish(current(), started, error)
                raise
            failed = isinstance(result, dict) and (
                result.get("execution_status") == "failed"
                or result.get("technical_failures", 0)
                or current().budget.exhausted
            )
            finish(
                current(),
                started,
                OperationsError("operation_failed", "Failed") if failed else None,
            )
            return result

        return call

    return decorate


def submit(pool, function, *args):
    return pool.submit(copy_context().run, function, *args)


def add_arguments(parser):
    parser.add_argument("--max-api-requests", type=int, default=1000)
    parser.add_argument("--max-estimated-input-tokens", type=int, default=10_000_000)
    parser.add_argument("--max-output-tokens-total", type=int, default=4_000_000)
    parser.add_argument("--events-file", type=str)


def cli_arguments(args):
    return dict(
        limits=Limits(
            args.max_api_requests, args.max_estimated_input_tokens, args.max_output_tokens_total
        ),
        events_file=args.events_file,
    )


def estimate(text):
    # UTF-8 bytes conservatively upper-bound text BPE tokens without downloads.
    # Provider framing/schema overhead is reserved separately by generation.
    return sum(len(text[i : i + 8192].encode("utf-8")) for i in range(0, len(text), 8192))


def preflight(requests, input_tokens, output_tokens=0, retries=1):
    control = current()
    budget = control.budget if control else Budget()
    budget.check_plan(requests, input_tokens, output_tokens)
    return dict(
        budget=budget.snapshot(),
        estimated_requests=requests,
        request_attempts_upper_bound=requests * retries,
        estimated_input_tokens=input_tokens,
        reserved_output_tokens=output_tokens,
    )


def enforce_budget():
    if current() and current().budget.exhausted:
        raise OperationsError("budget_exceeded", "The task API budget is exhausted.")


def run_cli(function, argv=None):
    import argparse
    import sys

    parser = argparse.ArgumentParser(add_help=False)
    add_arguments(parser)
    options, _ = parser.parse_known_args(argv)
    try:
        with task(**cli_arguments(options)) as control:
            try:
                result = function(argv)
                return 1 if control.budget.exhausted else result
            finally:
                accounting = control.budget.snapshot()
                if accounting["attempts"] or accounting["exhausted"]:
                    import json

                    print(json.dumps({"operations": accounting}), file=sys.stderr)
    except OperationsError as error:
        print(f"documents: {error.code}: task resource limit reached.", file=sys.stderr)
        return 1


def generation_estimate(instructions, payload, schema):
    import json

    return (
        estimate(instructions)
        + estimate(json.dumps(payload, ensure_ascii=False))
        + estimate(json.dumps(schema.model_json_schema()))
        + 256
    )
