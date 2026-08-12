#!/bin/sh

set -e

# Inspect the first argument ($1) passed to the container CMD.
# If it is 'celery', skip the database operations completely.

if [ "$1" = "celery" ]; then
    echo "Celery Worker container detected. Skipping database migration loop."
    echo "Handing thread over to Celery runner process..."
    exec "$@" 
fi

echo "Step 1: Waiting for PostgreSQL Database Engine to accept connections..."

until python -c "
import sys, psycopg2, os
try:
    psycopg2.connect(
        dbname=os.environ.get('DB_NAME', 'oreilly_db'),
        user=os.environ.get('DB_USER', 'postgres_user'),
        password=os.environ.get('DB_PASSWORD', 'secure_password123'),
        host=os.environ.get('DB_HOST', 'postgres-db-service'),
        port=os.environ.get('DB_PORT', '5432')
    )
except Exception as e:
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; do
    echo "Postgres is unavailable - sleeping for 2 seconds..."
    sleep 2
done

echo "PostgreSQL is live!"

echo "Step 2: Executing database model migrations..."

# Force discovery of your root-level app explicitly
python manage.py makemigrations interactive_challenges --noinput
python manage.py makemigrations base_project --noinput

python manage.py migrate --noinput

echo "Running Automated PyTest Suite Verification Checks..."
python -m pytest -v --no-summary

echo "Populating baseline course metadata catalog rows..."

python manage.py shell -c "
from base_project.models import Course
course, created = Course.objects.get_or_create(id=1,defaults={'title': 'Kubernetes Microservices Architecture', 'description': 'Automated Cluster Content'})
if created:
    print('Course ID 1 initialized successfully in storage layer.')
else:
    print('Course ID 1 already present, skipping instantiation loop.')
"
echo "Handing execution thread over to specified runtime service container process..."
# Exec evaluates the incoming CMD parameter tokens passed via Docker or K8s cleanly
exec "$@"