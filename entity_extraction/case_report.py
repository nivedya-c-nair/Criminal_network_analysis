from collections import defaultdict

from database import (
    get_connection,
    initialize_database,
)


# ============================================================
# GET ENTITY CASES
# ============================================================

def get_entity_cases(entity_name):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT case_id
        FROM entities
        WHERE LOWER(name) = LOWER(?)
        ORDER BY case_id
        """,
        (entity_name,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        row["case_id"]
        for row in rows
    ]


# ============================================================
# GET ENTITY RELATIONSHIPS
# ============================================================

def get_entity_relationships(entity_name):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            case_id,
            from_entity,
            relationship_type,
            to_entity,
            confidence,
            date,
            source
        FROM relationships
        WHERE
            LOWER(from_entity) = LOWER(?)
            OR
            LOWER(to_entity) = LOWER(?)
        ORDER BY id
        """,
        (
            entity_name,
            entity_name,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# GET RELATED ENTITIES
# ============================================================

def get_related_entities(entity_name):

    relationships = get_entity_relationships(
        entity_name
    )

    related = set()

    for relationship in relationships:

        from_entity = relationship[
            "from_entity"
        ]

        to_entity = relationship[
            "to_entity"
        ]

        if (
            from_entity.lower()
            == entity_name.lower()
        ):

            related.add(
                to_entity
            )

        if (
            to_entity.lower()
            == entity_name.lower()
        ):

            related.add(
                from_entity
            )

    return sorted(related)


# ============================================================
# GET LOCATIONS
# ============================================================

def get_entity_locations(entity_name):

    relationships = get_entity_relationships(
        entity_name
    )

    locations = set()

    for relationship in relationships:

        if (
            relationship[
                "relationship_type"
            ]
            == "located_in"
        ):

            if (
                relationship[
                    "from_entity"
                ].lower()
                == entity_name.lower()
            ):

                locations.add(
                    relationship[
                        "to_entity"
                    ]
                )

            elif (
                relationship[
                    "to_entity"
                ].lower()
                == entity_name.lower()
            ):

                locations.add(
                    relationship[
                        "from_entity"
                    ]
                )

    return sorted(locations)


# ============================================================
# GET DATES
# ============================================================

def get_entity_dates(entity_name):

    relationships = get_entity_relationships(
        entity_name
    )

    dates = set()

    for relationship in relationships:

        date = relationship.get(
            "date"
        )

        if date:
            dates.add(
                date
            )

    return sorted(dates)


# ============================================================
# GET CROSS-CASE CONNECTIONS
# ============================================================

def get_cross_case_connections(
    entity_name
):

    cases = get_entity_cases(
        entity_name
    )

    if len(cases) < 2:
        return {}

    connection_map = defaultdict(set)

    connection = get_connection()
    cursor = connection.cursor()

    for case_id in cases:

        cursor.execute(
            """
            SELECT
                from_entity,
                to_entity
            FROM relationships
            WHERE case_id = ?
            """,
            (case_id,),
        )

        rows = cursor.fetchall()

        for row in rows:

            from_entity = row[
                "from_entity"
            ]

            to_entity = row[
                "to_entity"
            ]

            if (
                from_entity.lower()
                != entity_name.lower()
            ):

                connection_map[
                    case_id
                ].add(
                    from_entity
                )

            if (
                to_entity.lower()
                != entity_name.lower()
            ):

                connection_map[
                    case_id
                ].add(
                    to_entity
                )

    connection.close()

    return {
        case_id: sorted(
            entities
        )
        for case_id, entities
        in connection_map.items()
    }


# ============================================================
# GENERATE REPORT
# ============================================================

def generate_entity_report(
    entity_name
):

    cases = get_entity_cases(
        entity_name
    )

    relationships = (
        get_entity_relationships(
            entity_name
        )
    )

    related_entities = (
        get_related_entities(
            entity_name
        )
    )

    locations = (
        get_entity_locations(
            entity_name
        )
    )

    dates = (
        get_entity_dates(
            entity_name
        )
    )

    cross_case = (
        get_cross_case_connections(
            entity_name
        )
    )

    report = []

    report.append(
        "=========================================="
    )

    report.append(
        "        ENTITY INVESTIGATION REPORT"
    )

    report.append(
        "=========================================="
    )

    report.append("")

    report.append(
        f"Entity: {entity_name}"
    )

    report.append("")

    # --------------------------------------------------------
    # CASES
    # --------------------------------------------------------

    report.append(
        "CASES"
    )

    report.append(
        "-----"
    )

    if cases:

        for case_id in cases:

            report.append(
                f"- {case_id}"
            )

    else:

        report.append(
            "- No cases found"
        )

    report.append("")

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    report.append(
        "RELATIONSHIPS"
    )

    report.append(
        "-------------"
    )

    if relationships:

        for relationship in relationships:

            report.append(
                f"- "
                f"{relationship['from_entity']} "
                f"--[{relationship['relationship_type']}]--> "
                f"{relationship['to_entity']}"
            )

            report.append(
                f"  Case: "
                f"{relationship['case_id']}"
            )

            if relationship["date"]:

                report.append(
                    f"  Date: "
                    f"{relationship['date']}"
                )

            report.append(
                f"  Confidence: "
                f"{relationship['confidence']}"
            )

            report.append("")

    else:

        report.append(
            "- No relationships found"
        )

        report.append("")

    # --------------------------------------------------------
    # RELATED ENTITIES
    # --------------------------------------------------------

    report.append(
        "DIRECT CONNECTIONS"
    )

    report.append(
        "------------------"
    )

    if related_entities:

        for entity in related_entities:

            report.append(
                f"- {entity}"
            )

    else:

        report.append(
            "- None"
        )

    report.append("")

    # --------------------------------------------------------
    # LOCATIONS
    # --------------------------------------------------------

    report.append(
        "LOCATIONS"
    )

    report.append(
        "---------"
    )

    if locations:

        for location in locations:

            report.append(
                f"- {location}"
            )

    else:

        report.append(
            "- No location relationship found"
        )

    report.append("")

    # --------------------------------------------------------
    # TIMELINE
    # --------------------------------------------------------

    report.append(
        "TIMELINE"
    )

    report.append(
        "--------"
    )

    if dates:

        for date in dates:

            report.append(
                f"- {date}"
            )

    else:

        report.append(
            "- No dates recorded"
        )

    report.append("")

    # --------------------------------------------------------
    # CROSS-CASE
    # --------------------------------------------------------

    report.append(
        "CROSS-CASE INFORMATION"
    )

    report.append(
        "----------------------"
    )

    if len(cases) > 1:

        report.append(
            f"This entity appears in "
            f"{len(cases)} cases."
        )

        report.append("")

        for case_id, entities in (
            cross_case.items()
        ):

            report.append(
                f"{case_id}:"
            )

            for entity in entities:

                report.append(
                    f"  - {entity}"
                )

    else:

        report.append(
            "Entity appears in only one case."
        )

    report.append("")

    # --------------------------------------------------------
    # END
    # --------------------------------------------------------

    report.append(
        "=========================================="
    )

    report.append(
        "Report generated from stored database records."
    )

    report.append(
        "This report is descriptive and does not "
        "determine guilt or responsibility."
    )

    report.append(
        "=========================================="
    )

    return "\n".join(
        report
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    initialize_database()

    entity = input(
        "Enter entity name: "
    ).strip()

    if not entity:

        print(
            "Please enter an entity."
        )

    else:

        report = generate_entity_report(
            entity
        )

        print()
        print(report)