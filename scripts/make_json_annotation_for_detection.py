import json
import os
from PIL import Image
import logging
import base64

# Define label classes as per their indices
LABELS = [
    "cooler",
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
    gcs_path = 'gws-pepsi/projects/3' # change it according to your project setup

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
            if len(parts) < 5:  # Basic validation
                logging.warning(f"Invalid format in {txt_file}. Skipping line.")
                continue

            try:
                label_index = int(parts[0])
                x_center_ratio, y_center_ratio, width_ratio, height_ratio = map(float, parts[1:])
                
                # Validate label index
                if label_index < 0 or label_index >= len(LABELS):
                    logging.warning(f"Invalid label index {label_index} in {txt_file}. Skipping line.")
                    continue
                
                label = LABELS[label_index]
                
                # Convert YOLO coordinates to pixel coordinates
                x_center = x_center_ratio * image_width
                y_center = y_center_ratio * image_height
                width = width_ratio * image_width
                height = height_ratio * image_height

                # Calculate bounding box corners
                x_min = x_center - (width / 2)
                y_min = y_center - (height / 2)

                # Normalize to 0-100 range
                x_min_normalized = (x_min / image_width) * 100
                y_min_normalized = (y_min / image_height) * 100
                width_normalized = (width / image_width) * 100
                height_normalized = (height / image_height) * 100

                # Ensure no negative values
                if x_min_normalized < 0:
                    x_min_normalized = 0
                if y_min_normalized < 0:
                    y_min_normalized = 0
                if width_normalized < 0:
                    width_normalized = 0
                if height_normalized < 0:
                    height_normalized = 0

            except ValueError:
                logging.warning(f"Not proper format values in {txt_folder}/{txt_file}. Skipping line.")
                continue

            annotations.append({
                "id": f"result{i+1}",
                "type": "rectanglelabels",
                "from_name": "label",
                "to_name": "image",
                "value": {
                    "x": x_min_normalized,
                    "y": y_min_normalized,
                    "width": width_normalized,
                    "height": height_normalized,
                    "rectanglelabels": [label]
                }
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