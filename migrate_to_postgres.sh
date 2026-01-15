#!/bin/bash
# Script to migrate SQLite data to PostgreSQL

set -e

echo "=== SQLite to PostgreSQL Migration Script ==="
echo ""

# Check if db_dump.json exists
if [ ! -f "db_dump.json" ]; then
    echo "Error: db_dump.json not found!"
    echo "Run: uv run python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 -o db_dump.json"
    exit 1
fi

echo "Step 1: Backing up current SQLite database..."
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)

echo "Step 2: Setting DATABASE_URL to PostgreSQL..."
export DATABASE_URL="postgresql://meal_planner:${MEAL_PLANNER_DB_PASSWORD}@localhost:5432/meal_planner"

echo "Step 3: Running migrations on PostgreSQL..."
uv run python manage.py migrate

echo "Step 4: Loading data into PostgreSQL..."
uv run python manage.py loaddata db_dump.json

echo ""
echo "=== Migration Complete ==="
echo "Your data has been successfully migrated to PostgreSQL!"
echo "SQLite backup saved as: db.sqlite3.backup.*"
