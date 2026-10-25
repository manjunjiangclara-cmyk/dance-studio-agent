import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from studio_copilot.demo import seed_demo
from studio_copilot.persistence.models import Student

pytestmark = pytest.mark.integration


def test_demo_seed_is_repeatable_and_preserves_edits(db_engine):
    with Session(db_engine) as db, db.begin():
        result = seed_demo(db)
        assert result["created"]
    with Session(db_engine) as db, db.begin():
        alex = db.get(Student, result["ids"]["alex"])
        alex.highest_level = "Staff corrected level"
    with Session(db_engine) as db, db.begin():
        assert not seed_demo(db)["created"]
        assert db.scalar(select(func.count()).select_from(Student)) == 2
        assert db.get(Student, result["ids"]["alex"]).highest_level == "Staff corrected level"
