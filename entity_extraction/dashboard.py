import re
from collections import Counter
from datetime import datetime

import networkx as nx
import spacy
import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components

from database import (
    initialize_database,
    case_exists,
    insert_case,
    insert_entity,
    insert_relationship,
    get_all_cases,
    get_all_entities,
    get_all_relationships,
    get_database_counts,
)

from relationship_extraction import (
    extract_relationships,
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

from ai_analysis import (
    analyze_entity,
)

from graph_ai_analysis import (
    build_graph as build_ai_graph,
    build_graph_context,
    format_graph_context,
    analyze_graph_with_ai,
)

from query_assistant import (
    understand_question,
    execute_query,
    explain_results,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Criminal Network Analysis",
    page_icon="🕵️",
    layout="wide",
)


# ============================================================
# SESSION STATE
# ============================================================

if "pending_case" not in st.session_state:
    st.session_state.pending_case = None

if "ai_analysis" not in st.session_state:
    st.session_state.ai_analysis = None

if "ai_entity" not in st.session_state:
    st.session_state.ai_entity = None

if "graph_ai_result" not in st.session_state:
    st.session_state.graph_ai_result = None

if "graph_ai_entity" not in st.session_state:
    st.session_state.graph_ai_entity = None

if "assistant_answer" not in st.session_state:
    st.session_state.assistant_answer = None

if "assistant_result" not in st.session_state:
    st.session_state.assistant_result = None

if "assistant_question" not in st.session_state:
    st.session_state.assistant_question = None

if "assistant_query_type" not in st.session_state:
    st.session_state.assistant_query_type = None


# ============================================================
# DATABASE
# ============================================================

initialize_database()


# ============================================================
# CONSTANTS
# ============================================================

PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
)

DATE_PATTERNS = [
    re.compile(
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+"
        r"\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"
    ),
]

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

RELATIONSHIP_COLORS = {
    "called": "#ff7f0e",
    "used": "#1f77b4",
    "located_in": "#2ca02c",
    "occurred_on": "#9467bd",
}


# ============================================================
# NLP
# ============================================================

@st.cache_resource
def load_nlp():
    return spacy.load(
        "en_core_web_sm"
    )


try:

    nlp = load_nlp()

except Exception as exc:

    st.error(
        "spaCy model 'en_core_web_sm' could not be loaded."
    )

    st.code(
        "python -m spacy download en_core_web_sm"
    )

    st.exception(exc)
    st.stop()


# ============================================================
# ENTITY FUNCTIONS
# ============================================================

def normalize_phone(phone):

    digits = re.sub(
        r"\D",
        "",
        str(phone),
    )

    if (
        digits.startswith("91")
        and len(digits) == 12
    ):

        digits = digits[-10:]

    return digits


def extract_phones(text):

    return sorted(
        {
            normalize_phone(phone)
            for phone in PHONE_PATTERN.findall(
                text
            )
        }
    )


def extract_date(text):

    for pattern in DATE_PATTERNS:

        match = pattern.search(text)

        if match:
            return match.group(0)

    return None


def detect_entity_type(name):

    name = str(name).strip()

    if not name:
        return "OTHER"

    if name.startswith("Case_"):
        return "CASE"

    if re.fullmatch(
        r"\d{10}",
        name,
    ):
        return "PHONE"

    if name.lower() in KNOWN_LOCATIONS:
        return "LOCATION"

    for pattern in DATE_PATTERNS:

        if pattern.fullmatch(name):
            return "DATE"

    return "PERSON"


def extract_entities(
    text,
    case_id=None,
):

    doc = nlp(text)

    entities = []

    for ent in doc.ents:

        if ent.label_ in {
            "PERSON",
            "GPE",
            "LOC",
            "FAC",
            "ORG",
            "DATE",
        }:

            entities.append(
                {
                    "name": ent.text.strip(),
                    "type": ent.label_,
                    "case_id": case_id,
                }
            )

    for phone in extract_phones(text):

        entities.append(
            {
                "name": phone,
                "type": "PHONE",
                "case_id": case_id,
            }
        )

    date = extract_date(text)

    if date:

        entities.append(
            {
                "name": date,
                "type": "DATE",
                "case_id": case_id,
            }
        )

    if case_id:

        entities.append(
            {
                "name": case_id,
                "type": "CASE",
                "case_id": case_id,
            }
        )

    unique = []
    seen = set()

    for item in entities:

        key = (
            item["name"].lower(),
            item["type"],
            item.get("case_id"),
        )

        if key not in seen:

            seen.add(key)
            unique.append(item)

    return unique


