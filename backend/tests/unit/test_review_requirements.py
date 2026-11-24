from studio_copilot.agent.review_requirements import review_requirements


def test_review_separates_student_information_from_an_unanswered_studio_fact():
    draft = {
        "answers": [
            {"status": "needs_student"},
            {"status": "needs_teacher", "question_id": "fee"},
        ],
        "required_question_ids": ["fee"],
    }
    assert review_requirements("enquiry", {}, [], draft) == ["student_information", "teacher_input"]
    draft["question_resolutions"] = [{"question_id": "fee", "decision": "defer"}]
    assert review_requirements("enquiry", {}, [], draft) == ["student_information"]


def test_multiple_eligible_makeup_sessions_need_the_students_choice():
    evidence = [
        {"tool": "verify_makeup_request", "result": {"verified": True}},
        {
            "tool": "validate_makeup_candidates",
            "result": {
                "ambiguous": True,
                "valid_session_ids": ["session-a", "session-b"],
                "max_attended_level": "Level 2",
            },
        },
    ]
    assert review_requirements("makeup", {"absence_date": "2027-02-08"}, evidence, None) == [
        "student_information"
    ]


def test_missing_absence_date_needs_student_information_without_assuming_late_notice():
    evidence = [
        {
            "tool": "verify_makeup_request",
            "result": {
                "verified": False,
                "notice_acceptable": False,
                "notice_before_start": None,
            },
        },
    ]
    assert review_requirements("makeup", {"absence_date": None}, evidence, None) == [
        "student_information"
    ]


def test_full_makeup_session_needs_another_student_choice():
    evidence = [
        {"tool": "verify_makeup_request", "result": {"verified": True}},
        {
            "tool": "validate_makeup_candidates",
            "result": {
                "valid_session_ids": [],
                "max_attended_level": "Level 2",
                "excluded": [{"reason": "full"}],
            },
        },
    ]
    assert review_requirements("makeup", {"absence_date": "2027-02-08"}, evidence, None) == [
        "student_information"
    ]
