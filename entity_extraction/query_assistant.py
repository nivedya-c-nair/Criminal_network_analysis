import json
import os

from openai import OpenAI

from database import (
    initialize_database,
)

from sql_queries import (
    get_cases_for_entity,
    get_entity_connections,
    get_cross_case_entities,
    get_relationships_by_date,
    get_case_relationships,
    search_entities,
    get_cases_sharing_phone,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gpt-5.6-luna"


# ============================================================
# OPENAI CLIENT
# ============================================================

def get_client():

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENAI_API_KEY is not set."
        )

    return OpenAI(
        api_key=api_key
    )


# ============================================================
# ASK AI TO UNDERSTAND THE QUESTION
# ============================================================

def understand_question(
    question
):

    client = get_client()

    instructions = """
You are a query-understanding assistant for an
educational SQLite network-analysis project.

Your job is ONLY to classify the user's question
into one of the allowed query types and extract
the relevant parameter.

Allowed query types:

1. ENTITY_CASES
   Find the cases containing an entity.

2. ENTITY_CONNECTIONS
   Find all recorded relationships involving an entity.

3. CROSS_CASE
   Find entities appearing in multiple cases.

4. CASE_RELATIONSHIPS
   Find relationships belonging to a specific case.

5. DATE_RELATIONSHIPS
   Find relationships recorded on a specific date.

6. PHONE_CASES
   Find cases associated with a phone number.

7. ENTITY_SEARCH
   Search the entity database using partial text.

8. UNKNOWN
   Use when the question does not fit the supported queries.

Return ONLY valid JSON.

Format:

{
    "query_type": "ENTITY_CASES",
    "parameter": "Rahul"
}

For CROSS_CASE the parameter should be an empty string.

Do not answer the question yourself.
Do not invent data.
"""

    prompt = f"""
Classify this user question:

{question}
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=prompt,
    )

    text = response.output_text.strip()

    # --------------------------------------------------------
    # Clean possible markdown fences
    # --------------------------------------------------------

    if text.startswith(
        "```"
    ):

        text = text.replace(
            "```json",
            "",
        )

        text = text.replace(
            "```",
            "",
        )

        text = text.strip()

    try:

        result = json.loads(
            text
        )

    except json.JSONDecodeError:

        return {
            "query_type": "UNKNOWN",
            "parameter": "",
        }

    return result


# ============================================================
# NORMALIZE PHONE
# ============================================================

def normalize_phone(
    phone
):

    digits = "".join(
        character
        for character in str(phone)
        if character.isdigit()
    )

    if (
        digits.startswith("91")
        and len(digits) == 12
    ):

        digits = digits[-10:]

    return digits


# ============================================================
# EXECUTE SAFE QUERY
# ============================================================

def execute_query(
    query_type,
    parameter,
):

    parameter = str(
        parameter or ""
    ).strip()

    # --------------------------------------------------------
    # Entity → Cases
    # --------------------------------------------------------

    if query_type == "ENTITY_CASES":

        if not parameter:

            return {
                "error": "No entity was supplied."
            }

        results = get_cases_for_entity(
            parameter
        )

        return {
            "query_type": query_type,
            "parameter": parameter,
            "results": results,
        }

    # --------------------------------------------------------
    # Entity → Connections
    # --------------------------------------------------------

    if query_type == "ENTITY_CONNECTIONS":

        if not parameter:

            return {
                "error": "No entity was supplied."
            }

        results = get_entity_connections(
            parameter
        )

        return {
            "query_type": query_type,
            "parameter": parameter,
            "results": results,
        }

    # --------------------------------------------------------
    # Cross-case entities
    # --------------------------------------------------------

    if query_type == "CROSS_CASE":

        results = get_cross_case_entities()

        return {
            "query_type": query_type,
            "parameter": "",
            "results": results,
        }

    # --------------------------------------------------------
    # Case relationships
    # --------------------------------------------------------

    if query_type == "CASE_RELATIONSHIPS":

        if not parameter:

            return {
                "error": "No Case ID was supplied."
            }

        results = get_case_relationships(
            parameter
        )

        return {
            "query_type": query_type,
            "parameter": parameter,
            "results": results,
        }

    # --------------------------------------------------------
    # Date relationships
    # --------------------------------------------------------

    if query_type == "DATE_RELATIONSHIPS":

        if not parameter:

            return {
                "error": "No date was supplied."
            }

        results = get_relationships_by_date(
            parameter
        )

        return {
            "query_type": query_type,
            "parameter": parameter,
            "results": results,
        }

    # --------------------------------------------------------
    # Phone → Cases
    # --------------------------------------------------------

    if query_type == "PHONE_CASES":

        if not parameter:

            return {
                "error": "No phone number was supplied."
            }

        phone = normalize_phone(
            parameter
        )

        results = get_cases_sharing_phone(
            phone
        )

        return {
            "query_type": query_type,
            "parameter": phone,
            "results": results,
        }

    # --------------------------------------------------------
    # Entity search
    # --------------------------------------------------------

    if query_type == "ENTITY_SEARCH":

        if not parameter:

            return {
                "error": "No search text was supplied."
            }

        results = search_entities(
            parameter
        )

        return {
            "query_type": query_type,
            "parameter": parameter,
            "results": results,
        }

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    return {
        "query_type": "UNKNOWN",
        "parameter": parameter,
        "results": [],
    }


# ============================================================
# FORMAT RESULTS FOR AI
# ============================================================

def format_results(
    question,
    query_result,
):

    return json.dumps(
        {
            "user_question": question,
            "query_result": query_result,
        },
        indent=4,
        ensure_ascii=False,
    )


# ============================================================
# AI EXPLANATION
# ============================================================

def explain_results(
    question,
    query_result,
):

    client = get_client()

    result_text = format_results(
        question,
        query_result,
    )

    instructions = """
