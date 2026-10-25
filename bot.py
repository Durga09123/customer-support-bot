"""Rule-based NLP engine for the Fresh Fruit Shop customer support bot.

Pipeline: normalise text -> tokenise (quantities, fruits, words)
-> fuzzy-match fruit names -> pair quantities with fruits -> build a reply.
Only the Python standard library is used, so it runs anywhere (including Vercel).
"""

import re
from difflib import get_close_matches

# ---------------------------------------------------------------- catalogue
CATALOG = {
    "banana": ("Banana", 100),
    "orange": ("Orange", 120),
    "mango": ("Mango", 150),
    "grapes": ("Grapes", 140),
    "watermelon": ("Watermelon", 40),
    "pineapple": ("Pineapple", 80),
    "guava": ("Guava", 90),
    "papaya": ("Papaya", 70),
    "pomegranate": ("Pomegranate", 200),
    "pear": ("Pear", 180),
    "lemon": ("Lemon", 100),
    "kiwi": ("Kiwi", 350),
    "strawberry": ("Strawberry", 300),
    "sapota": ("Sapota", 100),
    "dragonfruit": ("Dragon fruit", 250),
    "apple": ("Apple", 200),
}

ALIASES = {"chikoo": "sapota", "grape": "grapes", "dragon": "dragonfruit"}

MAX_KG = 100

# Words that are never treated as fruit names or "unknown items".
STOP = set(
    """i me my we you your is are am it this that the a an of and or to for in on at
    with do does have has can could would will please pls kindly want need like buy get
    order give send show tell what which how much many price prices cost rate rates
    available availability stock instock any some fresh today now there here kg kgs kilo
    kilos gram grams total bill hi hello hey hii thanks thank bye help list menu fruit
    fruits all view check about so also more another plus just only yes no ok okay sure
    half quarter is are was were be been
    """.split()
)
FILLER = {"of", "and", "with", "plus", "a", "an", "the", "some", "please", "pls", "also"}

QUERY_HINT = re.compile(r"\b(available|have|price|cost|rate|stock|buy|want|need|how much)\b")
GREETING = re.compile(r"^(hi+|hello+|hey+|vanakkam|good\s+(morning|afternoon|evening))\b")
THANKS = re.compile(r"\b(thanks?|thank you|nandri)\b")
GOODBYE = re.compile(r"\b(bye|goodbye|see you|good night)\b")
HELP = re.compile(r"\b(help|what can you do|options|how does this work)\b")
LISTING = re.compile(r"\b(list|menu|catalog(ue)?|all fruits|fruits|view|show)\b")

TOKEN_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kgs?|kilograms?|kilos?|grams?|gms?|g)?\b|([a-z]+)"
)


# ------------------------------------------------------------------ helpers
def money(amount):
    amount = round(amount, 2)
    if amount == int(amount):
        return f"₹{int(amount):,}"
    return f"₹{amount:,.2f}"


def qty_text(kg):
    return f"{int(round(kg * 1000))} g" if kg < 1 else f"{kg:g} kg"


def normalise(text):
    text = text.lower()
    text = re.sub(r"dragon\s*-?\s*fruits?", "dragonfruit", text)
    text = re.sub(r"half\s*(a\s*)?(kg|kilo)s?", "0.5 kg", text)
    text = re.sub(r"quarter\s*(of\s*a\s*)?(kg|kilo)s?", "0.25 kg", text)
    return text


def to_fruit(word):
    """Return the catalogue key for a word (handles plurals and typos)."""
    if word in CATALOG:
        return word
    if word in ALIASES:
        return ALIASES[word]

    stems = []
    if word.endswith("ies"):
        stems.append(word[:-3] + "y")
    if word.endswith("es"):
        stems.append(word[:-2])
    if word.endswith("s"):
        stems.append(word[:-1])
    for stem in stems:
        if stem in CATALOG:
            return stem
        if stem in ALIASES:
            return ALIASES[stem]

    if len(word) >= 4 and word not in STOP:
        match = get_close_matches(word, list(CATALOG) + list(ALIASES), n=1, cutoff=0.82)
        if match:
            return ALIASES.get(match[0], match[0])
    return None


def tokenise(text):
    """Turn text into [("qty", kg) | ("fruit", key) | ("word", w)] tokens."""
    tokens = []
    for m in TOKEN_RE.finditer(text):
        if m.group(1):
            value = float(m.group(1))
            unit = m.group(2) or "kg"  # a bare number is taken as kg
            tokens.append(("qty", value / 1000 if unit.startswith("g") else value))
        else:
            word = m.group(3)
            key = None if word in STOP else to_fruit(word)
            tokens.append(("fruit", key) if key else ("word", word))
    return tokens


