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
