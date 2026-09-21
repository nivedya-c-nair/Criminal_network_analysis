import os

from openai import OpenAI

from case_report import (
    generate_entity_report,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gpt-5.6-luna"


# ============================================================
# CREATE OPENAI CLIENT
# ============================================================

def get_client():
    """
    Create an OpenAI client using the OPENAI_API_KEY
    environment variable.
    """

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENAI_API_KEY environment variable "
            "was not found."
        )

    return OpenAI(
        api_key=api_key
    )


# ============================================================
# AI ANALYSIS
# ============================================================

def analyze_case_report(
    report,
):
    """
    Send a structured database report to the AI
    and request a factual natural-language analysis.
    """

    client = get_client()

    instructions = """
You are an AI assistant helping analyze a synthetic
network-analysis dataset for an educational software project.

Your task is to summarize ONLY the information explicitly
contained in the supplied report.

Rules:

1. Do not invent facts.
2. Do not claim that a person committed a crime.
3. Do not determine guilt, innocence, or responsibility.
4. Clearly distinguish recorded facts from possible patterns.
5. Treat confidence values as data-quality indicators,
   not proof.
6. Mention cross-case connections when they exist.
7. Keep the explanation structured and easy to understand.
8. If information is missing, say that it is missing.
9. Use neutral language.
10. The dataset is synthetic and for learning purposes.
"""

    user_prompt = f"""
Analyze the following synthetic entity investigation report.

REPORT
------
{report}

Provide the response using these sections:

1. Entity Overview
2. Recorded Cases
3. Recorded Relationships
4. Timeline
5. Cross-Case Connections
6. Data Observations
7. Important Limitations

Under "Data Observations", describe patterns that are directly
visible in the records. Do not make accusations or conclusions
about criminal activity.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=user_prompt,
    )

    return response.output_text


# ============================================================
# ENTITY → AI ANALYSIS
# ============================================================

def analyze_entity(
    entity_name,
):
    """
    Generate a database report and send it to the AI.
    """

    report = generate_entity_report(
        entity_name
    )

    analysis = analyze_case_report(
        report
    )

    return analysis


# ============================================================
# MAIN PROGRAM
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )
    print(
        "       AI CASE ANALYSIS"
    )
    print(
        "=========================================="
    )

    entity_name = input(
        "Enter entity name: "
    ).strip()

    if not entity_name:

        print(
            "Please enter an entity name."
        )

        raise SystemExit

    try:

        print()
        print(
            "Generating database report..."
        )

        report = generate_entity_report(
            entity_name
        )

        print(
            "Sending report to AI..."
        )

        analysis = analyze_case_report(
            report
        )

        print()
        print(
            "=========================================="
        )
        print(
            "            AI ANALYSIS"
        )
        print(
            "=========================================="
        )

        print()
        print(
            analysis
        )

        print()
        print(
            "=========================================="
        )

    except Exception as exc:

        print()
        print(
            "ERROR"
        )

        print(
            "----"
        )

        print(
            str(exc)
        )