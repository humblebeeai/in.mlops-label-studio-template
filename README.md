# HBAI Custom Label Studio Template

This is a customized version of Label Studio specifically configured for HBAI (HumbleBeeAI) with enhanced security and cloud storage integration.

## Key Modifications

### 1. Disabled Import Functionality
- **Import** buttons have been disabled to prevent local file uploads
- Drag-and-drop dataset functionality is blocked for security compliance
- All data ingestion is controlled through configured cloud storage

### 2. Enhanced Authentication Security
- **Signup** functionality disabled in the UI
- User registration is only possible through invite links
- This ensures proper user authentication and access control

### 3. Google Cloud Storage Integration
- Custom GCS (Google Cloud Storage) configured as both **Consistent** and **Source Storage**
- Seamless integration with GWS GCS bucket
- Automatic file synchronization and backup

## Docker Setup Guide

### Prerequisites
- Docker and Docker Compose installed
- Google Cloud Service Account key file
- Access to the GWS GCS bucket

### Setup Instructions

#### Necessary steps
- 

1. **Clone the repository:**
   ```bash
   git clone <repository-url> label-studio-{your-project-name}
   cd label-studio-{your-project-name}

   ```

2. **Prepare Google Cloud credentials:**
   ```bash
   mkdir secrets
   # Place your GCS service account key file as secrets/key.json
   ```

3. **Create data directory and set permissions:**
   ```bash
   mkdir data
   chmod 755 data
   ```

