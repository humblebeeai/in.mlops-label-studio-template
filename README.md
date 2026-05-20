# HBAI Custom Label Studio Template

This is a customized version of Label Studio specifically configured for HBAI (HumbleBeeAI) with enhanced security and cloud storage integration.

## Table of Contents

- [Key Modifications](#key-modifications)
- [Docker Setup Guide](#docker-setup-guide)
- [Database Backup and Migration](#database-backup-and-migration)
- [Tailscale Network Configuration](#tailscale-network-configuration)
- [Rebuilding Data and Annotations](#rebuilding-data-and-annotations)
- [GCS Dataset Structure for Computer Vision Projects](#gcs-dataset-structure-for-computer-vision-projects)

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
- Seamless integration with HBAI GCS bucket
- Automatic file synchronization and backup

## Docker Setup Guide

### Prerequisites
- Docker and Docker Compose installed
- Google Cloud Service Account key file
- Access to the HBAI Label Studio GCS bucket

### Setup Instructions

#### Necessary steps
- 

1. **Clone the repository:**
   ```bash
   git clone <repository-url> {your-project-name}
   cd {your-project-name}

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

4. **Configure Docker Compose for your project:**

   **IMPORTANT**: You must customize the docker-compose.yml file for each project to avoid conflicts:

   a. **Edit docker-compose.yml** and modify the following settings:
   ```yaml
   # Change the service name to match your project
   services:
     ls-{your-project-name}:  # Replace {your-project-name} with your actual project name

   # Change the container name
   container_name: label-studio-{your-project-name}

   # Change the port mapping to avoid conflicts (8800 is used for GWS-Pepsi)
   ports:
     - "8800:8080"  # Use 8801, 8802, 8803, etc. for different projects

   # Update the storage folder path in environment variables
   environment:
     - GOOGLE_APPLICATION_CREDENTIALS=/tmp/key.json
     - STORAGE_TYPE=gcs
     - GCS_BUCKET_NAME=hbai-label-studio
     - GCS_PROJECT_NAME=humblebee-project
     - GCS_FOLDER={your-project-name}/projects  # Replace with your project name
   ```

   b. **Key configurations to customize**:
   - **Service name**: `ls-{your-project-name}` (line with service definition)
   - **Container name**: `label-studio-{your-project-name}`
   - **Port mapping**: Use different external ports (8800, 8802, etc.) to run multiple instances
   - **GCS folder**: `{your-project-name}/projects` for organized cloud storage
   - **Project-specific environment variables** as needed

5. **Initial Setup (First Run):**
   
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

6. **Access Label Studio (After Initial Setup):**
   - Open your browser and navigate to `http://localhost:8800` (or your custom port like 8801)
   - Login with your admin account
   - Use invite links to add additional users (signup page will no longer be available)

7. **Set up automated database backup:**

   **IMPORTANT**: Configure automated backups to protect your annotation data and enable easy server migration.

   a. **Configure backup settings** in `backup_db.sh`:
   ```bash
   # Edit the following variables in backup_db.sh
   DB_PATH="/path/to/data/label_studio.sqlite3"
   GCS_BUCKET="gs://hbai-label-studio/{your-project-name}/db_backup/"
   SERVICE_ACCOUNT_KEY="/path/to/secrets/key.json"
   BACKUP_FILENAME="label_studio_{your-project-name}_${TIMESTAMP}.sqlite3"
   ```

   b. **Set up daily backups (recommended)**:
   ```bash
   cd /root/label-studio-{your-project-name}
   ./setup_cron.sh
   ```

   c. **Verify the backup setup**:
   ```bash
   crontab -l  # Check if cron job is installed
   ./backup_db.sh  # Run manual backup to test
   ```

   This ensures your data is regularly backed up to Google Cloud Storage for protection and easy migration.

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
   GCS_BUCKET="gs://gws-{company_name}/db_backup/"
   SERVICE_ACCOUNT_KEY="/path/to/secrets/key.json"
   BACKUP_FILENAME="label_studio_{project_name}_${TIMESTAMP}.sqlite3" 
   
   ```

### Setting Up Automated Backups

**For daily backups (default - every day at 0 AM)** 
It is recomended to backup daily(default) 
```bash
cd /root/label-studio/{your-project-name}
./setup_cron.sh
```

**For weekly backups (every Sunday at 0 AM):**
```bash
cd /root/label-studio/{your-project-name}
./setup_cron.sh weekly
```

**For monthly backups (1st of each month at 0 AM):**
```bash
cd /root/label-studio/{your-project-name}
./setup_cron.sh monthly
```

**Verify cron jobs are installed:**
```bash
crontab -l
```

### Manual Backup

**Run a backup anytime:**
```bash
cd /root/label-studio/{your-project-name}
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
tail -f /root/label-studio/{your-project-name}/logs/backup.log
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

## Tailscale Network Configuration

If you're running Label Studio on a server with Tailscale and experience issues with YOLO export (images not downloading, connection timeouts), you may need to configure iptables rules to allow Docker containers to access the host through the Tailscale network.

### Problem Description

**Symptoms:**
- Export with images (e.g., "YOLO with images") fails with connection timeout errors
- Logs show: `Connection to <tailscale-ip> timed out`
- Error message: `Unable to download gs://... The item will be skipped`

**Root Cause:**
Tailscale's firewall rules (`ts-input` chain) block traffic from Docker containers trying to access the host's Tailscale IP address. This prevents the export process from downloading images through the presign endpoint.

### Solution: Configure Systemd Service for iptables

This solution allows Docker containers to access Label Studio ports on the Tailscale IP address. It's safe, scalable, and works for all Label Studio projects.

#### Step 1: Create the Systemd Service

```bash
# Create the service file
sudo tee /etc/systemd/system/label-studio-tailscale.service > /dev/null <<'EOF'
[Unit]
Description=Allow Docker containers to access Label Studio on Tailscale IP
After=tailscaled.service docker.service
Requires=tailscaled.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'sleep 2 && iptables -C ts-input -s 172.16.0.0/12 -d <TAILSCALE_IP> -p tcp -m multiport --dports 8800:8850 -j ACCEPT 2>/dev/null || iptables -I ts-input 3 -s 172.16.0.0/12 -d <TAILSCALE_IP> -p tcp -m multiport --dports 8800:8850 -j ACCEPT'
ExecStop=/bin/bash -c 'iptables -D ts-input -s 172.16.0.0/12 -d <TAILSCALE_IP> -p tcp -m multiport --dports 8800:8850 -j ACCEPT 2>/dev/null || true'

[Install]
WantedBy=multi-user.target
EOF
```

**Important:** Replace `<TAILSCALE_IP>` with your server's Tailscale IP address (e.g., `100.100.1.20`).

To find your Tailscale IP:
```bash
tailscale ip -4
```

#### Step 2: Enable and Start the Service

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Start the service (test mode - doesn't auto-start on boot yet)
sudo systemctl start label-studio-tailscale.service

# Check if it's working
sudo systemctl status label-studio-tailscale.service

# Verify the iptables rule was added
sudo iptables -L ts-input -n -v --line-numbers | grep "8800:8850"
```

#### Step 3: Test the Export

1. Go to your Label Studio project
2. Try exporting annotations with "YOLO with images" format
3. If it works successfully, enable auto-start on boot:

```bash
sudo systemctl enable label-studio-tailscale.service
```

### Managing the Systemd Service

**Check service status:**
```bash
sudo systemctl status label-studio-tailscale.service
```

**View service logs:**
```bash
sudo journalctl -u label-studio-tailscale.service -f
```

**Restart the service:**
```bash
sudo systemctl restart label-studio-tailscale.service
```

**Stop the service:**
```bash
sudo systemctl stop label-studio-tailscale.service
```

**Disable auto-start on boot:**
```bash
sudo systemctl disable label-studio-tailscale.service
```

**Remove the service completely:**
```bash
# Stop and disable the service
sudo systemctl stop label-studio-tailscale.service
sudo systemctl disable label-studio-tailscale.service

# Remove the service file
sudo rm /etc/systemd/system/label-studio-tailscale.service

# Reload systemd
sudo systemctl daemon-reload

# Manually remove the iptables rule
sudo iptables -D ts-input -s 172.16.0.0/12 -d <TAILSCALE_IP> -p tcp -m multiport --dports 8800:8850 -j ACCEPT
```

### What This Configuration Does

- **Allows**: Docker containers (from any Docker bridge network) to access Label Studio ports (8800-8850) on the server's Tailscale IP
- **Port Range**: 8800-8850 covers all Label Studio instances on the server
- **Security**: Only affects Label Studio ports, doesn't bypass Tailscale security for other services
- **Persistence**: Automatically applies the rule on boot and after Tailscale restarts

### Troubleshooting the Tailscale Configuration

**If export still fails after enabling the service:**

1. Check if the iptables rule is present:
   ```bash
   sudo iptables -L ts-input -n -v --line-numbers
   ```
   You should see a rule with source `172.16.0.0/12` and destination `<TAILSCALE_IP>` on ports `8800:8850`.

2. Verify the rule is in the correct position (should be line 3 or higher, before any DROP rules):
   ```bash
   sudo iptables -L ts-input -n -v --line-numbers | head -10
   ```

3. Test connectivity from inside a container:
   ```bash
   sudo docker exec -it label-studio-<project-name> curl -v http://<TAILSCALE_IP>:8805/api/health
   ```
   This should return a 200 OK response.

4. Check service status for errors:
   ```bash
   sudo systemctl status label-studio-tailscale.service
   sudo journalctl -u label-studio-tailscale.service -n 50
   ```

**If the service fails to start:**

- Verify Tailscale is running: `sudo systemctl status tailscaled`
- Check that the Tailscale IP in the service file matches your actual Tailscale IP: `tailscale ip -4`
- Ensure Docker is running: `sudo systemctl status docker`

### Alternative: Manual iptables Rule (Temporary)

If you prefer not to use the systemd service, you can manually add the iptables rule. Note that this rule will be lost after a reboot:

```bash
# Replace <TAILSCALE_IP> with your server's Tailscale IP
sudo iptables -I ts-input 3 -s 172.16.0.0/12 -d <TAILSCALE_IP> -p tcp -m multiport --dports 8800:8850 -j ACCEPT
```

To verify:
```bash
sudo iptables -L ts-input -n -v --line-numbers
```

## Rebuilding Data and Annotations

When you have existing data with labels that need to be reconstructed or reimported into Label Studio, use the provided scripts to rebuild your dataset and annotations in the correct format.

### Available Scripts

The `scripts/` directory contains utilities for different annotation formats:

- **Detection format**: `scripts/make_json_annotation_for_detection.py`
- **Segmentation with polygons**: `scripts/make_json_annotation_for_segmentation.py`

### Step-by-Step Process

1. **Prepare your annotation JSON file:**

   **For detection datasets:**
   ```bash
   python scripts/make_json_annotation_for_detection.py
   ```

   **For segmentation with polygons:**
   ```bash
   python scripts/make_json_annotation_for_segmentation.py
   ```

2. **Upload annotation JSON to GCS:**
   ```bash
   gsutil cp your_annotations.json gs://hbai-label-studio/{your_project_name}/projects/annotations_json/{project_number_in_label_studio}/
   ```

3. **Upload data images to GCS:**
   ```bash
   gsutil -m cp -r your_images_folder/* gs://hbai-label-studio/{your_project_name}/projects/{project_number_in_label_studio}/
   ```

4. **Configure Label Studio project:**

   a. **Go to your project settings** in the Label Studio UI

   b. **Add Source Cloud Storage:**
   - Navigate to Settings → Cloud Storage → Source Storage
   - Add new GCS storage pointing to your annotation JSON file:
     ```
     gs://hbai-label-studio/projects/annotations_json/{project_number_in_label_studio}/
     ```

   c. **Sync the source storage:**
   - Click "Sync" on the added source cloud storage
   - This will import all the pre-annotated data into your Label Studio project

### File Structure in GCS

After following the process, your GCS bucket structure should look like:

```
gs://hbai-label-studio/{your_project_name}/
├── projects/
│   ├── {project_number_in_label_studio}/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── ...
│   └── annotations_json/
│       └── {project_number_in_label_studio}/
│           └── your_annotations.json
```

### Important Notes

- Replace `{your_project_name}` with the actual name of your project
- Replace `{project_number_in_label_studio}` with your actual project number from the Label Studio UI
- Ensure your images are accessible from the annotation JSON file paths
- The annotation JSON should contain proper Label Studio format annotations
- Always test with a small subset of data first before uploading large datasets

## GCS Dataset Structure for Computer Vision Projects

Each Computer Vision project follows a standardized structure in Google Cloud Storage to organize datasets, annotations, and backups efficiently.

### Complete Project Structure

```
gs://hbai-label-studio/{your_project_name}/
├── db_backup/
│   ├── label_studio_{your-project-name}_20250101_120000.sqlite3
│   ├── label_studio_{your-project-name}_20250102_120000.sqlite3
│   └── ...
├── projects/
│   ├── 1/                          # Project ID 1 images
│   │   ├── image001.jpg
│   │   ├── image002.jpg
│   │   └── ...
│   ├── 2/                          # Project ID 2 images
│   │   ├── image001.jpg
│   │   ├── image002.jpg
│   │   └── ...
│   ├── .../                        # Additional project directories
│   └── annotations_json/
│       ├── 1/                      # Project ID 1 annotations
│       │   └── annotations.json
│       ├── 2/                      # Project ID 2 annotations
│       │   └── annotations.json
│       └── .../                    # Additional annotation directories
```

### Directory Breakdown

**`db_backup/`**
- Contains automated database backups with timestamps
- Format: `label_studio_{your-project-name}_${TIMESTAMP}.sqlite3`
- Essential for data recovery and server migration

**`projects/{project_id}/`**
- Contains all image files for each Label Studio project
- Project ID corresponds to the project number in Label Studio UI
- Supports common image formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`

**`projects/annotations_json/{project_id}/`**
- Contains annotation JSON files for pre-labeled data
- Used for importing existing annotations into Label Studio
- JSON format must match Label Studio's annotation schema

### Usage Examples

**For a project named "traffic-detection":**
```
gs://hbai-label-studio/traffic-detection/
├── db_backup/
│   └── label_studio_traffic-detection_20250926_090000.sqlite3
├── projects/
│   ├── 1/                          # Detection project
│   │   ├── car_001.jpg
│   │   ├── car_002.jpg
│   │   └── truck_001.jpg
│   ├── 2/                          # Segmentation project
│   │   ├── road_001.jpg
│   │   ├── road_002.jpg
│   │   └── intersection_001.jpg
│   └── annotations_json/
│       ├── 1/
│       │   └── detection_annotations.json
│       └── 2/
│           └── segmentation_annotations.json
```
