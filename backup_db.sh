#!/bin/bash

# Label Studio SQLite Database Backup Script
# Backs up label_studio.sqlite3 to Google Cloud Storage with timestamp
# Before running, do `chmod +x /root/label-studio/backup_db.sh`

set -e

# Configuration
DB_PATH="/home/bekhzod/label-studio-gws/data/label_studio.sqlite3"
GCS_BUCKET="gs://hbai-label-studio/gws-pepsi/db_backup/"
SERVICE_ACCOUNT_KEY="/home/bekhzod/label-studio-gws/secrets/key.json"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="label_studio_gws_pepsi_${TIMESTAMP}.sqlite3"

# Verify service account key permissions
if [ "$(stat -c "%a" "$SERVICE_ACCOUNT_KEY")" != "755" ]; then
    echo "Warning: Fixing service account key file permissions..."
    chmod 755 "$SERVICE_ACCOUNT_KEY"
fi

# Ensure database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found at $DB_PATH"
    exit 1
fi

# Ensure service account key exists
if [ ! -f "$SERVICE_ACCOUNT_KEY" ]; then
    echo "Error: Service account key not found at $SERVICE_ACCOUNT_KEY"
    exit 1
fi

# Authenticate with Google Cloud using service account
export GOOGLE_APPLICATION_CREDENTIALS="$SERVICE_ACCOUNT_KEY"

echo "Starting backup of Label Studio database..."
echo "Source: $DB_PATH"
echo "Destination: ${GCS_BUCKET}${BACKUP_FILENAME}"

# Check if gsutil is available
if ! command -v gsutil &> /dev/null; then
    echo "Error: gsutil is not installed. Please install Google Cloud SDK."
    exit 1
fi

# Test bucket access
if ! gsutil ls "$GCS_BUCKET" &>/dev/null; then
    echo "Error: Cannot access GCS bucket. Check permissions and bucket name."
    exit 1
fi

# Create a copy of the database to avoid locking issues during backup
TEMP_DB_PATH="/tmp/${BACKUP_FILENAME}"
cp "$DB_PATH" "$TEMP_DB_PATH"

# Upload to GCS
if gsutil cp "$TEMP_DB_PATH" "${GCS_BUCKET}${BACKUP_FILENAME}"; then
    echo "Backup successful: ${GCS_BUCKET}${BACKUP_FILENAME}"
    
    # Clean up temporary file
    rm "$TEMP_DB_PATH"
    
    # Optional: List recent backups
    # echo "Recent backups in GCS bucket:"
    # gsutil ls -l "${GCS_BUCKET}" | tail -5
else
    echo "Backup failed!"
    rm "$TEMP_DB_PATH"
    exit 1
fi