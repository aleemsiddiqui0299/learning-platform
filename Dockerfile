FROM python:3.13-slim

# Prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr for immediate logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for compiling native C-extensions like psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python package dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application codebase
COPY . /app/

# Force convert the script to Unix line endings and grant execute permissions
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]