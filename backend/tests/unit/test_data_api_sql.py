from datetime import date
from uuid import UUID

import pytest

from experiments.data_api.retrieval import normalize, statement
from experiments.data_api.sql import DataSQL, decode, identifier, parameter


def test_parameters_are_explicit_and_do_not_use_data_api_array_binding():
    assert parameter("n", None)["value"] == {"isNull": True}
    assert parameter("b", True)["value"] == {"booleanValue": True}
    assert parameter("d", date(2027, 2, 8))["typeHint"] == "DATE"
    assert parameter("ids", [UUID(int=1)])["typeHint"] == "JSON"
    assert parameter("blob", b"\x00\xff")["value"] == {"blobValue": b"\x00\xff"}
    with pytest.raises(TypeError):
        parameter("bad", object())


def test_decoder_rejects_unknown_or_ambiguous_results():
    assert decode({"isNull": True}) is None
    assert decode({"longValue": 42}) == 42
    for field in ({}, {"arrayValue": {}}, {"stringValue": "x", "longValue": 1}):
        with pytest.raises(ValueError):
            decode(field)


def test_schema_identifiers_cannot_escape_owned_namespace():
    assert identifier("data_api_" + "a" * 32)
    for schema in ("public", "data_api_test; DROP SCHEMA public", "data_api_../other"):
        with pytest.raises(ValueError):
            identifier(schema)


def test_retrieval_arrays_and_typed_rows_are_adapted():
    schema = "data_api_" + "b" * 32
    sql = statement("SELECT * FROM embedding_runs WHERE id=ANY(:run_ids)", schema)
    assert f"{schema}.embedding_runs" in sql and "::uuid[]" in sql
    assert "jsonb_array_elements_text" in sql
    row = normalize(
        {
            "run_id": str(UUID(int=1)),
            "profile": '{"model":"fake"}',
            "effective_from": "2027-02-08",
            "effective_to": None,
        }
    )
    assert row["run_id"] == UUID(int=1)
    assert row["profile"] == {"model": "fake"}
    assert row["effective_from"] == date(2027, 2, 8)


def test_failed_transaction_rolls_back_and_does_not_hide_original_error():
    class Client:
        rolled_back = False

        def begin_transaction(self, **kwargs):
            return {"transactionId": "tx"}

        def rollback_transaction(self, **kwargs):
            self.rolled_back = True
            raise RuntimeError("Rollback acknowledgement also failed")

    client = Client()
    with pytest.raises(ValueError, match="original"):
        with DataSQL(client, "cluster", "secret").transaction():
            raise ValueError("original")
    assert client.rolled_back
