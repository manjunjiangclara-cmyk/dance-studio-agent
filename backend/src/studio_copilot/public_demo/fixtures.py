"""Immutable fictional inputs for the public demonstration (not workspace data)."""

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
            "Use the session roster to check available places and the student's makeup record "
            "to check approval status. A suggested class or a request awaiting approval does "
            "not reserve a place. Refer any unresolved credit or entitlement to the teacher.\n"
        ),
        "revision": 2,
    },
    {
        "id": "class-information",
        "title": "Adult class information",
        "filename": "adult-class-information.md",
        "content": (
            "# Adult class information\n\n"
            "Fictional Saturday trial options:\n"
            + "\n".join(f"- {description}" for description in SATURDAY_TRIAL_CLASSES.values())
            + "\n\nLevel 1 is for beginners, Level 2 is intermediate, and Level 3 is advanced. "
            "For a real class, the teacher confirms placement and completes the booking.\n\n"
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
            "A student may ask the studio about trying a class. The trial fee is not "
            "specified in the example studio information. The teacher must confirm the "
            "price and any applicable conditions before giving a quote.\n"
        ),
        "revision": 1,
    },
]
