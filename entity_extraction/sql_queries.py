import sqlite3

from database import get_connection


# ============================================================
# 1. GET ALL CASES
# ============================================================

def get_cases():
    """
    Return all cases from the database.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            case_id,
            text
        FROM cases
        ORDER BY case_id
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [dict(row) for row in rows]


# ============================================================
# 2. FIND CASES CONTAINING AN ENTITY
# ============================================================

def get_cases_for_entity(entity_name):
    """
    Find every case where a particular entity appears.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT
            case_id
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
# 3. FIND ALL CONNECTIONS OF AN ENTITY
# ============================================================

def get_entity_connections(entity_name):
    """
    Find all relationships involving an entity.
    """

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
# 4. FIND ENTITIES APPEARING IN MULTIPLE CASES
# ============================================================

def get_cross_case_entities():
    """
    Find entities that appear in more than one case.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            name,
            entity_type,
            COUNT(DISTINCT case_id) AS case_count
        FROM entities
        GROUP BY
            name,
            entity_type
        HAVING
            COUNT(DISTINCT case_id) > 1
        ORDER BY
            case_count DESC,
            name
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# 5. FIND RELATIONSHIPS BY DATE
# ============================================================

def get_relationships_by_date(date_text):
    """
    Find relationships recorded on a specific date.
    """

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
            LOWER(date) = LOWER(?)
        ORDER BY
            case_id
        """,
        (date_text,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# 6. FIND ALL RELATIONSHIPS IN A CASE
# ============================================================

def get_case_relationships(case_id):
    """
    Return every relationship belonging to a case.
    """

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
            case_id = ?
        ORDER BY
            id
        """,
        (case_id,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# 7. SEARCH ENTITIES
# ============================================================

def search_entities(search_text):
    """
    Search for entities containing the supplied text.
    """

    connection = get_connection()
    cursor = connection.cursor()

    search_pattern = (
        f"%{search_text}%"
    )

    cursor.execute(
        """
        SELECT DISTINCT
            name,
            entity_type
        FROM entities
        WHERE
            LOWER(name) LIKE LOWER(?)
        ORDER BY
            name
        """,
        (search_pattern,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# 8. GET CASE SUMMARY
# ============================================================

def get_case_summary():
    """
    Return one summary row for every case.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            c.case_id,
            c.text,
            COUNT(DISTINCT r.id) AS relationship_count,
            COUNT(DISTINCT e.id) AS entity_count
        FROM cases c

        LEFT JOIN relationships r
            ON c.case_id = r.case_id

        LEFT JOIN entities e
            ON c.case_id = e.case_id

        GROUP BY
            c.case_id,
            c.text

        ORDER BY
            c.case_id
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# 9. GET RELATIONSHIP TYPE COUNTS
# ============================================================

def get_relationship_type_counts():
    """
    Count how many times each relationship type occurs.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            relationship_type,
            COUNT(*) AS count
        FROM relationships
        GROUP BY
            relationship_type
        ORDER BY
            count DESC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# 10. FIND PHONE CONNECTIONS
# ============================================================

def get_phone_connections(phone_number):
    """
    Find all relationships involving a phone number.
    """

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
            from_entity = ?
            OR
            to_entity = ?
        ORDER BY
            case_id
        """,
        (
            phone_number,
            phone_number,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# 11. FIND CASES SHARING A PHONE
# ============================================================

def get_cases_sharing_phone(phone_number):
    """
    Find all cases associated with a phone number.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT
            case_id
        FROM entities
        WHERE
            name = ?
            AND entity_type = 'PHONE'
        ORDER BY
            case_id
        """,
        (phone_number,),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        row["case_id"]
        for row in rows
    ]


# ============================================================
# 12. GET DATABASE COUNTS
# ============================================================

def get_database_counts():
    """
    Return record counts for the main tables.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM cases"
    )

    case_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM entities"
    )

    entity_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM relationships"
    )

    relationship_count = cursor.fetchone()[0]

    connection.close()

    return {
        "cases": case_count,
        "entities": entity_count,
        "relationships": relationship_count,
    }


# ============================================================
# 13. PRINT ENTITY INVESTIGATION
# ============================================================

def print_entity_investigation(entity_name):
    """
    Print a simple investigation report for one entity.
    """

    print()
    print(
        "=========================================="
    )
    print(
        f"ENTITY INVESTIGATION: {entity_name}"
    )
    print(
        "=========================================="
    )

    # Cases
    cases = get_cases_for_entity(
        entity_name
    )

    print()
    print(
        "Cases:"
    )

    if cases:

        for case_id in cases:
            print(
                f"  - {case_id}"
            )

    else:

        print(
            "  No cases found."
        )

    # Connections
    connections = get_entity_connections(
        entity_name
    )

    print()
    print(
        "Connections:"
    )

    if connections:

        for connection in connections:

            print(
                f"  {connection['from_entity']} "
                f"--[{connection['relationship_type']}]--> "
                f"{connection['to_entity']}"
            )

            print(
                f"     Case: "
                f"{connection['case_id']}"
            )

            print(
                f"     Date: "
                f"{connection['date']}"
            )

            print(
                f"     Confidence: "
                f"{connection['confidence']}"
            )

    else:

        print(
            "  No connections found."
        )

    print()


# ============================================================
# 14. PRINT CROSS-CASE ENTITIES
# ============================================================

def print_cross_case_entities():
    """
    Print entities appearing in multiple cases.
    """

    rows = get_cross_case_entities()

    print()
    print(
        "=========================================="
    )
    print(
        "CROSS-CASE ENTITIES"
    )
    print(
        "=========================================="
    )

    if not rows:

        print(
            "No repeated entities found."
        )

        return

    for row in rows:

        print(
            f"{row['name']} "
            f"({row['entity_type']}) "
            f"-> "
            f"{row['case_count']} cases"
        )

    print()


# ============================================================
# 15. PRINT DATABASE SUMMARY
# ============================================================

def print_database_summary():
    """
    Print overall database information.
    """

    counts = get_database_counts()

    print()
    print(
        "=========================================="
    )
    print(
        "DATABASE SUMMARY"
    )
    print(
        "=========================================="
    )

    print(
        f"Cases:          {counts['cases']}"
    )

    print(
        f"Entities:       {counts['entities']}"
    )

    print(
        f"Relationships:  {counts['relationships']}"
    )

    print()


# ============================================================
# 16. DEMO QUERIES
# ============================================================

def run_demo():

    print_database_summary()

    print_cross_case_entities()

    print_entity_investigation(
        "Rahul"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    try:

        run_demo()

    except sqlite3.Error as exc:

        print()
        print(
            "SQLite error:"
        )

        print(exc)

    except Exception as exc:

        print()
        print(
            "Unexpected error:"
        )

        print(exc)