# ============================================================
# GRAPH FUNCTIONS
# ============================================================

def build_graph(
    relationships,
):

    graph = nx.Graph()

    for relationship in relationships:

        source = str(
            relationship.get(
                "from",
                "Unknown",
            )
        )

        target = str(
            relationship.get(
                "to",
                "Unknown",
            )
        )

        relationship_type = str(
            relationship.get(
                "type",
                "related_to",
            )
        )

        graph.add_node(
            source,
            entity_type=detect_entity_type(
                source
            ),
        )

        graph.add_node(
            target,
            entity_type=detect_entity_type(
                target
            ),
        )

        if graph.has_edge(
            source,
            target,
        ):

            edge = graph[
                source
            ][target]

            old_types = edge.get(
                "relationship_types",
                [],
            )

            if (
                relationship_type
                not in old_types
            ):

                old_types.append(
                    relationship_type
                )

            edge[
                "relationship_types"
            ] = old_types

            edge["weight"] = (
                edge.get(
                    "weight",
                    1,
                )
                + 1
            )

        else:

            graph.add_edge(
                source,
                target,
                relationship_types=[
                    relationship_type
                ],
                weight=1,
            )

    return graph


def create_network(
    relationships,
    height="650px",
):

    graph = build_graph(
        relationships
    )

    network = Network(
        height=height,
        width="100%",
        bgcolor="#ffffff",
        font_color="#222222",
        notebook=False,
        directed=False,
    )

    network.barnes_hut(
        gravity=-3000,
        central_gravity=0.1,
        spring_length=160,
        spring_strength=0.04,
        damping=0.09,
    )

    for node in graph.nodes:

        entity_type = graph.nodes[
            node
        ].get(
            "entity_type",
            "PERSON",
        )

        if entity_type == "PERSON":

            color = "#ff9999"
            shape = "dot"

        elif entity_type == "PHONE":

            color = "#8ecae6"
            shape = "box"

        elif entity_type == "CASE":

            color = "#cdb4db"
            shape = "diamond"

        elif entity_type == "DATE":

            color = "#bde0fe"
            shape = "ellipse"

        else:

            color = "#90be6d"
            shape = "triangle"

        network.add_node(
            node,
            label=str(node),
            title=(
                f"Entity: {node}"
                f"<br>Type: {entity_type}"
            ),
            color=color,
            shape=shape,
        )

    for (
        source,
        target,
        attributes,
    ) in graph.edges(
        data=True
    ):

        relationship_types = (
            attributes.get(
                "relationship_types",
                [],
            )
        )

        relationship_text = ", ".join(
            relationship_types
        )

        first_relationship = (
            relationship_types[0]
            if relationship_types
            else ""
        )

        network.add_edge(
            source,
            target,
            label=relationship_text,
            title=(
                f"Relationship: "
                f"{relationship_text}"
            ),
            color=RELATIONSHIP_COLORS.get(
                first_relationship,
                "#888888",
            ),
        )

    return network.generate_html()


def show_network(
    relationships,
    height=700,
):

    if not relationships:

        st.info(
            "No relationships available."
        )

        return

    html = create_network(
        relationships,
        height=f"{height}px",
    )

    components.html(
        html,
        height=height,
        scrolling=True,
    )


# ============================================================
# LOAD DATABASE
# ============================================================

cases = get_all_cases()

all_relationships = (
    get_all_relationships()
)

database_entities = (
    get_all_entities()
)

database_counts = (
    get_database_counts()
)


# ============================================================
# ENTITY LIST
# ============================================================

all_entities = set()

for entity in database_entities:

    if entity.get("name"):

        all_entities.add(
            str(
                entity["name"]
            )
        )

for relationship in all_relationships:

    if relationship.get("from"):

        all_entities.add(
            str(
                relationship["from"]
            )
        )

    if relationship.get("to"):

        all_entities.add(
            str(
                relationship["to"]
            )
        )

all_entities = sorted(
    all_entities
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "🕵️ Criminal Network Analysis"
)

