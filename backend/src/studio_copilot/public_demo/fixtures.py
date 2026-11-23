"""Immutable fictional inputs for the public demonstration (not workspace data)."""

from studio_copilot.public_demo.additional_documents import PUBLIC_ADDITIONAL_DOCUMENTS

CLOTHING = (
    "Wear comfortable clothes you can move in, such as leggings and a fitted T-shirt. "
    "Socks are suitable for your first class; ballet shoes are optional."
)
SATURDAY_TRIAL_CLASSES = {
    1: "Adult Ballet Level 1, Saturday 13 February 2027 at 4 pm, Merri Ballet Brunswick",
    2: "Adult Ballet Level 2, Saturday 13 February 2027 at 6 pm, Merri Ballet Brunswick",
    3: "Adult Ballet Level 3, Saturday 13 February 2027 at 7:30 pm, Merri Ballet Brunswick",
}
PUBLIC_DOCUMENTS = [
    {
        "id": "beginner-clothing",
        "title": "Beginner clothing policy",
        "filename": "beginner-clothing.md",
        "content": (
            "# Beginner clothing policy\n\n"
            "## What to wear\n\n"
            "For adult beginners attending a first class: " + CLOTHING + " "
            "Choose clothing that allows you to bend, stretch and move comfortably. "
            "A fitted top can help the teacher see your alignment and offer useful guidance. "
            "You do not need to buy a new outfit before trying a class.\n\n"
            "## Footwear and preparation\n\n"
            "Socks are suitable for your first class; ballet shoes are optional. "
            "Tie long hair back so it stays away from your face, and bring water. "
            "If you have questions about footwear or what will work for you, ask the studio "
            "before your visit.\n\n"
            "## Related questions\n\n"
            "The first-class guide has more information about preparing for a visit. "
            "This clothing document does not specify trial fees; ask the studio to confirm "
            "the price and any conditions. Class placement should be confirmed with the teacher.\n"
        ),
        "revision": 1,
    },
    {
        "id": "studio-welcome",
        "title": "Studio welcome",
        "filename": "welcome.md",
        "content": (
            "# Welcome to Merri Ballet\n\n"
            "Our adult classes take place in Melbourne. We welcome people who are "
            "discovering ballet as well as dancers returning after time away. Our teachers "
            "aim to create a supportive environment where adults can learn at their own pace "
            "and ask questions about their practice.\n\n"
            "## Staying in touch\n\n"
            "Contact the studio if you would like to learn more about our classes or share "
            "feedback about your experience. When writing about a particular session, include "
            "its date and name so the team can find the relevant information. The studio team "
            "will refer individual questions to a teacher when more information is needed.\n\n"
            "## Our community\n\n"
            "Students bring different backgrounds and goals to class. Some are exploring a "
            "new activity, while others are returning to a familiar practice. We encourage "
            "everyone to communicate with the teacher and respect the people sharing the "
            "studio. This introduction is general information about the fictional studio.\n"
        ),
        "revision": 1,
    },
    {
        "id": "first-class-guide",
        "title": "Your first ballet class",
        "filename": "first-class.md",
        "content": (
            "# Your first ballet class\n\n"
            "## Choosing a class\n\n"
            "Adult beginners are welcome to ask the studio for help choosing a class. "
            "Tell us whether you have danced before and which class interests you. "
            "The adult class information document describes the example levels and sessions. "
            "A particular class placement needs to be confirmed with the teacher.\n\n"
            "## Getting ready\n\n"
            "Bring water and tie long hair back. Wear comfortable clothes you can move in. "
            "Socks are suitable for a first class and ballet shoes are optional. "
            "Leggings and a fitted T-shirt are examples of suitable clothing; you do not "
            "need to purchase a special outfit before trying a class.\n\n"
            "## Before you attend\n\n"
            "Check the date, time and location with the studio, and let the teacher know if "
            "you have questions about participating. Availability can change, so a suggested "
            "session is not a confirmed booking. The teacher reviews and completes the booking.\n\n"
            "If you would like to know the trial price or conditions, ask the studio. "
            "The example documents do not specify a trial fee.\n"
        ),
        "revision": 1,
    },
    {
        "id": "makeup-guidelines",
        "title": "Absences and makeup classes",
        "filename": "absences-and-makeup.md",
        "content": (
            "# Absences and makeup classes\n\n"
            "## Letting us know\n\n"
            "Tell the studio about an absence before the class starts. Include the date of "
            "the class you expect to miss and, if you have one in mind, the date and class "
            "you would like to attend instead. This helps the teacher find the right records.\n\n"
            "## Checking a possible makeup\n\n"
            "A suggested makeup class must not be harder than the student's recorded "
            "attendance level. The teacher needs to check the student's attendance and the "
            "details of the missed class; a student's general experience or enrolment alone "
            "does not establish the recorded attendance level.\n\n"
            "Use the session roster to check available places and the student's makeup record "
            "to check approval status. Availability may change while a request is being "
            "reviewed. A suggested class or a request awaiting approval does not reserve "
            "a place. The teacher reviews the request before a booking is confirmed.\n\n"
            "## Questions that need follow-up\n\n"
            "If the absence date, preferred class or relevant record is missing, ask for "
            "the information needed to review the request. Refer any unresolved credit or "
            "entitlement to the teacher. This guide does not specify additional credit "
            "limits, expiry dates or fees.\n"
        ),
        "revision": 2,
    },
    {
        "id": "class-information",
        "title": "Adult class information",
        "filename": "adult-class-information.md",
        "content": (
            "# Adult class information\n\n"
            "## Choosing a level\n\n"
            "Level 1 is for beginners, Level 2 is intermediate, and Level 3 is advanced. "
            "If you are unsure which class suits you, tell the studio about your previous "
            "dance experience and ask for guidance. The teacher confirms placement; a "
            "timetable listing alone does not establish that a class is suitable for you.\n\n"
            "## Example Saturday trial options\n\n"
            "The following are fictional sessions used in this demonstration:\n\n"
            + "\n".join(f"- {description}" for description in SATURDAY_TRIAL_CLASSES.values())
            + "\n\n## Enquiries and bookings\n\n"
            "When enquiring, include the level and session you are interested in and any "
            "relevant experience. Class availability can change. A place is confirmed only "
            "after the teacher has reviewed and completed the booking; asking about a class "
            "or receiving a suggestion does not reserve a place.\n\n"
            "For a first visit, see the beginner clothing policy and first-class guide. "
            "The trial fee and any conditions are not specified in this example; the teacher "
            "must confirm them before a price is quoted.\n"
        ),
        "revision": 2,
    },
    {
        "id": "trials-and-fees",
        "title": "Trial classes and fees",
        "filename": "trials-and-fees.md",
        "content": (
            "# Trial classes and fees\n\n"
            "## Asking about a trial\n\n"
            "A student may ask the studio about trying a class. When you get in touch, "
            "it is helpful to mention your dance experience, the level you are considering "
            "and the session you would like to attend. The teacher can help confirm the "
            "appropriate placement and check the availability of the requested class.\n\n"
            "## Price and conditions\n\n"
            "The trial fee is not specified in the example studio information. The teacher "
            "must confirm the price and any applicable conditions before giving a quote. "
            "Do not assume a trial is free, apply a fee from another class, or infer payment "
            "or refund conditions from this document. Ask the studio when those details matter.\n\n"
            "## Confirming a place\n\n"
            "A class suggestion or a question about a trial is not a booking. Availability "
            "may change, and a place is confirmed only after the teacher has reviewed and "
            "completed the booking. The adult class information document lists the fictional "
            "sessions used in the demo; the first-class guide covers what to bring and wear.\n"
        ),
        "revision": 1,
    },
]

PUBLIC_DOCUMENTS.extend(PUBLIC_ADDITIONAL_DOCUMENTS)

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
