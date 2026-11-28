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
            + "\n\nLevel 1 is for beginners, Level 2 is intermediate, and Level 3 is advanced. "
            "For a real class, the teacher confirms placement and completes the booking.\n\n"
            "## Enquiries and bookings\n\n"
            "When enquiring, include the level and session you are interested in and any "
            "relevant experience. Class availability can change. A place is confirmed only "
            "after the teacher has reviewed and completed the booking; asking about a class "
            "or receiving a suggestion does not reserve a place.\n\n"
            "For a first visit, see the beginner clothing policy and first-class guide. "
            "The trial fee and any conditions are not specified in this example; the teacher "
            "must confirm them before a price is quoted.\n\n"
            "In this demo, a clear request for one eligible trial with an open place can "
            "complete automatically in the simulation. Class availability can change.\n"
        ),
        "revision": 3,
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
