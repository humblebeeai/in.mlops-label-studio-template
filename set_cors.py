# first run - export GOOGLE_APPLICATION_CREDENTIALS="/root/label-studio/secrets/key.json"

from google.cloud import storage

def cors_configuration(bucket_name: str):
    """Set a bucket's CORS policies configuration."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    bucket.cors = [
        {
            "origin": ["*"],
            "responseHeader": ["Content-Type", "x-goog-resumable"],
            "method": ["PUT", "POST", "GET", "DELETE", "HEAD"],
            "maxAgeSeconds": 3600
        }
    ]
    bucket.patch()
    print(f"Set CORS policies for bucket {bucket.name}: {bucket.cors}")

if __name__ == "__main__":
    cors_configuration("hbai-label-studio")  # Replace with your bucket name