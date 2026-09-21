import re

import spacy


# ============================================================
# LOAD NLP
# ============================================================

nlp = spacy.load(
    "en_core_web_sm"
)


# ============================================================
# PATTERNS
# ============================================================

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
)

CALL_PATTERN = re.compile(
    r"\b([A-Z][a-z]+)\s+"
    r"(?:called|calls|call)\s+"
    r"([A-Z][a-z]+)\b",
    re.IGNORECASE,
)

USED_PATTERN = re.compile(
    r"\b([A-Z][a-z]+)\s+"
    r"(?:used|uses|use)\s+"
    r"((?:\+91[\s-]?)?[6-9]\d{9})\b",
    re.IGNORECASE,
)

LOCATION_PATTERN = re.compile(
    r"\b(?:in|from|at|near)\s+"
    r"([A-Z][a-z]+)\b",
    re.IGNORECASE,
)

KNOWN_LOCATIONS = {
    "kochi",
    "mumbai",
    "delhi",
    "bangalore",
    "bengaluru",
    "chennai",
    "hyderabad",
    "pune",
    "thrissur",
    "kerala",
    "india",
}


# ============================================================
# PHONE NORMALIZATION
# ============================================================

def normalize_phone(phone):

    digits = re.sub(
        r"\D",
        "",
        phone,
    )

    if (
        len(digits) == 12
        and digits.startswith("91")
    ):

        digits = digits[-10:]

    return digits


# ============================================================
# EXTRACT PHONES
# ============================================================

def extract_phones(text):

    return sorted(
        {
            normalize_phone(phone)
            for phone in PHONE_PATTERN.findall(
                text
            )
        }
    )


# ============================================================
# FIND PERSON CANDIDATES
# ============================================================

def get_person_candidates(text):

    candidates = []

    doc = nlp(text)

    # --------------------------------------------------------
    # spaCy PERSON entities
    # --------------------------------------------------------

    for ent in doc.ents:

        if ent.label_ == "PERSON":

            name = ent.text.strip()

            if (
                name
                and name.lower()
                not in {
                    "contact",
                    "case",
                }
                and name not in candidates
            ):

                candidates.append(
                    name
                )

    # --------------------------------------------------------
    # Capitalized-name fallback
    # --------------------------------------------------------

    capitalized_words = re.findall(
        r"\b[A-Z][a-z]{2,}\b",
        text,
    )

    for word in capitalized_words:

        lower_word = word.lower()

        if lower_word in KNOWN_LOCATIONS:
            continue

        if lower_word in {
            "contact",
            "case",
            "called",
            "call",
            "calls",
            "used",
            "uses",
            "use",
        }:

            continue

        if word not in candidates:

            candidates.append(
                word
            )

    return candidates


# ============================================================
# CALLED RELATIONSHIPS
# ============================================================

def extract_called_relationships(
    text
):

    relationships = []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    for sentence in sentences:

        match = CALL_PATTERN.search(
            sentence
        )

        if not match:
            continue

        caller = match.group(1).strip()
        receiver = match.group(2).strip()

        if (
            caller.lower()
            in KNOWN_LOCATIONS
        ):
            continue

        if (
            receiver.lower()
            in KNOWN_LOCATIONS
        ):
            continue

        relationships.append(
            {
                "from": caller,
                "type": "called",
                "to": receiver,
                "confidence": 0.90,
                "date": None,
                "source": "Rule-based extraction",
            }
        )

    return relationships


# ============================================================
# PHONE RELATIONSHIPS
# ============================================================

def extract_phone_relationships(
    text
):

    relationships = []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    # --------------------------------------------------------
    # Remember the most recent person
    # --------------------------------------------------------

    last_known_person = None

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        # ----------------------------------------------------
        # Explicit "person used phone"
        # ----------------------------------------------------

        used_match = USED_PATTERN.search(
            sentence
        )

        if used_match:

            person = (
                used_match.group(1).strip()
            )

            phone = normalize_phone(
                used_match.group(2)
            )

            relationships.append(
                {
                    "from": person,
                    "type": "used",
                    "to": phone,
                    "confidence": 0.96,
                    "date": None,
                    "source": "Rule-based extraction",
                }
            )

            last_known_person = person

            continue

        # ----------------------------------------------------
        # Look for phones
        # ----------------------------------------------------

        phones = extract_phones(
            sentence
        )

        # ----------------------------------------------------
        # Update person from current sentence
        # ----------------------------------------------------

        candidates = get_person_candidates(
            sentence
        )

        if candidates:

            last_known_person = candidates[0]

        # ----------------------------------------------------
        # Phone on its own / Contact: phone
        # ----------------------------------------------------

        if phones and last_known_person:

            # Avoid treating a person-name sentence as
            # multiple unrelated people.

            for phone in phones:

                relationships.append(
                    {
                        "from": last_known_person,
                        "type": "used",
                        "to": phone,
                        "confidence": 0.86,
                        "date": None,
                        "source": "Context-based extraction",
                    }
                )

    return relationships


# ============================================================
# LOCATION RELATIONSHIPS
# ============================================================

def extract_location_relationships(
    text
):

    relationships = []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    for sentence in sentences:

        location_match = (
            LOCATION_PATTERN.search(
                sentence
            )
        )

        if not location_match:
            continue

        location = (
            location_match.group(1).strip()
        )

        if (
            location.lower()
            not in KNOWN_LOCATIONS
        ):

            continue

        candidates = get_person_candidates(
            sentence
        )

        if not candidates:
            continue

        person = candidates[0]

        relationships.append(
            {
                "from": person,
                "type": "located_in",
                "to": location,
                "confidence": 0.88,
                "date": None,
                "source": "Rule-based extraction",
            }
        )

    return relationships


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(
    relationships
):

    unique = []

    seen = set()

    for relationship in relationships:

        key = (
            relationship.get("from"),
            relationship.get("type"),
            relationship.get("to"),
        )

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            relationship
        )

    return unique


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_relationships(
    text
):

    relationships = []

    relationships.extend(
        extract_called_relationships(
            text
        )
    )

    relationships.extend(
        extract_phone_relationships(
            text
        )
    )

    relationships.extend(
        extract_location_relationships(
            text
        )
    )

    return remove_duplicates(
        relationships
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_text = (
        "Arjun called Meera in Kochi "
        "on 30 August 2026. "
        "Contact: 9987654321."
    )

    print()

    print(
        "======================================"
    )

    print(
        "RELATIONSHIP EXTRACTION TEST"
    )

    print(
        "======================================"
    )

    print()

    print(
        test_text
    )

    print()

    results = extract_relationships(
        test_text
    )

    if results:

        for relationship in results:

            print(
                f"{relationship['from']} "
                f"--[{relationship['type']}]--> "
                f"{relationship['to']}"
            )

    else:

        print(
            "No relationships detected."
        )

    print()