"""Use LangGraph's own checkpoint schema; provision it explicitly, not during API startup."""

from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row


@contextmanager
def postgres_checkpointer(engine):
    raw = engine.raw_connection()
    connection = raw.driver_connection
    previous_autocommit, previous_row_factory = connection.autocommit, connection.row_factory
    try:
        connection.autocommit = True
        connection.row_factory = dict_row
        yield PostgresSaver(connection)
    finally:
        connection.row_factory = previous_row_factory
        connection.autocommit = previous_autocommit
        raw.close()


def main():
    from studio_copilot.persistence.database import make_engine

    engine = make_engine()
    try:
        with postgres_checkpointer(engine) as saver:
            saver.setup()
    finally:
        engine.dispose()
    print("LangGraph checkpoint tables are ready.")


if __name__ == "__main__":
    main()