st.caption(
    "NLP + SQLite + SQL + Graph Analysis + AI"
)


# ============================================================
# DATABASE STATUS
# ============================================================

st.success(
    "🗄️ SQLite database connected"
)


m1, m2, m3 = st.columns(3)

m1.metric(
    "Cases",
    database_counts["cases"],
)

m2.metric(
    "Entities",
    database_counts["entities"],
)

m3.metric(
    "Relationships",
    database_counts["relationships"],
)


# ============================================================
# NEW INVESTIGATION
# ============================================================

st.divider()

st.subheader(
    "➕ New Investigation"
)

with st.form(
    "new_investigation"
):

    new_case_id = st.text_input(
        "Case ID",
        placeholder="Example: Case_106",
    )

    new_case_text = st.text_area(
        "Investigation Text",
        placeholder=(
            "Example: Rahul called Anu in Kochi "
            "on 15 September 2026. "
            "Contact: 9876543210."
        ),
        height=120,
    )

    analyze_button = st.form_submit_button(
        "🔎 Analyze Text"
    )


# ============================================================
# ANALYZE NEW CASE
# ============================================================

if analyze_button:

    case_id = new_case_id.strip()
    text = new_case_text.strip()

    if not case_id:

        st.warning(
            "Please enter a Case ID."
        )

    elif not text:

        st.warning(
            "Please enter investigation text."
        )

    elif case_exists(
        case_id
    ):

        st.warning(
            f"That Case ID already exists: "
            f"{case_id}"
        )

    else:

        try:

            extracted = extract_relationships(
                text
            )

            detected_date = extract_date(
                text
            )

            prepared = []

            for relationship in extracted:

                item = dict(
                    relationship
                )

                item["confidence"] = item.get(
                    "confidence",
                    0.80,
                )

                item["date"] = item.get(
                    "date"
                ) or detected_date

                item["source"] = item.get(
                    "source"
                ) or "Automatic extraction"

                prepared.append(
                    item
                )

            st.session_state.pending_case = {
                "case_id": case_id,
                "text": text,
                "relationships": prepared,
            }

            st.success(
                "Text analyzed successfully."
            )

        except Exception as exc:

            st.error(
                "Could not analyze the text."
            )

            st.exception(exc)


# ============================================================
# PENDING CASE PREVIEW
# ============================================================

if st.session_state.pending_case:

    pending = (
        st.session_state.pending_case
    )

    st.divider()

    st.subheader(
        f"📋 Review {pending['case_id']}"
    )

    pending_entities = extract_entities(
        pending["text"],
        pending["case_id"],
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            "**Detected Entities**"
        )

        entity_rows = []

        for entity in pending_entities:

            entity_rows.append(
                {
                    "Entity": entity[
                        "name"
                    ],
                    "Type": entity[
                        "type"
                    ],
                }
            )

        if entity_rows:

            st.dataframe(
                entity_rows,
                use_container_width=True,
                hide_index=True,
            )

    with col2:

        st.markdown(
            "**Extracted Relationships**"
        )

        relationship_rows = []

        for relationship in pending[
            "relationships"
        ]:

            relationship_rows.append(
                {
                    "From": relationship.get(
                        "from",
                        "",
                    ),
                    "Type": relationship.get(
                        "type",
                        "",
                    ),
                    "To": relationship.get(
                        "to",
                        "",
                    ),
                    "Confidence": relationship.get(
                        "confidence",
                        "",
                    ),
                    "Date": relationship.get(
                        "date",
                        "",
                    ),
                }
            )

        if relationship_rows:

            st.dataframe(
                relationship_rows,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No relationships detected."
            )

    st.markdown(
        "**Temporary Network**"
    )

    show_network(
        pending["relationships"],
        height=500,
    )

    save_col, cancel_col = (
        st.columns(2)
    )

    with save_col:

        if st.button(
            "💾 Save Case to SQLite",
            key="save_case",
        ):

            if case_exists(
                pending["case_id"]
            ):

                st.warning(
                    "That Case ID already exists."
                )

            else:

                inserted = insert_case(
                    pending["case_id"],
                    pending["text"],
                )

                if inserted:

                    for entity in pending_entities:

                        insert_entity(
                            name=entity[
                                "name"
                            ],
                            entity_type=entity[
                                "type"
                            ],
                            case_id=pending[
                                "case_id"
                            ],
                        )

                    for relationship in pending[
                        "relationships"
                    ]:

                        from_entity = (
                            relationship.get(
                                "from",
                                "",
                            )
                        )

                        to_entity = (
                            relationship.get(
                                "to",
                                "",
                            )
                        )

                        relationship_type = (
                            relationship.get(
                                "type",
                                "",
                            )
                        )

                        if (
                            from_entity
                            and to_entity
                            and relationship_type
                        ):

                            insert_relationship(
                                case_id=pending[
                                    "case_id"
                                ],
                                from_entity=from_entity,
                                relationship_type=(
                                    relationship_type
                                ),
                                to_entity=to_entity,
                                confidence=relationship.get(
                                    "confidence",
                                    0.80,
                                ),
                                date=relationship.get(
                                    "date"
                                ),
                                source=relationship.get(
                                    "source",
                                    "Automatic extraction",
                                ),
                            )

                            insert_entity(
                                name=from_entity,
                                entity_type=detect_entity_type(
                                    from_entity
                                ),
                                case_id=pending[
                                    "case_id"
                                ],
                            )

                            insert_entity(
                                name=to_entity,
                                entity_type=detect_entity_type(
                                    to_entity
                                ),
                                case_id=pending[
                                    "case_id"
                                ],
                            )

                    st.session_state.pending_case = None

                    st.success(
                        "✅ Case saved to SQLite!"
                    )

                    st.rerun()

    with cancel_col:

        if st.button(
            "❌ Cancel",
            key="cancel_case",
        ):

            st.session_state.pending_case = None
            st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "Filters"
)

