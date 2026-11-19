"""Immutable fictional inputs for the public demonstration (not workspace data)."""

CLOTHING = (
    "Wear comfortable clothes you can move in, such as leggings and a fitted T-shirt. "
    "Socks are suitable for your first class; ballet shoes are optional."
)
PUBLIC_DOCUMENTS = [
    {
        "id": "beginner-clothing",
        "title": "Beginner clothing policy",
        "filename": "beginner-clothing.md",
        "content": (
            "Merri Ballet — Beginner clothing policy\n\n"
            "For adult beginners attending a first class:\n" + CLOTHING + "\n\n"
            "Bring water and tie long hair back. This document does not specify trial fees.\n"
        ),
        "revision": 1,
    },
    {
        "id": "studio-welcome",
        "title": "Studio welcome",
        "filename": "welcome.md",
        "content": "Studio welcome: our adult classes take place in Melbourne.",
        "revision": 1,
    },
    {
        "id": "first-class-guide",
        "title": "Your first ballet class",
        "filename": "first-class.md",
        "content": (
            "# Your first ballet class\n\n"
            "Adult beginners are welcome to ask the studio for help choosing a class. "
            "A particular class placement needs to be confirmed with the teacher.\n\n"
            "Bring water and tie long hair back. Wear comfortable clothes you can move in. "
            "Socks are suitable for a first class and ballet shoes are optional.\n"
        ),
        "revision": 1,
    },
    {
        "id": "makeup-guidelines",
        "title": "Absences and makeup classes",
        "filename": "absences-and-makeup.md",
        "content": (
            "# Absences and makeup classes\n\n"
            "Tell the studio about an absence before the class starts. A suggested makeup "
            "class must not be harder than the student's recorded attendance level.\n\n"
            "Availability and any other makeup entitlement or credit rules need confirmation "
            "from the teacher. A suggested class is not a reservation.\n"
        ),
        "revision": 1,
    },
    {
        "id": "class-information",
        "title": "Adult class information",
        "filename": "adult-class-information.md",
        "content": (
            "# Adult class information\n\n"
            "The fictional timetable includes Adult Ballet Level 2 at Merri Ballet Brunswick "
            "on Saturday 13 February 2027 at 6 pm. Ask the teacher whether this level is "
            "appropriate before treating it as a beginner placement.\n\n"
            "Class availability can change. A place is confirmed only after the teacher "
            "has reviewed and completed the booking.\n"
        ),
        "revision": 1,
    },
    {
        "id": "trials-and-fees",
        "title": "Trial classes and fees",
        "filename": "trials-and-fees.md",
        "content": (
            "# Trial classes and fees\n\n"
            "A student may ask the studio about trying a class. The trial fee is not "
            "specified in the example studio information. The teacher must confirm the "
            "price and any applicable conditions before giving a quote.\n"
        ),
        "revision": 1,
    },
]

CATALOG = {
    "booking": {
        "history": "Alex's original email asks to replace Monday 8 February 2027 with Thursday. "
        "The latest email says: Actually, Saturday 13 February would be better. "
        "The latest preference supersedes Thursday.",
        "notice": "The fictional absence notice arrived before Monday's class started.",
        "attendance": "Alex has recorded Level 2 attendance. The example policy permits "
        "a replacement at that level when the absence notice is timely.",
        "session": "Saturday 13 February 2027, 6 pm, Adult Ballet Level 2, Merri Ballet "
        "Brunswick. Capacity 2, current students: Noah Ellis. One place available. "
        "No booking exists for Alex; final approval remains simulated.",
    },
    "document": {
        "clothing": "Beginner clothing policy, revision 1: " + PUBLIC_DOCUMENTS[0]["content"],
        "missing_fee": "No trial fee is specified in this fictional source. "
        + PUBLIC_DOCUMENTS[5]["content"],
        "unrelated": PUBLIC_DOCUMENTS[1]["content"],
    },
}
EMAILS = {
    "booking": "I cannot attend Monday 8 February. Could I come Thursday instead?\n"
    "Follow-up: Actually, Saturday 13 February would be better.",
    "document": "I'm new to ballet. What should I wear for my first class, "
    "and what does a trial cost?",
}

CUSTOM_STUDENTS = {
    "alex": {"name": "Alex Morgan", "email": "alex@example.test"},
    "jules": {"name": "Jules Park", "email": "jules@example.test"},
}
CUSTOM_CATALOG = {
    "alex": {
        "student": "Alex Morgan has recorded Level 2 attendance and a regular Thursday "
        "Level 2 enrolment. These are fictional demonstration records.",
        "history": "Earlier email, 7 February 2027: Alex cannot attend Monday 8 February "
        "and asks about Thursday instead. Treat the new email as the latest request, "
        "which can change earlier preferences.",
        "notice": CATALOG["booking"]["notice"],
        "makeup_policy": "The example policy requires absence notice before class starts "
        "and a replacement no harder than the student's recorded attendance level. "
        "Other makeup entitlement or credit rules are unspecified.",
        "session": CATALOG["booking"]["session"],
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
        "first_class": PUBLIC_DOCUMENTS[2]["content"],
        "makeup_guide": PUBLIC_DOCUMENTS[3]["content"],
        "class_information": PUBLIC_DOCUMENTS[4]["content"],
        "trials_and_fees": PUBLIC_DOCUMENTS[5]["content"],
        "welcome": PUBLIC_DOCUMENTS[1]["content"],
    },
    "jules": {
        "student": "Jules Park is a new enquirer with no recorded level, attendance, "
        "enrolment or booking. Do not infer placement or eligibility.",
        "session": "Adult Ballet Level 2 meets Saturday 13 February 2027 at 6 pm "
        "at Merri Ballet Brunswick. It is not an established beginner placement.",
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
        "first_class": PUBLIC_DOCUMENTS[2]["content"],
        "makeup_guide": PUBLIC_DOCUMENTS[3]["content"],
        "class_information": PUBLIC_DOCUMENTS[4]["content"],
        "trials_and_fees": PUBLIC_DOCUMENTS[5]["content"],
        "welcome": PUBLIC_DOCUMENTS[1]["content"],
    },
}
