#!/usr/bin/env python3
"""
Label Studio Webhook Listener for GCS File Deletion - V2

This service listens for Label Studio events and:
1. Caches task metadata when tasks are created/updated
2. Deletes GCS files when tasks are deleted using the cached metadata

Setup:
1. Set environment variables:
   - GOOGLE_APPLICATION_CREDENTIALS: path to your GCS service account key
   - GCS_BUCKET_NAME: your GCS bucket name
   - WEBHOOK_SECRET: optional webhook secret for authentication
   - WEBHOOK_PORT: port to listen on (default: 8000)

2. In Label Studio UI:
   - Go to Settings → Webhooks
   - Add webhook URL: http://172.22.0.2:8000/webhook
   - Enable "Send payload" and "Send for all actions"

Usage:
    python webhook_listener_v2.py
"""

import os
import json
import logging
import sqlite3
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from contextlib import contextmanager

from flask import Flask, request, jsonify
from google.cloud import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'hbai-label-studio')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')
WEBHOOK_PORT = int(os.environ.get('WEBHOOK_PORT', '8000'))
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '/opt/secrets/key.json')
DB_PATH = '/data/task_cache.db'
LS_DATABASE_PATH = os.environ.get('LS_DATABASE_PATH', '/ls-data/label_studio.sqlite3')

# Initialize Flask app
app = Flask(__name__)

# Initialize GCS client
storage_client = None