You are an AI assistant for an educational
network-analysis project using synthetic data.

Explain ONLY the results supplied to you.

Rules:

1. Do not invent information.
2. Do not add relationships that are not present.
3. Do not accuse people of crimes.
4. Do not determine guilt, innocence, or responsibility.
5. Use neutral language.
6. Clearly distinguish database records from interpretation.
7. If no results were found, say so clearly.
8. Keep the answer concise and easy to understand.
9. Treat confidence values as record-quality information,
   not proof.
10. Mention that the dataset is synthetic when appropriate.
"""

    prompt = f"""
User question:

{question}

Database result:

{result_text}

Explain the answer to the user.

Use these sections:

## Answer

Give the direct answer.

## Recorded Data

Summarize the relevant database records.

## Limitations

Mention important missing information or limits.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=prompt,
    )

    return response.output_text


# ============================================================
# PRINT RAW RESULTS
# ============================================================

def print_raw_results(
    query_result
):

    print()
    print(
        "------------------------------------------"
    )
    print(
        "DATABASE RESULT"
    )
    print(
        "------------------------------------------"
    )

    print(
        json.dumps(
            query_result,
            indent=4,
            ensure_ascii=False,
        )
    )


# ============================================================
# RUN ASSISTANT
# ============================================================

def run_assistant(
    question
):

    print()
    print(
        "Understanding your question..."
    )

    interpretation = understand_question(
        question
    )

    query_type = interpretation.get(
        "query_type",
        "UNKNOWN",
    )

    parameter = interpretation.get(
        "parameter",
        "",
    )

    print(
        f"Query type: {query_type}"
    )

    if parameter:

        print(
            f"Parameter: {parameter}"
        )

    print()

    if query_type == "UNKNOWN":

        return (
            "I couldn't map that question to one "
            "of the supported database investigations."
        )

    print(
        "Querying SQLite..."
    )

    query_result = execute_query(
        query_type,
        parameter,
    )

    if "error" in query_result:

        return (
            f"Database query error: "
            f"{query_result['error']}"
        )

    print(
        "Database query completed."
    )

    print_raw_results(
        query_result
    )

    print()
    print(
        "Generating explanation..."
    )

    explanation = explain_results(
        question,
        query_result,
    )

    return explanation


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print()
    print(
        "=========================================="
    )
    print(
        "       NATURAL LANGUAGE QUERY ASSISTANT"
    )
    print(
        "=========================================="
    )

    print()
    print(
        "Examples:"
    )

    print(
        "  Who is connected to Rahul?"
    )

    print(
        "  Which cases contain Rahul?"
    )

    print(
        "  Which entities appear in multiple cases?"
    )

    print(
        "  What relationships are in Case_102?"
    )

    print(
        "  What happened on 15 August 2026?"
    )

    print(
        "  Which cases use phone 9876543210?"
    )

    print()

    question = input(
        "Ask a question: "
    ).strip()

    if not question:

        print(
            "Please enter a question."
        )

        raise SystemExit

    try:

        answer = run_assistant(
            question
        )

        print()
        print(
            "=========================================="
        )
        print(
            "             AI ANSWER"
        )
        print(
            "=========================================="
        )

        print()
        print(
            answer
        )

        print()

    except Exception as exc:

        print()
        print(
            "ERROR"
        )
        print(
            "-----"
        )
        print(
            str(exc)
        )