"""Immutable fictional inputs for the public demonstration (not workspace data)."""

CLOTHING = (
    "Wear comfortable clothes you can move in, such as leggings and a fitted T-shirt. "
    "Socks are suitable for your first class; ballet shoes are optional."
)
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
        "clothing": "Beginner clothing policy, revision 1: " + CLOTHING,
        "missing_fee": "No trial fee is specified in this fictional source. A teacher "
        "must provide the fee or choose to confirm later. Never invent an amount.",
        "unrelated": "Studio welcome: our adult classes take place in Melbourne.",
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
    },
    "jules": {
        "student": "Jules Park is a new enquirer with no recorded level, attendance, "
        "enrolment or booking. Do not infer placement or eligibility.",
        "session": "Adult Ballet Level 2 meets Saturday 13 February 2027 at 6 pm "
        "at Merri Ballet Brunswick. It is not an established beginner placement.",
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
    },
}
