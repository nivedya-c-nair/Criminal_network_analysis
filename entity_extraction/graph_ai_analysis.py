import os

import networkx as nx
from openai import OpenAI

from database import (
    initialize_database,
    get_all_relationships,
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
# BUILD COMPLETE GRAPH
# ============================================================

def build_graph():

    relationships = get_all_relationships()

    graph = nx.Graph()

    for relationship in relationships:

        source = str(
            relationship.get(
                "from",
                ""
            )
        ).strip()

        target = str(
            relationship.get(
                "to",
                ""
            )
        ).strip()

        relationship_type = str(
            relationship.get(
                "type",
                "related_to"
            )
        )

        if not source or not target:

            continue

        graph.add_node(
            source
        )

        graph.add_node(
            target
        )

        graph.add_edge(
            source,
            target,
            relationship_type=relationship_type,
            case_id=relationship.get(
                "case_id"
            ),
            date=relationship.get(
                "date"
            ),
            confidence=relationship.get(
                "confidence"
            ),
            source=relationship.get(
                "source"
            ),
        )

    return graph


# ============================================================
# DIRECT CONNECTIONS
# ============================================================

def get_direct_connections(
    graph,
    entity_name,
):

    if entity_name not in graph:

        return []

    connections = []

    for neighbor in graph.neighbors(
        entity_name
    ):

        edge = graph[
            entity_name
        ][neighbor]

        connections.append(
            {
                "entity": neighbor,
                "relationship": edge.get(
                    "relationship_type"
                ),
                "case": edge.get(
                    "case_id"
                ),
                "date": edge.get(
                    "date"
                ),
                "confidence": edge.get(
                    "confidence"
                ),
            }
        )

    return connections


# ============================================================
# TWO-HOP CONNECTIONS
# ============================================================

def get_two_hop_connections(
    graph,
    entity_name,
):

    if entity_name not in graph:

        return []

    direct_neighbors = set(
        graph.neighbors(
            entity_name
        )
    )

    two_hop = set()

    for neighbor in direct_neighbors:

        for second_neighbor in graph.neighbors(
            neighbor
        ):

            if (
                second_neighbor != entity_name
                and second_neighbor
                not in direct_neighbors
            ):

                two_hop.add(
                    second_neighbor
                )

    return sorted(
        two_hop
    )


# ============================================================
# GET CASES FOR ENTITY
# ============================================================

def get_entity_cases(
    entity_name,
):

    relationships = get_all_relationships()

    cases = set()

    for relationship in relationships:

        from_entity = str(
            relationship.get(
                "from",
                ""
            )
        )

        to_entity = str(
            relationship.get(
                "to",
                ""
            )
        )

        case_id = relationship.get(
            "case_id"
        )

        if not case_id:

            continue

        if (
            from_entity.lower()
            == entity_name.lower()
        ):

            cases.add(
                case_id
            )

        if (
            to_entity.lower()
            == entity_name.lower()
        ):

            cases.add(
                case_id
            )

    return sorted(
        cases
    )


# ============================================================
# BUILD GRAPH CONTEXT
# ============================================================

def build_graph_context(
    entity_name,
):

    graph = build_graph()

    direct_connections = (
        get_direct_connections(
            graph,
            entity_name
        )
    )

    two_hop_connections = (
        get_two_hop_connections(
            graph,
            entity_name
        )
    )

    cases = get_entity_cases(
        entity_name
    )

    network_degree = 0

    if entity_name in graph:

        network_degree = graph.degree(
            entity_name
        )

    return {
        "entity": entity_name,
        "cases": cases,
        "direct_connections": direct_connections,
        "two_hop_connections": (
            two_hop_connections
        ),
        "network_degree": network_degree,
    }


# ============================================================
# FORMAT GRAPH CONTEXT
# ============================================================

def format_graph_context(
    context,
):

    lines = []

    lines.append(
        f"Entity: {context['entity']}"
    )

    lines.append(
        "Cases: "
        + (
            ", ".join(
                context["cases"]
            )
            if context["cases"]
            else "None"
        )
    )

    lines.append(
        f"Network degree: "
        f"{context['network_degree']}"
    )

    lines.append("")

    lines.append(
        "DIRECT CONNECTIONS:"
    )

    direct_connections = (
        context[
            "direct_connections"
        ]
    )

    if direct_connections:

        for connection in direct_connections:

            lines.append(
                "- "
                f"{connection['entity']} | "
                f"relationship="
                f"{connection['relationship']} | "
                f"case="
                f"{connection['case']} | "
                f"date="
                f"{connection['date']} | "
                f"confidence="
                f"{connection['confidence']}"
            )

    else:

        lines.append(
            "- None"
        )

    lines.append("")

    lines.append(
        "TWO-HOP CONNECTIONS:"
    )

    two_hop = context[
        "two_hop_connections"
    ]

    if two_hop:

        for entity in two_hop:

            lines.append(
                f"- {entity}"
            )

    else:

        lines.append(
            "- None"
        )

    return "\n".join(
        lines
    )


# ============================================================
# AI GRAPH ANALYSIS
# ============================================================

def analyze_graph_with_ai(
    entity_name,
):

    context = build_graph_context(
        entity_name
    )

    formatted_context = (
        format_graph_context(
            context
        )
    )

    client = get_client()

    instructions = """
You are assisting with an educational network-analysis
project using synthetic data.

Analyze ONLY the network information supplied to you.

Rules:

1. Do not invent facts.
2. Do not invent relationships.
3. Do not accuse any person of criminal activity.
4. Do not determine guilt, innocence, or responsibility.
5. Clearly distinguish direct connections from two-hop
   connections.
6. A graph connection only means that the supplied dataset
   contains a recorded relationship.
7. Confidence values describe the supplied record and are
   not proof.
8. Use neutral and factual language.
9. Mention missing information when appropriate.
10. Treat the entire dataset as synthetic educational data.
"""

    prompt = f"""
Analyze the following network information for the entity:

{formatted_context}

Give the answer using exactly these sections:

## 1. Network Overview

Describe the entity's recorded position in the network.

## 2. Direct Connections

List and explain the recorded direct connections.

## 3. Two-Hop Connections

Explain which entities are reachable through another
entity in the supplied network.

## 4. Case Coverage

List the cases in which the entity appears.

## 5. Data Observations

Describe patterns that are directly visible in the data.

## 6. Limitations

Explain what the supplied data does not tell us.

Do not make claims about criminal behavior, guilt,
or responsibility.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=prompt,
    )

    return response.output_text


# ============================================================
# PRINT GRAPH INFORMATION
# ============================================================

def print_graph_context(
    entity_name,
):

    context = build_graph_context(
        entity_name
    )

    print()
    print(
        "=========================================="
    )
    print(
        "            GRAPH CONTEXT"
    )
    print(
        "=========================================="
    )

    print(
        f"Entity: "
        f"{context['entity']}"
    )

    print(
        "Cases: "
        + (
            ", ".join(
                context["cases"]
            )
            if context["cases"]
            else "None"
        )
    )

    print(
        f"Network degree: "
        f"{context['network_degree']}"
    )

    print()

    print(
        "Direct connections:"
    )

    if context[
        "direct_connections"
    ]:

        for connection in context[
            "direct_connections"
        ]:

            print(
                f"  - "
                f"{connection['entity']} "
                f"[{connection['relationship']}] "
                f"(Case: "
                f"{connection['case']})"
            )

    else:

        print(
            "  - None"
        )

    print()

    print(
        "Two-hop connections:"
    )

    if context[
        "two_hop_connections"
    ]:

        for entity in context[
            "two_hop_connections"
        ]:

            print(
                f"  - {entity}"
            )

    else:

        print(
            "  - None"
        )

    print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    initialize_database()

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
            "Building graph context..."
        )

        print_graph_context(
            entity_name
        )

        print(
            "Sending graph context to AI..."
        )

        analysis = analyze_graph_with_ai(
            entity_name
        )

        print()

        print(
            "=========================================="
        )

        print(
            "          AI GRAPH ANALYSIS"
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
            "-----"
        )

        print(
            str(exc)
        )