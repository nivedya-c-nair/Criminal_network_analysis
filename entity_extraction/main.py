import spacy
import re
import networkx as nx
import matplotlib.pyplot as plt


# ==========================================
# 1. LOAD NLP MODEL
# ==========================================

nlp = spacy.load("en_core_web_sm")


# ==========================================
# 2. INVESTIGATION TEXT
# ==========================================

text = (
    "Rahul called Anu in Kochi on 15 August 2026. "
    "Contact: 9876543210."
)


# ==========================================
# 3. PROCESS TEXT USING SPACY
# ==========================================

doc = nlp(text)


# ==========================================
# 4. EXTRACT ENTITIES
# ==========================================

entities = []

for entity in doc.ents:

    # Ignore 10-digit numbers detected by spaCy
    if entity.text.isdigit() and len(entity.text) == 10:
        continue

    entities.append({
        "text": entity.text,
        "type": entity.label_
    })


# ==========================================
# 5. EXTRACT PHONE NUMBERS
# ==========================================

phone_pattern = r"\b\d{10}\b"

phones = re.findall(phone_pattern, text)

for phone in phones:

    entities.append({
        "text": phone,
        "type": "PHONE"
    })


# ==========================================
# 6. DISPLAY ENTITIES
# ==========================================

print("=== FINAL ENTITIES ===")

for entity in entities:
    print(entity)


# ==========================================
# 7. CREATE RELATIONSHIPS
# ==========================================

relationships = [

    # --------------------------------------
    # CASE 102
    # --------------------------------------

    {
        "from": "Rahul",
        "type": "called",
        "to": "Anu",

        "confidence": 0.94,

        "evidence": {
            "case": "Case_102",
            "date": "15 August 2026",
            "source": "Call record"
        }
    },

    {
        "from": "Rahul",
        "type": "used",
        "to": "9876543210",

        "confidence": 0.98,

        "evidence": {
            "case": "Case_102",
            "date": "15 August 2026",
            "source": "Phone record"
        }
    },

    {
        "from": "Rahul",
        "type": "located_in",
        "to": "Kochi",

        "confidence": 0.90,

        "evidence": {
            "case": "Case_102",
            "date": "15 August 2026",
            "source": "Investigation record"
        }
    },

    {
        "from": "Case_102",
        "type": "occurred_on",
        "to": "15 August 2026",

        "confidence": 1.00,

        "evidence": {
            "source": "Case record"
        }
    },


    # --------------------------------------
    # CASE 103
    # --------------------------------------

    {
        "from": "Arjun",
        "type": "used",
        "to": "9876543210",

        "confidence": 0.92,

        "evidence": {
            "case": "Case_103",
            "date": "20 August 2026",
            "source": "Phone record"
        }
    },

    {
        "from": "Arjun",
        "type": "called",
        "to": "Meera",

        "confidence": 0.91,

        "evidence": {
            "case": "Case_103",
            "date": "20 August 2026",
            "source": "Call record"
        }
    },

    {
        "from": "Case_103",
        "type": "occurred_on",
        "to": "20 August 2026",

        "confidence": 1.00,

        "evidence": {
            "source": "Case record"
        }
    }
]


# ==========================================
# 8. DISPLAY RELATIONSHIPS
# ==========================================

print()
print("=== RELATIONSHIPS ===")

for relationship in relationships:

    print("From:", relationship["from"])
    print("Relationship:", relationship["type"])
    print("To:", relationship["to"])
    print("Confidence:", relationship["confidence"])

    print(
        "Evidence:",
        relationship["evidence"]
    )

    print()


# ==========================================
# 9. CREATE GRAPH NODES
# ==========================================

nodes = []


# ------------------------------------------
# Add nodes from extracted entities
# ------------------------------------------

for entity in entities:

    nodes.append({
        "id": entity["text"],
        "type": entity["type"]
    })


# ------------------------------------------
# Add nodes from relationships
# ------------------------------------------

