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
    "new": {"name": "New enquirer"},
    "alex": {"name": "Alex Morgan", "email": "alex@example.test"},
    "jules": {"name": "Jules Park", "email": "jules@example.test"},
    "833efaed-1e89-5f89-8b47-cb9cbcf3399c": {"name": "Maya Chen", "email": "maya@example.test"},
    "60bbb539-91bc-5858-80f5-a1b6ae915aae": {"name": "Noah Ellis", "email": "noah@example.test"},
    "2eca4988-037e-54f9-9668-59ee06b2888b": {"name": "Riley James", "email": "riley@example.test"},
}
# These summaries mirror the fictional Student Profile memory shown in the UI.
# A parity test compares them with the public example data.
CUSTOM_MEMORY = {
    "new": {},
    "alex": {
        "conversation_summary": "Has practised ballet for two years and enjoys evening ballet "
        "classes and barre work.",
        "request_summary": "Saturday replaces the earlier Thursday preference.",
    },
    "833efaed-1e89-5f89-8b47-cb9cbcf3399c": {
        "conversation_summary": "Asked about a makeup class for Monday 8 February.",
        "request_summary": "Asked whether Saturday 13 February was an option. "
        "A teacher reviewed the response.",
    },
    "60bbb539-91bc-5858-80f5-a1b6ae915aae": {
        "conversation_summary": "Asked whether a makeup class could be arranged.",
        "request_summary": "The absence and preferred makeup dates were not provided.",
    },
    "jules": {
        "conversation_summary": "New to ballet and has never danced before.",
        "request_summary": "Asked about the Thursday class time and location, trial cost, "
        "and what to wear.",
    },
    "2eca4988-037e-54f9-9668-59ee06b2888b": {
        "conversation_summary": "Asked for help choosing a ballet class.",
        "request_summary": "No class preferences or dance experience were provided.",
    },
}
# Shared session facts contain no student-specific records.
CUSTOM_SESSION = (
    "Adult Ballet Level 2 meets Saturday 13 February 2027 at 6 pm "
    "at Merri Ballet Brunswick. It is not an established beginner placement."
)
CUSTOM_CATALOG = {
    "new": {
        "student": "A new enquirer with no recorded level, attendance, enrolment or booking. "
        "Do not infer placement or eligibility.",
        "session": CUSTOM_SESSION,
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
    },
    "alex": {
        "student": "Alex Morgan has recorded Level 2 attendance. The Thursday Level 2 "
        "enrolment begins 10 February, after the reference date. These are fictional records.",
        "history": "Earlier email, 7 February 2027: Alex cannot attend Monday 8 February "
        "and asks about Thursday instead; a follow-up says Saturday 13 February would be better. "
        "Treat the new email as the latest request, which can change earlier preferences.",
        "notice": CATALOG["booking"]["notice"],
        "makeup_policy": "The example policy requires absence notice before class starts "
        "and a replacement no harder than the student's recorded attendance level. "
        "Other makeup entitlement or credit rules are unspecified.",
        "session": CUSTOM_SESSION,
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
    },
    "jules": {
        "student": "Jules Park has no recorded level or enrolment. "
        "Do not infer placement or eligibility.",
        "history": "Jules previously wrote: I have never danced before. When and where is the "
        "Thursday class? What does a trial cost, and what should I wear?",
        "session": CUSTOM_SESSION,
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
    },
    "833efaed-1e89-5f89-8b47-cb9cbcf3399c": {
        "student": "Maya Chen has a recorded Level 2 and an active enrolment. "
        "Do not infer attendance or makeup eligibility.",
        "history": "Maya previously wrote: I will miss Monday 8 February. "
        "Is Saturday 13 February an option?",
        "session": CUSTOM_SESSION,
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
    },
    "60bbb539-91bc-5858-80f5-a1b6ae915aae": {
        "student": "Noah Ellis has a recorded Level 2 and an active enrolment. "
        "Do not infer attendance or makeup eligibility.",
        "history": "Noah previously wrote: Could I arrange a makeup class? "
        "No absence or preferred date was provided.",
        "session": CUSTOM_SESSION,
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
    },
    "2eca4988-037e-54f9-9668-59ee06b2888b": {
        "student": "Riley James has no recorded level or enrolment. "
        "Do not infer placement or eligibility.",
        "history": "Riley previously wrote: Could you help me choose a class?",
        "session": CUSTOM_SESSION,
        "clothing": CATALOG["document"]["clothing"],
        "missing_fee": CATALOG["document"]["missing_fee"],
    },
}
