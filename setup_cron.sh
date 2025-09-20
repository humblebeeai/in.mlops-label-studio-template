#!/bin/bash

# Setup cron jobs for Label Studio database backups
# Run this script once to install the cron jobs
# Before running, do `chmod +x /root/label-studio-gws/setup_cron.sh` to make it executable
#
# Usage:
#   ./setup_cron.sh           # Sets up weekly backups (default)
#   ./setup_cron.sh monthly   # Sets up monthly backups instead

SCRIPT_PATH="label-studio-gws/backup_db.sh" # Change to your backup script path
LOG_PATH="label-studio-gws/backup.log"
BACKUP_TYPE="${1:-daily}"  # Default to weekly if no argument provided

# Ensure backup script exists and is executable
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: Backup script not found at $SCRIPT_PATH"
    exit 1
fi

if [ ! -x "$SCRIPT_PATH" ]; then
    chmod +x "$SCRIPT_PATH"
fi

# Create cron entries based on backup type
echo "Setting up cron jobs for database backups..."
echo "Backup type: $BACKUP_TYPE"

# Add header comment (only if not already present)
if ! crontab -l 2>/dev/null | grep -q "Label Studio Database Backups"; then
    (crontab -l 2>/dev/null; echo "# Label Studio Database Backups") | crontab -
fi

if [ "$BACKUP_TYPE" = "monthly" ]; then
    # Monthly backup: 1st of every month at 0:00 AM
    (crontab -l 2>/dev/null; echo "0 0 1 * * $SCRIPT_PATH >> $LOG_PATH 2>&1  # Monthly backup (1st of month 0AM)") | crontab -
    echo "Cron job installed successfully!"
    echo "Monthly backups: 1st of every month at 0:00 AM"

elif [ "$BACKUP_TYPE" = "weekly" ]; then
    # Weekly backup: Every Sunday at 0:00 AM
    (crontab -l 2>/dev/null; echo "0 0 * * 0 $SCRIPT_PATH >> $LOG_PATH 2>&1  # Weekly backup (Sunday 0AM)") | crontab -
    echo "Cron job installed successfully!"
    echo "Daily backups: Every day at 0:00 AM"

else
    # Daily backup: Every day at 0:00 AM (default)
    (crontab -l 2>/dev/null; echo "0 0 * * * $SCRIPT_PATH >> $LOG_PATH 2>&1  # Daily backup (0AM)") | crontab -
    echo "Cron job installed successfully!"
    echo "Daily backups: Every day at 0:00 AM"
fi

echo "Logs will be written to: $LOG_PATH"
echo ""
echo "To change backup frequency later:"
echo "  - For weekly:  ./setup_cron.sh weekly"
echo "  - For monthly: ./setup_cron.sh monthly"
echo ""
echo "Current crontab:"
crontab -l