case_options = [
    "All Cases"
] + sorted(
    [
        case["case_id"]
        for case in cases
    ]
)

selected_case = st.sidebar.selectbox(
    "Case",
    case_options,
)

entity_search = st.sidebar.text_input(
    "Search entity",
    placeholder="Rahul, Kochi...",
)


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_relationships = (
    all_relationships
)

if selected_case != "All Cases":

    filtered_relationships = [
        relationship
        for relationship
        in filtered_relationships
        if relationship.get(
            "case_id"
        )
        == selected_case
    ]

if entity_search.strip():

    query = entity_search.lower().strip()

    filtered_relationships = [
        relationship
        for relationship
        in filtered_relationships
        if (
            query
            in str(
                relationship.get(
                    "from",
                    "",
                )
            ).lower()
        )
        or (
            query
            in str(
                relationship.get(
                    "to",
                    "",
                )
            ).lower()
        )
    ]


filtered_graph = build_graph(
    filtered_relationships
)


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "🌐 Network Graph",
        "🔗 Relationships",
        "🔍 Cross-Case",
        "📊 Graph Analytics",
        "🕒 Timeline",
        "🧠 NLP Entities",
        "🕵️ Entity Investigation",
        "🗄️ SQL Investigation",
        "🤖 AI Analysis",
        "🧠 Graph AI",
        "💬 Query Assistant",
    ]
)


# ============================================================
# TAB 1 - NETWORK GRAPH
# ============================================================

with tabs[0]:

    st.subheader(
        "🌐 Network Graph"
    )

    show_network(
        filtered_relationships,
        height=700,
    )


# ============================================================
# TAB 2 - RELATIONSHIPS
# ============================================================

with tabs[1]:

    st.subheader(
        "🔗 Relationship Records"
    )

    if filtered_relationships:

        rows = []

        for relationship in (
            filtered_relationships
        ):

            rows.append(
                {
                    "Case": relationship.get(
                        "case_id",
                        "",
                    ),
                    "From": relationship.get(
                        "from",
                        "",
                    ),
                    "Type": relationship.get(
                        "type",
                        "",
                    ),
                    "To": relationship.get(
                        "to",
                        "",
                    ),
                    "Confidence": relationship.get(
                        "confidence",
                        "",
                    ),
                    "Date": relationship.get(
                        "date",
                        "",
                    ),
                    "Source": relationship.get(
                        "source",
                        "",
                    ),
                }
            )

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No relationship records found."
        )


# ============================================================
# TAB 3 - CROSS CASE
# ============================================================