for relationship in relationships:

    from_node = relationship["from"]
    to_node = relationship["to"]


    # --------------------------------------
    # FROM NODE
    # --------------------------------------

    if not any(
        node["id"] == from_node
        for node in nodes
    ):

        if str(from_node).startswith("Case_"):

            nodes.append({
                "id": from_node,
                "type": "CASE"
            })

        else:

            nodes.append({
                "id": from_node,
                "type": "PERSON"
            })


    # --------------------------------------
    # TO NODE
    # --------------------------------------

    if not any(
        node["id"] == to_node
        for node in nodes
    ):

        # Phone
        if (
            str(to_node).isdigit()
            and len(str(to_node)) == 10
        ):

            nodes.append({
                "id": to_node,
                "type": "PHONE"
            })

        # Date
        elif "August" in str(to_node):

            nodes.append({
                "id": to_node,
                "type": "DATE"
            })

        # Location
        elif to_node == "Kochi":

            nodes.append({
                "id": to_node,
                "type": "LOCATION"
            })

        # Otherwise
        else:

            nodes.append({
                "id": to_node,
                "type": "PERSON"
            })


# ------------------------------------------
# Add CASE nodes from evidence
# ------------------------------------------

for relationship in relationships:

    case = relationship["evidence"].get("case")

    if case is not None:

        if not any(
            node["id"] == case
            for node in nodes
        ):

            nodes.append({
                "id": case,
                "type": "CASE"
            })


# ==========================================
# 10. CONVERT SPA CY TYPES
# ==========================================

for node in nodes:

    if node["type"] == "GPE":

        node["type"] = "LOCATION"


# ==========================================
# 11. DISPLAY NODES
# ==========================================

print("=== NODES ===")

for node in nodes:

    print(node)


# ==========================================
# 12. CREATE NETWORKX GRAPH
# ==========================================

graph = nx.Graph()


# ------------------------------------------
# Add nodes
# ------------------------------------------

for node in nodes:

    graph.add_node(
        node["id"],
        type=node["type"]
    )


# ------------------------------------------
# Add relationships
# ------------------------------------------

for relationship in relationships:

    graph.add_edge(

        relationship["from"],

        relationship["to"],

        relationship=relationship["type"],

        confidence=relationship["confidence"],

        evidence=relationship["evidence"]
    )


# ==========================================
# 13. DISPLAY NETWORKX GRAPH
# ==========================================

print()
print("=== NETWORKX GRAPH ===")

print(
    "Nodes:",
    list(graph.nodes)
)

print(
    "Edges:",
    list(graph.edges)
)

print()

print(
    "Number of nodes:",
    graph.number_of_nodes()
)

print(
    "Number of edges:",
    graph.number_of_edges()
)


# ==========================================
# 14. DISPLAY RELATIONSHIP EVIDENCE
# ==========================================

print()
print("=== RELATIONSHIP EVIDENCE ===")

for relationship in relationships:

    print()

    print("Relationship:")

    print(
        relationship["from"],
        "->",
        relationship["type"],
        "->",
        relationship["to"]
    )

    print(
        "Confidence:",
        relationship["confidence"] * 100,
        "%"
    )

    print(
        "Case:",
        relationship["evidence"].get(
            "case",
            "N/A"
        )
    )

    print(
        "Date:",
        relationship["evidence"].get(
            "date",
            "N/A"
        )
    )

    print(
        "Source:",
        relationship["evidence"].get(
            "source",
            "N/A"
        )
    )

    print("-" * 40)


# ==========================================
# 15. EVIDENCE LOOKUP
# ==========================================

print()
print("=== EVIDENCE LOOKUP ===")

search_from = input(
    "Enter FROM person/entity: "
)

search_to = input(
    "Enter TO person/entity: "
)

found = False


