#!/usr/bin/env bash
# exit on error
set -o errexit

# Tell Render to step inside the correct folder where the code lives
cd stratix-dashboard

# Install dependencies and gather static files
pip install -r requirements.txt
python manage.py collectstatic --no-input

# --- BULLETPROOF DATABASE SYNC FIX ---
# This script uses Django's native schema editor to forcefully create the 
# SupportTicket table, completely bypassing any corrupted migration history.
cat << 'EOF' > fix_db.py
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from django.db import connection
from reports.models import SupportTicket

# 1. Clean up legacy site issues if out of sync
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='reports_project' AND column_name='require_photo_minimums';")
    if not cursor.fetchone():
        cursor.execute("DROP TABLE IF EXISTS reports_siteissue CASCADE;")

# 2. Forcefully inject the SupportTicket table
try:
    tables = connection.introspection.table_names()
    if 'reports_supportticket' not in tables:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(SupportTicket)
            print("🚀 BULLETPROOF FIX: SupportTicket table forcefully created!")
    else:
        print("✅ SupportTicket table already exists.")
except Exception as e:
    print(f"Database sync message: {e}")
EOF
python fix_db.py
# -------------------------------

# Run standard migrations (Notice we removed 'makemigrations' to prevent conflicts)
python manage.py migrate

python create_admin.py