4. **Initial Setup (First Run):**
   
   **IMPORTANT**: On the first run, you need to enable user signup to create the initial admin user:
   
   a. **Edit docker-compose.yml** and ensure `LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK: "true"` is commented out (has # in front):
   ```yaml
   # LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK: "true"  # Keep this commented for first run
   ```
   
   b. **Start the application:**
   ```bash
   docker-compose up -d
   ```
   
   c. **Create admin user:**
   - Open your browser and navigate to `http://localhost:8080`
   - Sign up to create the initial admin account (signup page will be available)
   
   d. **Stop the application:**
   ```bash
   docker-compose down
   ```
   
   e. **Enable signup restriction** by uncommenting the line in docker-compose.yml:
   ```yaml
   LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK: "true"  # Remove the # to enable restriction
   ```
   
   f. **Restart the application:**
   ```bash
   docker-compose up -d
   ```

5. **Access Label Studio (After Initial Setup):**
   - Open your browser and navigate to `http://localhost:8080`
   - Login with your admin account
   - Use invite links to add additional users (signup page will no longer be available)

### Configuration Details

The application is pre-configured with:
- **Port**: 8080 (Now this port is being used for GWS-Pepsi. For a new project you should change it to another port like 8081, then 8082, etc)
- **GCS Bucket**: `hbai-label-studio`
- **GCS Project**: `humblebee-project`
- **Storage Folder**: `gws-pepsi/projects`
- **Custom CSS**: Applied for UI modifications

### Environment Variables

Key environment variables set in docker-compose.yaml:
- `STORAGE_TYPE=gcs` - Enables Google Cloud Storage
- `LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK=true` - Enforces invite-only registration
- `USE_NGINX_FOR_UPLOADS=false` - Recommended for GCS integration

### Google Cloud Storage CORS Configuration

Label Studio requires proper CORS (Cross-Origin Resource Sharing) configuration on your GCS bucket to handle file uploads and access from the web interface.

#### Setting CORS Policies

1. **Using the included Python script:**
   ```bash
   # Set your Google Cloud credentials
   export GOOGLE_APPLICATION_CREDENTIALS="./secrets/key.json"
   
   # Install required dependency
   pip install google-cloud-storage
   
   # Run the CORS configuration script after replacing your targer bucket name in `set_cors.py`
   python set_cors.py
   ```

2. **Manual CORS configuration using gsutil:**
   ```bash
   # Create a cors.json file with the following content:
   echo '[
     {
       "origin": ["*"],
       "responseHeader": ["Content-Type", "x-goog-resumable"],
       "method": ["PUT", "POST", "GET", "DELETE", "HEAD"],
       "maxAgeSeconds": 3600
     }
   ]' > cors.json
   
   # Apply CORS configuration to your bucket
   gsutil cors set cors.json gs://your-bucket-name
   ```

#### CORS Policy Details

The CORS configuration allows:
- **Origins**: All domains (`*`) - restrict this in production as needed
- **Methods**: PUT, POST, GET, DELETE, HEAD for full functionality
- **Headers**: Content-Type and x-goog-resumable for file uploads
- **Max Age**: 3600 seconds (1 hour) for preflight request caching

## Database Backup and Migration

The Label Studio database contains all your projects, annotations, and user data. Regular backups are essential for data protection and server migration.

### Why Backup the Database?

When migrating Label Studio from one server to another, the simplest approach is to:
1. Backup the `label_studio.sqlite3` database file
2. Copy it to the new server
3. Rename the timestamped backup file back to `label_studio.sqlite3`

This preserves all your projects, annotations, users, and configurations without complex data exports.

### Prerequisites for Database Backup

1. **First change configs in `backup_db.sh` file**:
   ```sh
   DB_PATH="/path/to/data/label_studio.sqlite3"
   GCS_BUCKET="gs://gws-{company_name}/ls/db_backup/"
   SERVICE_ACCOUNT_KEY="/path/to/secrets/key.json"
   BACKUP_FILENAME="label_studio_{project_name}_${TIMESTAMP}.sqlite3" 
   
   ```

### Setting Up Automated Backups

**For daily backups (default - every day at 0 AM)** 
It is recomended to backup daily(default) 
```bash
cd /root/label-studio-{your-project-name}
./setup_cron.sh
```

**For weekly backups (every Sunday at 0 AM):**
```bash
cd /root/label-studio-{your-project-name}
./setup_cron.sh weekly
```

**For monthly backups (1st of each month at 0 AM):**
```bash
cd /root/label-studio-{your-project-name}
./setup_cron.sh monthly
```

**Verify cron jobs are installed:**
```bash
crontab -l
```

### Manual Backup

**Run a backup anytime:**
```bash
cd /root/label-studio-{your-project-name}
./backup_db.sh
```

This creates a backup with timestamp like: `label_studio_{your-project-name}_20250811_143022.sqlite3` in the GCS bucket `gs://hbai-label-studio/{your-project-name}/db_backup/`

### Database Migration Process

1. **Download the backup from GCS:**
   ```bash
   gsutil cp gs://hbai-label-studio/{your-project-name}/db_backup/label_studio_{your-project-name}_YYYYMMDD_HHMMSS.sqlite3 ./
   ```

2. **Rename the backup file:**
   ```bash
   mv label_studio_{your-project-name}_YYYYMMDD_HHMMSS.sqlite3 label_studio.sqlite3
   ```

3. **Place it in the data directory:**
   ```bash
   cp label_studio.sqlite3 /path/to/new/server/data/
   ```

4. **Set proper permissions for Docker container access:**
   ```bash
   # Set ownership to match Docker container user (usually 1001 or 1000)
   chown 1001:1001 /path/to/new/server/data/label_studio.sqlite3
   # Or try 1000:1000 if 1001 doesn't work
   # chown 1000:1000 /path/to/new/server/data/label_studio.sqlite3
   ```
   
   Note: Docker containers often run with user ID 1001 or 1000. Check your container's user ID if these don't work.

5. **Start Label Studio** - it will use the restored database with all your data intact.

### Monitoring and Management

**Check backup logs:**
```bash
tail -f /root/label-studio-{your-project-name}/logs/backup.log
```

**List recent backups in GCS:**
```bash
gsutil ls -l gs://hbai-label-studio/{your-project-name}/db_backup/
```

**Switch backup frequency:**
- Change to daily: `./setup_cron.sh`
- Change to weekly: `./setup_cron.sh weekly`
- Change to monthly: `./setup_cron.sh monthly`

**Remove existing cron jobs:**
```bash
crontab -e
```
This opens your crontab in an editor. Find the backup job line, delete it, then save and exit.

### Troubleshooting

- Ensure the GCS service account key has proper permissions
- Check that the `hbai-label-studio` bucket is accessible
- **Verify CORS is set correctly** - this is required for file uploads to work
- Verify Docker containers are running: `docker-compose ps`
- Check logs: `docker-compose logs ls-{your-project-name}`