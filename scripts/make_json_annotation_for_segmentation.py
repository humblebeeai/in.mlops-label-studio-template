import json
import os
from PIL import Image
import logging
import base64

# Define label classes as per their indices
LABELS = [
    "Shelf",
]

# Set up logging
os.makedirs('annotations', exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('annotations/conversion_warnings.txt'),
        logging.StreamHandler()
    ]
)

def convert_annotations(txt_folder, image_folder, output_json):
    tasks = []
    txt_files = [f for f in os.listdir(txt_folder) if f.endswith(".txt")]
    
    # GCS configuration for Label Studio
    gcs_bucket = 'hbai-label-studio'
    gcs_path = 'gws-pepsi/projects/4' # change it according to your project setup

    # Process files
    for txt_file in txt_files:
        image_file = txt_file.replace(".txt", ".jpg")
        image_path = os.path.join(image_folder, image_file)
        txt_path = os.path.join(txt_folder, txt_file)
        
        # Check if the image exists locally
        if not os.path.exists(image_path):
            logging.warning(f"Image file {image_file} not found. Skipping annotation.")
            continue

        # Get image dimensions
        with Image.open(image_path) as img:
            image_width, image_height = img.size
        
        # Read and parse the .txt file
        with open(txt_path, 'r') as file:
            lines = file.readlines()
        
        annotations = []
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) < 3:  # Minimum: class_id + at least one point (x,y)
                logging.warning(f"Invalid format in {txt_file}. Skipping line.")
                continue

            try:
                label_index = int(parts[0])

                # Validate label index
                if label_index < 0 or label_index >= len(LABELS):
                    logging.warning(f"Invalid label index {label_index} in {txt_file}. Skipping line.")
                    continue

                label = LABELS[label_index]

                # Extract polygon points (x,y pairs)
                coordinate_values = list(map(float, parts[1:]))

                # Ensure we have an even number of coordinates (pairs of x,y)
                if len(coordinate_values) % 2 != 0:
                    logging.warning(f"Odd number of coordinates in {txt_file}, line {i+1}. Skipping.")
                    continue

                # Group coordinates into (x,y) pairs and convert to Label Studio format
                polygon_points = []
                for j in range(0, len(coordinate_values), 2):
                    x_norm = coordinate_values[j]  # Already normalized (0-1)
                    y_norm = coordinate_values[j + 1]  # Already normalized (0-1)

                    # Convert to percentage (0-100) for Label Studio
                    x_percent = x_norm * 100
                    y_percent = y_norm * 100

                    # Ensure values are within 0-100 range
                    x_percent = max(0, min(100, x_percent))
                    y_percent = max(0, min(100, y_percent))

                    polygon_points.append([x_percent, y_percent])

                # Need at least 3 points to form a polygon
                if len(polygon_points) < 3:
                    logging.warning(f"Insufficient points for polygon in {txt_file}, line {i+1}. Skipping.")
                    continue

            except ValueError:
                logging.warning(f"Not proper format values in {txt_folder}/{txt_file}. Skipping line.")
                continue

            annotations.append({
                "original_width": image_width,
                "original_height": image_height,
                "image_rotation": 0,
                "value": {
                    "points": polygon_points,
                    "closed": True,
                    "polygonlabels": [label]
                },
                "id": f"polygon_{i+1}",
                "from_name": "label",
                "to_name": "image",
                "type": "polygonlabels",
                "origin": "manual"
            })

        # Construct GCS URL for Label Studio
        image_url = f'gs://{gcs_bucket}/{gcs_path}/{image_file}'

        tasks.append({
            "data": {
                "image": image_url
            },
            "annotations": [{
                "result": annotations
            }]
        })

    # Save to JSON
    with open(output_json, 'w', encoding='utf-8') as outfile:
        json.dump(tasks, outfile, indent=4, ensure_ascii=False)


current_dir = os.getcwd()

# Define packs as a list of folders in 'data_with_names'
data_dir = os.path.join(current_dir, 'data')
# packs = [name for name in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, name))]
# print(f'packs: {packs}')



images_folder = os.path.join(data_dir, 'images')

# Paths to folders
txt_folder = f'data/labels'  # Folder containing .txt files
image_folder = f'data/images'     # Folder containing .jpg files
output_dir = f'annotations'
os.makedirs(output_dir, exist_ok=True)
output_json = f'{output_dir}/data_annotation.json'

convert_annotations(txt_folder, image_folder, output_json)