def init_database():
    """Initialize SQLite database for caching task metadata"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_metadata (
            task_id INTEGER PRIMARY KEY,
            project_id INTEGER,
            gcs_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def seed_cache_from_label_studio():
    """
    Seed the cache with existing tasks from Label Studio's database.
    This is called on startup to handle existing tasks that were created
    before the webhook listener was deployed.
    """
    if not os.path.exists(LS_DATABASE_PATH):
        logger.warning(f"Label Studio database not found at {LS_DATABASE_PATH}")
        logger.warning("Skipping cache seeding. Only new tasks will be tracked.")
        return 0

    try:
        # Connect to Label Studio database
        ls_conn = sqlite3.connect(LS_DATABASE_PATH)
        ls_cursor = ls_conn.cursor()

        # Get all existing GCS storage links
        ls_cursor.execute('''
            SELECT task_id, key, storage_id
            FROM io_storages_gcsimportstoragelink
            WHERE object_exists = 1
        ''')

        existing_links = ls_cursor.fetchall()
        ls_conn.close()

        if not existing_links:
            logger.info("No existing GCS storage links found to seed")
            return 0

        # Seed the cache
        seeded_count = 0
        with get_db() as conn:
            cursor = conn.cursor()

            for task_id, gcs_path, storage_id in existing_links:
                # Check if already cached
                cursor.execute('SELECT 1 FROM task_metadata WHERE task_id = ?', (task_id,))
                if cursor.fetchone():
                    continue  # Already cached

                # Cache it
                cursor.execute('''
                    INSERT INTO task_metadata (task_id, project_id, gcs_path)
                    VALUES (?, ?, ?)
                ''', (task_id, storage_id, gcs_path))
                seeded_count += 1

            conn.commit()

        logger.info(f"✓ Seeded cache with {seeded_count} existing tasks from Label Studio database")
        return seeded_count

    except Exception as e:
        logger.error(f"Failed to seed cache from Label Studio database: {e}")
        return 0

@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def cache_task_metadata(task_id: int, project_id: int, gcs_path: str):
    """Cache task GCS path for later deletion"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_metadata (task_id, project_id, gcs_path)
                VALUES (?, ?, ?)
            ''', (task_id, project_id, gcs_path))
            conn.commit()
        logger.info(f"Cached metadata for task {task_id}: {gcs_path}")
    except Exception as e:
        logger.error(f"Failed to cache task metadata: {e}")

def get_cached_gcs_path(task_id: int) -> Optional[str]:
    """Get cached GCS path for a task"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT gcs_path FROM task_metadata WHERE task_id = ?', (task_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Failed to get cached GCS path: {e}")
        return None

def delete_cached_metadata(task_id: int):
    """Delete cached metadata after task deletion"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM task_metadata WHERE task_id = ?', (task_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to delete cached metadata: {e}")

def init_gcs_client():
    """Initialize Google Cloud Storage client"""
    global storage_client
    try:
        storage_client = storage.Client()
        logger.info(f"GCS client initialized successfully")
        # Test connection
        bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
        logger.info(f"Connected to GCS bucket: {bucket.name}")
    except Exception as e:
        logger.error(f"Failed to initialize GCS client: {e}")
        raise

def extract_gcs_path_from_task(task_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract GCS blob path from task data.

    Args:
        task_data: Task data from webhook payload

    Returns:
        GCS blob path (e.g., 'cv.oqtosh-factory/projects/2/image1.jpg') or None
    """
    try:
        # Try to get storage_filename first (most reliable)
        if 'storage_filename' in task_data:
            return task_data['storage_filename']

        # Try to extract from data field
        if 'data' in task_data:
            data = task_data['data']
            # Common fields: image, audio, video, text, etc.
            for field in ['image', 'audio', 'video', 'text', 'file']:
                if field in data and data[field]:
                    url = data[field]
                    # If it's a full URL, parse it
                    if url.startswith('gs://'):
                        # gs://bucket-name/path/to/file.jpg
                        path = url.replace(f'gs://{GCS_BUCKET_NAME}/', '')
                        return path
                    elif url.startswith('http'):
                        # For GCS signed URLs, the path is in the URL path
                        parsed = urlparse(url)
                        # Extract path after bucket name
                        # Example: /hbai-label-studio/cv.oqtosh-factory/projects/image.jpg
                        path_parts = parsed.path.strip('/').split('/', 1)
                        if len(path_parts) > 1:
                            return path_parts[1]
                    elif url.startswith('/data/'):
                        # Local path reference - try to extract from resolve URL
                        # This might be a reference to GCS file
                        continue
                    else:
                        # Direct path
                        return url

        logger.warning(f"Could not extract GCS path from task data: {task_data}")
        return None

    except Exception as e:
        logger.error(f"Error extracting GCS path: {e}")
        return None

def delete_gcs_blob(blob_path: str) -> bool:
    """
    Delete a blob from GCS bucket.

    Args:
        blob_path: Path to the blob in the bucket

    Returns:
        True if successful, False otherwise
    """
    try:
        bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(blob_path)

        if blob.exists():
            blob.delete()
            logger.info(f"Successfully deleted GCS blob: {blob_path}")
            return True
        else:
            logger.warning(f"GCS blob does not exist: {blob_path}")
            return False

    except Exception as e:
        logger.error(f"Failed to delete GCS blob {blob_path}: {e}")
        return False

def verify_webhook_signature(request) -> bool:
    """Verify webhook signature if WEBHOOK_SECRET is configured"""
    if not WEBHOOK_SECRET:
        return True

    signature = request.headers.get('X-Labelstudio-Signature', '')
    return signature == WEBHOOK_SECRET

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle webhook POST requests from Label Studio"""

    # Verify signature
    if not verify_webhook_signature(request):
        logger.warning("Invalid webhook signature")
        return jsonify({'error': 'Invalid signature'}), 401

    try:
        payload = request.get_json()

        if not payload:
            logger.warning("Empty webhook payload")
            return jsonify({'error': 'Empty payload'}), 400

        logger.info(f"Received webhook - action: {payload.get('action')}")
        logger.debug(f"Full payload: {json.dumps(payload, indent=2)}")

        # Extract event action
        action = payload.get('action')
        project_id = payload.get('project', {}).get('id')

        # Handle TASKS_CREATED - cache task metadata
        if action == 'TASKS_CREATED':
            tasks = payload.get('task') or payload.get('tasks') or []
            if not isinstance(tasks, list):
                tasks = [tasks]

            cached_count = 0
            for task in tasks:
                task_id = task.get('id')
                gcs_path = extract_gcs_path_from_task(task)

                if task_id and gcs_path:
                    cache_task_metadata(task_id, project_id, gcs_path)
                    cached_count += 1

            logger.info(f"Cached {cached_count} task(s) metadata")
            return jsonify({'status': 'cached', 'count': cached_count}), 200

        # Handle TASKS_DELETED - use cached metadata to delete GCS files
        elif action == 'TASKS_DELETED':
            tasks = payload.get('task') or payload.get('tasks') or []
            if not isinstance(tasks, list):
                tasks = [tasks]

            results = []
            for task in tasks:
                task_id = task.get('id')

                if not task_id:
                    continue

                # Try to get GCS path from cache
                gcs_path = get_cached_gcs_path(task_id)

                if gcs_path:
                    logger.info(f"Processing deletion for task {task_id}: {gcs_path}")
                    success = delete_gcs_blob(gcs_path)

                    if success:
                        delete_cached_metadata(task_id)

                    results.append({
                        'task_id': task_id,
                        'gcs_path': gcs_path,
                        'deleted': success
                    })
                else:
                    logger.warning(f"No cached GCS path found for task {task_id}")
                    results.append({
                        'task_id': task_id,
                        'error': 'No cached GCS path'
                    })

            return jsonify({
                'status': 'processed',
                'results': results
            }), 200

        else:
            # Other events - just acknowledge
            logger.info(f"Received event: {action} (not handled)")
            return jsonify({'status': 'acknowledged'}), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM task_metadata')
            cached_tasks = cursor.fetchone()[0]
    except:
        cached_tasks = -1

    return jsonify({
        'status': 'healthy',
        'bucket': GCS_BUCKET_NAME,
        'gcs_connected': storage_client is not None,
        'cached_tasks': cached_tasks
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with usage info"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM task_metadata')
            cached_tasks = cursor.fetchone()[0]
    except:
        cached_tasks = -1

    return jsonify({
        'service': 'Label Studio GCS Webhook Listener V2',
        'endpoints': {
            '/webhook': 'POST - Receive webhook events from Label Studio',
            '/health': 'GET - Health check',
            '/': 'GET - This help message'
        },
        'configuration': {
            'bucket': GCS_BUCKET_NAME,
            'port': WEBHOOK_PORT,
            'webhook_secret_configured': bool(WEBHOOK_SECRET),
            'cached_tasks': cached_tasks
        }
    }), 200

if __name__ == '__main__':
    # Initialize database
    init_database()

    # Initialize GCS client
    init_gcs_client()

    # Seed cache with existing tasks from Label Studio database
    logger.info("Seeding cache with existing tasks from Label Studio...")
    seeded_count = seed_cache_from_label_studio()
    if seeded_count > 0:
        logger.info(f"✓ Ready to track {seeded_count} existing tasks + new tasks from webhooks")
    else:
        logger.info("✓ Ready to track new tasks from webhooks")

    # Start Flask server
    logger.info(f"Starting webhook listener on port {WEBHOOK_PORT}")
    logger.info(f"GCS Bucket: {GCS_BUCKET_NAME}")
    logger.info(f"Label Studio Database: {LS_DATABASE_PATH}")
    logger.info(f"Webhook secret configured: {bool(WEBHOOK_SECRET)}")

    app.run(
        host='0.0.0.0',
        port=WEBHOOK_PORT,
        debug=False
    )