with tabs[2]:

    st.subheader(
        "🔍 Cross-Case Analysis"
    )

    results = (
        get_cross_case_entities()
    )

    if results:

        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "### Inspect a repeated entity"
        )

        repeated_entity = st.selectbox(
            "Entity",
            [
                row["name"]
                for row in results
            ],
            key="cross_case_entity",
        )

        entity_cases = (
            get_cases_for_entity(
                repeated_entity
            )
        )

        st.write(
            f"Cases containing "
            f"**{repeated_entity}**:"
        )

        st.write(
            ", ".join(entity_cases)
        )

    else:

        st.info(
            "No cross-case entities found."
        )


# ============================================================
# TAB 4 - GRAPH ANALYTICS
# ============================================================

with tabs[3]:

    st.subheader(
        "📊 Graph Analytics"
    )

    if not filtered_graph.nodes:

        st.info(
            "No graph data available."
        )

    else:

        st.markdown(
            "### Degree Centrality"
        )

        centrality = nx.degree_centrality(
            filtered_graph
        )

        centrality_rows = []

        for entity, score in sorted(
            centrality.items(),
            key=lambda item: item[1],
            reverse=True,
        ):

            centrality_rows.append(
                {
                    "Entity": entity,
                    "Degree": filtered_graph.degree(
                        entity
                    ),
                    "Centrality": round(
                        score,
                        3,
                    ),
                }
            )

        st.dataframe(
            centrality_rows,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "### Shortest Path"
        )

        nodes = sorted(
            filtered_graph.nodes
        )

        if len(nodes) >= 2:

            c1, c2 = st.columns(2)

            with c1:

                source = st.selectbox(
                    "From",
                    nodes,
                    key="analytics_source",
                )

            with c2:

                target = st.selectbox(
                    "To",
                    nodes,
                    index=min(
                        1,
                        len(nodes) - 1,
                    ),
                    key="analytics_target",
                )

            if source != target:

                try:

                    path = nx.shortest_path(
                        filtered_graph,
                        source=source,
                        target=target,
                    )

                    st.success(
                        " → ".join(path)
                    )

                    st.write(
                        f"Path length: "
                        f"{len(path) - 1}"
                    )

                except nx.NetworkXNoPath:

                    st.warning(
                        "No path exists."
                    )

        st.markdown(
            "### Connected Components"
        )

        components_list = list(
            nx.connected_components(
                filtered_graph
            )
        )

        component_rows = []

        for number, component in enumerate(
            components_list,
            start=1,
        ):

            component_rows.append(
                {
                    "Component": number,
                    "Size": len(component),
                    "Entities": ", ".join(
                        sorted(component)
                    ),
                }
            )

        st.dataframe(
            component_rows,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB 5 - TIMELINE
# ============================================================

with tabs[4]:

    st.subheader(
        "🕒 Timeline"
    )

    timeline = []

    for relationship in (
        all_relationships
    ):

        timeline.append(
            {
                "Date": relationship.get(
                    "date",
                    "",
                ),
                "Case": relationship.get(
                    "case_id",
                    "",
                ),
                "From": relationship.get(
                    "from",
                    "",
                ),
                "Relationship": relationship.get(
                    "type",
                    "",
                ),
                "To": relationship.get(
                    "to",
                    "",
                ),
                "Confidence": relationship.get(
                    "confidence",
                    "",
                ),
            }
        )

    def timeline_key(item):

        raw = str(
            item.get(
                "Date",
                "",
            )
        )

        formats = [
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%B %d %Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
        ]

        for fmt in formats:

            try:

                return datetime.strptime(
                    raw,
                    fmt,
                )

            except ValueError:

                pass

        return datetime.max

    timeline.sort(
        key=timeline_key
    )

    if timeline:

        st.dataframe(
            timeline,
            use_container_width=True,
            hide_index=True,
        )

        counts = Counter(
            item["Relationship"]
            for item in timeline
        )

        st.markdown(
            "### Relationship Summary"
        )

        st.dataframe(
            [
                {
                    "Relationship": name,
                    "Count": count,
                }
                for name, count
                in counts.most_common()
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No timeline data available."
        )


# ============================================================
# TAB 6 - NLP ENTITIES
# ============================================================

with tabs[5]:

    st.subheader(
        "🧠 NLP Entities"
    )

    if database_entities:

        st.dataframe(
            database_entities,
            use_container_width=True,
            hide_index=True,
        )

        type_counts = Counter(
            entity["type"]
            for entity
            in database_entities
        )

        st.markdown(
            "### Entity Types"
        )

        st.dataframe(
            [
                {
                    "Type": entity_type,
                    "Count": count,
                }
                for entity_type, count
                in type_counts.items()
            ],
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No entities stored."
        )


# ============================================================
# TAB 7 - ENTITY INVESTIGATION
# ============================================================

with tabs[6]:

    st.subheader(
        "🕵️ Entity Investigation"
    )

    if not all_entities:

        st.info(
            "No entities available."
        )

    else:

        selected_entity = st.selectbox(
            "Select entity",
            all_entities,
            key="investigation_entity",
        )

        connections = (
            get_entity_connections(
                selected_entity
            )
        )

        entity_cases = (
            get_cases_for_entity(
                selected_entity
            )
        )

        connected_entities = set()

        for connection in connections:

            if (
                connection[
                    "from_entity"
                ]
                == selected_entity
            ):

                connected_entities.add(
                    connection[
                        "to_entity"
                    ]
                )

            if (
                connection[
                    "to_entity"
                ]
                == selected_entity
            ):

                connected_entities.add(
                    connection[
                        "from_entity"
                    ]
                )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Type",
            detect_entity_type(
                selected_entity
            ),
        )

        c2.metric(
            "Cases",
            len(entity_cases),
        )

        c3.metric(
            "Connections",
            len(connected_entities),
        )

        st.markdown(
            "### Cases"
        )

        st.write(
            ", ".join(entity_cases)
            if entity_cases
            else "No cases found."
        )

        st.markdown(
            "### Relationships"
        )

        if connections:

            st.dataframe(
                connections,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No relationships found."
            )


# ============================================================
# TAB 8 - SQL INVESTIGATION
# ============================================================

with tabs[7]:

    st.subheader(
        "🗄️ SQL Investigation"
    )

    sql_option = st.selectbox(
        "Choose query",
        [
            "Find cases for an entity",
            "Find all connections of an entity",
            "Find cross-case entities",
            "Find relationships by date",
            "Find relationships in a case",
            "Search entities",
            "Find cases sharing a phone",
        ],
        key="sql_option",
    )

    if sql_option == (
        "Find cases for an entity"
    ):

        value = st.text_input(
            "Entity name",
            placeholder="Rahul",
            key="sql_entity_cases",
        )

        if st.button(
            "Run Query",
            key="sql_button_1",
        ):

            results = get_cases_for_entity(
                value.strip()
            )

            st.dataframe(
                [
                    {
                        "Case": item
                    }
                    for item in results
                ],
                use_container_width=True,
                hide_index=True,
            )

    elif sql_option == (
        "Find all connections of an entity"
    ):

        value = st.text_input(
            "Entity name",
            placeholder="Rahul",
            key="sql_entity_connections",
        )

        if st.button(
            "Run Query",
            key="sql_button_2",
        ):

            results = get_entity_connections(
                value.strip()
            )

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
            )

    elif sql_option == (
        "Find cross-case entities"
    ):

        if st.button(
            "Run Query",
            key="sql_button_3",
        ):

            results = (
                get_cross_case_entities()
            )

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
            )

    elif sql_option == (
        "Find relationships by date"
    ):

        value = st.text_input(
            "Date",
            placeholder="15 August 2026",
            key="sql_date",
        )

        if st.button(
            "Run Query",
            key="sql_button_4",
        ):

            results = (
                get_relationships_by_date(
                    value.strip()
                )
            )

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
            )

    elif sql_option == (
        "Find relationships in a case"
    ):

        value = st.text_input(
            "Case ID",
            placeholder="Case_102",
            key="sql_case",
        )

        if st.button(
            "Run Query",
            key="sql_button_5",
        ):

            results = (
                get_case_relationships(
                    value.strip()
                )
            )

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
            )

    elif sql_option == (
        "Search entities"
    ):

        value = st.text_input(
            "Search",
            placeholder="Rah",
            key="sql_search",
        )

        if st.button(
            "Run Query",
            key="sql_button_6",
        ):

            results = search_entities(
                value.strip()
            )

            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
            )

    elif sql_option == (
        "Find cases sharing a phone"
    ):

        value = st.text_input(
            "Phone",
            placeholder="9876543210",
            key="sql_phone",
        )

        if st.button(
            "Run Query",
            key="sql_button_7",
        ):

            phone = normalize_phone(
                value
            )

            results = (
                get_cases_sharing_phone(
                    phone
                )
            )

            st.dataframe(
                [
                    {
                        "Case": item
                    }
                    for item in results
                ],
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# TAB 9 - AI ANALYSIS
# ============================================================

with tabs[8]:

    st.subheader(
        "🤖 AI Case Analysis"
    )

    st.write(
        "Generate a natural-language explanation "
        "from the structured database records."
    )

    if not all_entities:

        st.info(
            "No entities available."
        )

    else:

        ai_entity = st.selectbox(
            "Select entity",
            all_entities,
            key="ai_entity_select",
        )

        if st.button(
            "🤖 Generate AI Analysis",
            type="primary",
            key="generate_ai",
        ):

            with st.spinner(
                "Generating AI analysis..."
            ):

                try:

                    result = analyze_entity(
                        ai_entity
                    )

                    st.session_state.ai_analysis = (
                        result
                    )

                    st.session_state.ai_entity = (
                        ai_entity
                    )

                except Exception as exc:

                    st.error(
                        "AI analysis failed."
                    )

                    st.exception(exc)

        if (
            st.session_state.ai_analysis
            and st.session_state.ai_entity
        ):

            st.divider()

            st.markdown(
                f"### Analysis for "
                f"{st.session_state.ai_entity}"
            )

            st.markdown(
                st.session_state.ai_analysis
            )

            st.download_button(
                "📄 Download Analysis",
                data=st.session_state.ai_analysis,
                file_name=(
                    f"{st.session_state.ai_entity}"
                    "_ai_analysis.txt"
                ),
                mime="text/plain",
                key="download_ai",
            )


# ============================================================
# TAB 10 - GRAPH AI
# ============================================================

with tabs[9]:

    st.subheader(
        "🧠 Graph AI Analysis"
    )

    st.write(
        "AI analysis based on the entity's position "
        "inside the NetworkX graph."
    )

    if not all_entities:

        st.info(
            "No entities available."
        )

    else:

        graph_ai_entity = st.selectbox(
            "Select entity",
            all_entities,
            key="graph_ai_entity_select",
        )

        context = build_graph_context(
            graph_ai_entity
        )

        # ----------------------------------------------------
        # Network summary
        # ----------------------------------------------------

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Network Degree",
            context["network_degree"],
        )

        c2.metric(
            "Cases",
            len(context["cases"]),
        )

        c3.metric(
            "Direct Connections",
            len(
                context[
                    "direct_connections"
                ]
            ),
        )

        st.markdown(
            "### Direct Connections"
        )

        if context[
            "direct_connections"
        ]:

            direct_rows = []

            for connection in (
                context[
                    "direct_connections"
                ]
            ):

                direct_rows.append(
                    {
                        "Entity": connection[
                            "entity"
                        ],
                        "Relationship": connection[
                            "relationship"
                        ],
                        "Case": connection[
                            "case"
                        ],
                        "Date": connection[
                            "date"
                        ],
                        "Confidence": connection[
                            "confidence"
                        ],
                    }
                )

            st.dataframe(
                direct_rows,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No direct connections."
            )

        st.markdown(
            "### Two-Hop Connections"
        )

        if context[
            "two_hop_connections"
        ]:

            st.write(
                ", ".join(
                    context[
                        "two_hop_connections"
                    ]
                )
            )

        else:

            st.info(
                "No two-hop connections."
            )

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        if st.button(
            "🧠 Generate Graph AI Analysis",
            type="primary",
            key="generate_graph_ai",
        ):

            with st.spinner(
                "Analyzing graph..."
            ):

                try:

                    result = (
                        analyze_graph_with_ai(
                            graph_ai_entity
                        )
                    )

                    st.session_state.graph_ai_result = (
                        result
                    )

                    st.session_state.graph_ai_entity = (
                        graph_ai_entity
                    )

                except Exception as exc:

                    st.error(
                        "Graph AI analysis failed."
                    )

                    st.exception(exc)

        if (
            st.session_state.graph_ai_result
            and st.session_state.graph_ai_entity
        ):

            st.divider()

            st.markdown(
                f"### AI Graph Analysis for "
                f"{st.session_state.graph_ai_entity}"
            )

            st.markdown(
                st.session_state.graph_ai_result
            )

            st.download_button(
                "📄 Download Graph Analysis",
                data=st.session_state.graph_ai_result,
                file_name=(
                    f"{st.session_state.graph_ai_entity}"
                    "_graph_ai_analysis.txt"
                ),
                mime="text/plain",
                key="download_graph_ai",
            )

        with st.expander(
            "🔍 View structured graph data"
        ):

            st.code(
                format_graph_context(
                    context
                ),
                language="text",
            )


