# 🕵️ Criminal Network Analysis

An educational Python project for analyzing relationships between entities in synthetic investigation data using NLP, graph analysis, SQL, SQLite, and AI.

## 📌 Project Overview

This project takes investigation text and extracts useful structured information such as:

- People
- Phone numbers
- Locations
- Dates
- Relationships between entities

The extracted information is stored in a SQLite database and visualized as an interactive network graph.

The project also includes SQL-based investigation tools, graph analytics, automated reports, AI-assisted analysis, graph-based AI analysis, and a natural-language query assistant.

## 🚀 Features

### 🧠 NLP Entity Extraction

Uses spaCy to identify entities from investigation text.

Examples:

- PERSON
- LOCATION
- DATE
- PHONE

### 🔗 Relationship Extraction

The system extracts relationships such as:

```text
Arjun → called → Meera
Arjun → used → 9987654321
Arjun → located_in → Kochi