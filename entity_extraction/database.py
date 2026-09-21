import json
import os
import sqlite3


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(__file__)

DATA_FILE = os.path.join(
    BASE_DIR,
    "data",
    "case_data.json",
)

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "criminal_network.db",
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    os.makedirs(
        os.path.dirname(DATABASE_FILE),
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # CASES
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            text TEXT NOT NULL
        )
        """
    )

    # --------------------------------------------------------
    # ENTITIES
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            case_id TEXT NOT NULL,
            UNIQUE(name, case_id)
        )
        """
    )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            from_entity TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            to_entity TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            date TEXT,
            source TEXT
        )
        """
    )

    connection.commit()
    connection.close()


# ============================================================
# LOAD JSON DATA
# ============================================================

def load_json_data():

    if not os.path.exists(
        DATA_FILE
    ):

        return {
            "cases": []
        }

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return {
            "cases": []
        }


# ============================================================
# INSERT CASE
# ============================================================

def insert_case(
    case_id,
    text,
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO cases (
                case_id,
                text
            )
            VALUES (?, ?)
            """,
            (
                case_id,
                text,
            ),
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        connection.close()


# ============================================================
# INSERT ENTITY
# ============================================================

def insert_entity(
    name,
    entity_type,
    case_id,
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO entities (
            name,
            entity_type,
            case_id
        )
        VALUES (?, ?, ?)
        """,
        (
            name,
            entity_type,
            case_id,
        ),
    )

    connection.commit()
    connection.close()


# ============================================================
# INSERT RELATIONSHIP
# ============================================================

def insert_relationship(
    case_id,
    from_entity,
    relationship_type,
    to_entity,
    confidence=0.0,
    date=None,
    source=None,
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO relationships (
            case_id,
            from_entity,
            relationship_type,
            to_entity,
            confidence,
            date,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            from_entity,
            relationship_type,
            to_entity,
            confidence,
            date,
            source,
        ),
    )

    connection.commit()
    connection.close()


# ============================================================
# GET ALL CASES
# ============================================================

def get_all_cases():

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

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# GET ALL RELATIONSHIPS
# ============================================================

def get_all_relationships():

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
        ORDER BY id
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        {
            "case_id": row["case_id"],
            "from": row["from_entity"],
            "type": row["relationship_type"],
            "to": row["to_entity"],
            "confidence": row["confidence"],
            "date": row["date"],
            "source": row["source"],
        }
        for row in rows
    ]


# ============================================================
# GET ALL ENTITIES
# ============================================================

def get_all_entities():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT
            name,
            entity_type
        FROM entities
        ORDER BY name
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        {
            "name": row["name"],
            "type": row["entity_type"],
        }
        for row in rows
    ]


# ============================================================
# CHECK CASE EXISTS
# ============================================================

def case_exists(
    case_id,
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM cases
        WHERE case_id = ?
        LIMIT 1
        """,
        (
            case_id,
        ),
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ============================================================
# GET DATABASE COUNTS
# ============================================================

def get_database_counts():

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
# ENTITY TYPE DETECTION
# ============================================================

def guess_entity_type(
    name,
):

    name = str(
        name
    ).strip()

    if not name:

        return "OTHER"

    if name.startswith(
        "Case_"
    ):

        return "CASE"

    digits = "".join(
        character
        for character in name
        if character.isdigit()
    )

    if len(digits) == 10:

        return "PHONE"

    known_locations = {
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

    if name.lower() in known_locations:

        return "LOCATION"

    month_names = {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }

    lower_name = name.lower()

    if any(
        month in lower_name
        for month in month_names
    ):

        return "DATE"

    return "PERSON"


# ============================================================
# MIGRATE ONE CASE
# ============================================================

def migrate_case(
    case,
):

    case_id = case.get(
        "case_id"
    )

    text = case.get(
        "text",
        "",
    )

    if not case_id:

        return

    if case_exists(
        case_id
    ):

        return

    inserted = insert_case(
        case_id,
        text,
    )

    if not inserted:

        return

    relationships = case.get(
        "relationships",
        [],
    )

    for relationship in relationships:

        from_entity = relationship.get(
            "from",
            "",
        )

        relationship_type = relationship.get(
            "type",
            "",
        )

        to_entity = relationship.get(
            "to",
            "",
        )

        confidence = relationship.get(
            "confidence",
            0.0,
        )

        date = relationship.get(
            "date"
        )

        source = relationship.get(
            "source"
        )

        if (
            from_entity
            and relationship_type
            and to_entity
        ):

            insert_relationship(
                case_id=case_id,
                from_entity=from_entity,
                relationship_type=relationship_type,
                to_entity=to_entity,
                confidence=confidence,
                date=date,
                source=source,
            )

            insert_entity(
                name=from_entity,
                entity_type=guess_entity_type(
                    from_entity
                ),
                case_id=case_id,
            )

            insert_entity(
                name=to_entity,
                entity_type=guess_entity_type(
                    to_entity
                ),
                case_id=case_id,
            )


# ============================================================
# MIGRATE JSON TO SQLITE
# ============================================================

def migrate_json_to_database():

    initialize_database()

    data = load_json_data()

    cases = data.get(
        "cases",
        [],
    )

    for case in cases:

        migrate_case(
            case
        )

    print()
    print(
        "======================================"
    )
    print(
        " JSON → SQLite migration completed"
    )
    print(
        "======================================"
    )

    print(
        f"Database: {DATABASE_FILE}"
    )

    print(
        f"Cases processed: {len(cases)}"
    )

    show_database_summary()


# ============================================================
# DATABASE SUMMARY
# ============================================================

def show_database_summary():

    counts = get_database_counts()

    print()
    print(
        "Database Summary"
    )
    print(
        "----------------"
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
# MAIN
# ============================================================

if __name__ == "__main__":

    migrate_json_to_database()