# ============================================================
# TAB 11 - QUERY ASSISTANT
# ============================================================

with tabs[10]:

    st.subheader(
        "💬 Natural-Language Query Assistant"
    )

    st.write(
        "Ask questions about the stored network "
        "using normal language."
    )

    st.info(
        "Examples: "
        "\"Who is connected to Rahul?\"  |  "
        "\"Which cases contain Rahul?\"  |  "
        "\"Which entities appear in multiple cases?\""
    )

    assistant_question = st.text_area(
        "Ask a question",
        placeholder=(
            "Example: Who is connected to Rahul?"
        ),
        height=100,
        key="assistant_input",
    )

    if st.button(
        "💬 Ask Assistant",
        type="primary",
        key="ask_assistant",
    ):

        if not assistant_question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "Understanding your question..."
            ):

                try:

                    interpretation = (
                        understand_question(
                            assistant_question.strip()
                        )
                    )

                    query_type = (
                        interpretation.get(
                            "query_type",
                            "UNKNOWN",
                        )
                    )

                    parameter = (
                        interpretation.get(
                            "parameter",
                            "",
                        )
                    )

                    st.session_state.assistant_question = (
                        assistant_question.strip()
                    )

                    st.session_state.assistant_query_type = (
                        query_type
                    )

                    if query_type == "UNKNOWN":

                        st.session_state.assistant_answer = (
                            "I couldn't map that question "
                            "to one of the supported "
                            "database investigations."
                        )

                        st.session_state.assistant_result = None

                    else:

                        with st.spinner(
                            "Querying SQLite..."
                        ):

                            query_result = execute_query(
                                query_type,
                                parameter,
                            )

                        if "error" in query_result:

                            st.session_state.assistant_answer = (
                                query_result["error"]
                            )

                            st.session_state.assistant_result = (
                                query_result
                            )

                        else:

                            with st.spinner(
                                "Generating explanation..."
                            ):

                                answer = explain_results(
                                    assistant_question.strip(),
                                    query_result,
                                )

                            st.session_state.assistant_answer = (
                                answer
                            )

                            st.session_state.assistant_result = (
                                query_result
                            )

                except Exception as exc:

                    st.error(
                        "Query Assistant failed."
                    )

                    st.exception(exc)

    if st.session_state.assistant_question:

        st.divider()

        st.markdown(
            "### 🔧 Query Information"
        )

        st.write(
            f"**Question:** "
            f"{st.session_state.assistant_question}"
        )

        st.write(
            f"**Detected Query Type:** "
            f"{st.session_state.assistant_query_type}"
        )

    if st.session_state.assistant_answer:

        st.divider()

        st.markdown(
            "### 🤖 Assistant Answer"
        )

        st.markdown(
            st.session_state.assistant_answer
        )

    if st.session_state.assistant_result:

        st.divider()

        st.markdown(
            "### 🗄️ Database Result"
        )

        result = (
            st.session_state.assistant_result
        )

        if "results" in result:

            results = result[
                "results"
            ]

            if results:

                if isinstance(
                    results,
                    list,
                ):

                    if all(
                        isinstance(
                            item,
                            dict,
                        )
                        for item in results
                    ):

                        st.dataframe(
                            results,
                            use_container_width=True,
                            hide_index=True,
                        )

                    else:

                        st.dataframe(
                            [
                                {
                                    "Result": item
                                }
                                for item
                                in results
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )

            else:

                st.info(
                    "No matching database records."
                )

    with st.expander(
        "🔍 View raw query result"
    ):

        if st.session_state.assistant_result:

            st.json(
                st.session_state.assistant_result
            )

        else:

            st.write(
                "No query executed yet."
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "⚠️ Educational project using synthetic data. "
    "Network connections and AI-generated explanations "
    "describe stored records and do not establish guilt "
    "or responsibility."
)