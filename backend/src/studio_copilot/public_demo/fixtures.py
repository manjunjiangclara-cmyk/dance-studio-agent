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

# All fictional students share the same studio document catalog.
for catalog in CUSTOM_CATALOG.values():
    catalog.update(
        first_class=PUBLIC_DOCUMENTS[2]["content"],
        makeup_guide=PUBLIC_DOCUMENTS[3]["content"],
        class_information=PUBLIC_DOCUMENTS[4]["content"],
        trials_and_fees=PUBLIC_DOCUMENTS[5]["content"],
        welcome=PUBLIC_DOCUMENTS[1]["content"],
    )