for relationship in relationships:

    if (
        relationship["from"].lower()
        == search_from.lower()

        and

        relationship["to"].lower()
        == search_to.lower()
    ):

        print()
        print("Relationship Found!")

        print(
            relationship["from"],
            "->",
            relationship["type"],
            "->",
            relationship["to"]
        )

        print(
            "Confidence:",
            relationship["confidence"] * 100,
            "%"
        )

        print(
            "Case:",
            relationship["evidence"].get(
                "case",
                "N/A"
            )
        )

        print(
            "Date:",
            relationship["evidence"].get(
                "date",
                "N/A"
            )
        )

        print(
            "Source:",
            relationship["evidence"].get(
                "source",
                "N/A"
            )
        )

        found = True

        break


if not found:

    print()
    print("No matching relationship found.")


# ==========================================
# 16. CROSS-CASE CORRELATION
# ==========================================

print()
print("=== CROSS-CASE CORRELATION ===")

entity_cases = {}
# ==========================================
# 17. GRAPH ANALYSIS
# ==========================================

print()
print("=== GRAPH ANALYSIS ===")

# Calculate degree centrality
centrality = nx.degree_centrality(graph)

# Display centrality of each node
for node, score in centrality.items():

    print(
        node,
        "->",
        round(score, 2)
    )


# ------------------------------------------
# Collect cases for each entity
# ------------------------------------------

for relationship in relationships:

    from_entity = relationship["from"]
    to_entity = relationship["to"]

    case = relationship["evidence"].get("case")


    # Ignore relationships without case
    if case is None:
        continue


    # --------------------------------------
    # FROM ENTITY
    # --------------------------------------

    if from_entity not in entity_cases:

        entity_cases[from_entity] = set()

    entity_cases[from_entity].add(case)


    # --------------------------------------
    # TO ENTITY
    # --------------------------------------

    if to_entity not in entity_cases:

        entity_cases[to_entity] = set()

    entity_cases[to_entity].add(case)


# ------------------------------------------
# Display entities in multiple cases
# ------------------------------------------

for entity, cases in entity_cases.items():

    if len(cases) > 1:

        print()

        print(
            "Entity:",
            entity
        )

        print(
            "Cases:",
            ", ".join(sorted(cases))
        )

        print(
            "Number of cases:",
            len(cases)
        )


# ==========================================
# 17. VISUALIZE GRAPH
# ==========================================

plt.figure(
    figsize=(12, 7)
)


# ------------------------------------------
# Create node positions
# ------------------------------------------

positions = nx.spring_layout(
    graph,
    seed=42
)


# ==========================================
# 18. NODE TYPES
# ==========================================

node_types = {

    "PERSON": "blue",

    "PHONE": "green",

    "LOCATION": "orange",

    "DATE": "purple",

    "CASE": "red",

    "UNKNOWN": "gray"
}


# ==========================================
# 19. DRAW DIFFERENT NODE TYPES
# ==========================================

for node_type, color in node_types.items():

    nodes_of_type = [

        node

        for node in graph.nodes

        if graph.nodes[node].get("type")
        == node_type

    ]


    if nodes_of_type:

        nx.draw_networkx_nodes(

            graph,

            positions,

            nodelist=nodes_of_type,

            node_color=color,

            node_size=2200

        )


# ==========================================
# 20. DRAW EDGES
# ==========================================

nx.draw_networkx_edges(

    graph,

    positions,

    width=2

)


# ==========================================
# 21. NODE LABELS
# ==========================================

node_labels = {}


for node in graph.nodes:

    node_type = graph.nodes[node].get(
        "type",
        "UNKNOWN"
    )

    node_labels[node] = (
        f"{node}\n({node_type})"
    )


nx.draw_networkx_labels(

    graph,

    positions,

    labels=node_labels,

    font_size=9

)


# ==========================================
# 22. EDGE LABELS
# ==========================================

edge_labels = nx.get_edge_attributes(

    graph,

    "relationship"

)


nx.draw_networkx_edge_labels(

    graph,

    positions,

    edge_labels=edge_labels,

    font_size=9

)


# ==========================================
# 23. TITLE
# ==========================================

plt.title(

    "Criminal Network Analysis",

    fontsize=16

)


# ==========================================
# 24. HIDE AXIS
# ==========================================

plt.axis("off")


# ==========================================
# 25. SHOW GRAPH
# ==========================================

plt.show()