def pair_items(tokens):
    """Attach each quantity to the nearest fruit: the one before it, else after it."""
    tokens = [t for t in tokens if not (t[0] == "word" and t[1] in FILLER)]
    used, items = set(), {}
    for i, (kind, value) in enumerate(tokens):
        if kind != "fruit":
            continue
        qty_index = None
        if i > 0 and tokens[i - 1][0] == "qty" and (i - 1) not in used:
            qty_index = i - 1
        elif i + 1 < len(tokens) and tokens[i + 1][0] == "qty" and (i + 1) not in used:
            qty_index = i + 1
        kg = None
        if qty_index is not None:
            used.add(qty_index)
            kg = tokens[qty_index][1]
        if value in items and kg is not None:
            items[value] = (items[value] or 0) + kg
        elif value not in items:
            items[value] = kg
    return items


def reply(text, table=None, suggestions=None):
    return {
        "text": text,
        "table": table,
        "suggestions": suggestions or ["View fruits", "Help"],
    }


# ------------------------------------------------------------------ replies
def fruit_table():
    rows = [[name, f"{money(price)} / kg"] for name, price in CATALOG.values()]
    return {"headers": ["Fruit", "Price"], "rows": rows, "footer": None}


def help_reply():
    return reply(
        "I can help you with fruit availability, prices and orders. Try:\n"
        "• “Is apple available?”\n"
        "• “2 kg apple”  or  “500 g mango”\n"
        "• “apple 1kg mango 2kg” for a combined bill",
        suggestions=["View fruits", "Is apple available?", "2 kg apple, 500 g mango"],
    )


def build_order(items, unknown):
    rows, total, assumed = [], 0.0, []
    for key, kg in items.items():
        name, price = CATALOG[key]
        if kg is None:
            kg = 1.0
            assumed.append(name)
        if kg <= 0:
            continue
        if kg > MAX_KG:
            return reply(
                f"For {name} orders above {MAX_KG} kg, please contact the shop directly "
                "so we can confirm stock.",
            )
        amount = price * kg
        total += amount
        rows.append([name, qty_text(kg), money(amount)])

    if not rows:
        return reply("Please enter a quantity greater than zero, for example “2 kg apple”.")

    text = "Here is your order summary."
    if assumed:
        text += f" No quantity was given for {', '.join(assumed)}, so 1 kg was assumed."
    if unknown:
        text += f" We don’t stock: {', '.join(unknown)}."
    return reply(
        text,
        table={
            "headers": ["Fruit", "Quantity", "Amount"],
            "rows": rows,
            "footer": ["Total", "", money(total)],
        },
        suggestions=["View fruits", "Help"],
    )


def build_availability(items):
    if len(items) == 1:
        key = next(iter(items))
        name, price = CATALOG[key]
        return reply(
            f"{name} is available.\nPrice: {money(price)} / kg",
            suggestions=[f"1 kg {name.lower()}", "View fruits"],
        )
    rows = [[CATALOG[k][0], f"{money(CATALOG[k][1])} / kg"] for k in items]
    return reply(
        "All of these are available.",
        table={"headers": ["Fruit", "Price"], "rows": rows, "footer": None},
    )


def get_reply(message):
    message = (message or "").strip()
    if not message:
        return reply("Please type a message, for example “Is mango available?”.")

    text = normalise(message)
    tokens = tokenise(text)
    items = pair_items(tokens)
    words = [v for k, v in tokens if k == "word"]
    unknown = [w for w in words if w not in STOP and len(w) > 2]

    # 1. The customer mentioned at least one fruit we sell.
    if items:
        if any(kg is not None for kg in items.values()):
            return build_order(items, unknown)
        return build_availability(items)

    # 2. General intents.
    if GREETING.search(text):
        return reply(
            "Hello! Welcome to Fresh Fruit Shop. I can check availability, prices "
            "and prepare your bill.",
            suggestions=["View fruits", "Is apple available?", "Help"],
        )
    if THANKS.search(text):
        return reply("You’re welcome! Let me know if you need anything else.")
    if GOODBYE.search(text):
        return reply("Thank you for visiting Fresh Fruit Shop. Have a great day!")
    if HELP.search(text):
        return help_reply()
    if LISTING.search(text):
        return reply("Here are the fruits available today.", table=fruit_table(), suggestions=["Help"])

    # 3. Something we do not sell, or something we did not understand.
    if unknown and (QUERY_HINT.search(text) or len(words) <= 3):
        return reply(
            f"Sorry, “{unknown[0]}” is not available right now. "
            "You can see everything we have in stock below.",
            table=fruit_table(),
            suggestions=["Help"],
        )
    return reply(
        "I didn’t quite understand that. I can help with fruit availability, prices "
        "and orders.",
        suggestions=["View fruits", "Help"],
    )
