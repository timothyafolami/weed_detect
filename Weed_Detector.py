import os
import cv2
import zipfile
import numpy as np
import streamlit as st
from io import BytesIO
from PIL import Image
from ultralytics import YOLO
from utils import create_shapefile_with_latlon


# Define paths
path_to_store_bounding_boxes = 'detect/'
path_to_save_shapefile = 'weed_detections.shp'

# Ensure the output directories exist
os.makedirs(path_to_store_bounding_boxes, exist_ok=True)

# loading a custom model
model = YOLO('new_yolov8_best.pt')

# Mapping of class labels to readable names (assuming 'weeds' is class 1)
class_names = ["citrus area", "trees", "weeds", "weeds and trees" ]


# Streamlit UI
st.title("Weed Detection and Shapefile Creation")

# Input coordinates for image corners
st.sidebar.header("Image Coordinates")
top_left = st.sidebar.text_input("Top Left (lon, lat)", value="-48.8864783, -20.5906375")
top_right = st.sidebar.text_input("Top Right (lon, lat)", value="-48.8855653, -20.5906264")
bottom_right = st.sidebar.text_input("Bottom Right (lon, lat)", value="-48.8855534, -20.5914861")
bottom_left = st.sidebar.text_input("Bottom Left (lon, lat)", value="-48.8864664, -20.5914973")

# Convert input coordinates to tuples
image_coords = [
    tuple(map(float, top_left.split(','))),
    tuple(map(float, top_right.split(','))),
    tuple(map(float, bottom_right.split(','))),
    tuple(map(float, bottom_left.split(',')))
]

# Upload image
uploaded_image = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

if uploaded_image is not None:
    # Display uploaded image
    st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
    img = Image.open(uploaded_image)
    img_array = np.array(img)
    image_height, image_width, _ = img_array.shape
    temp_image_path = "temp_uploaded_image.png"
    image = Image.open(uploaded_image)
    image.save(temp_image_path)

    # Perform weed detection on button click
    if st.button("Detect Weeds"):
        # Perform model prediction
        results = model.predict(temp_image_path, imgsz=640, conf=0.2, iou=0.4)
        results = results[0]
        
        weed_bboxes = []

        for i, box in enumerate(results.boxes):
            tensor = box.xyxy[0]
            x1 = int(tensor[0].item())
            y1 = int(tensor[1].item())
            x2 = int(tensor[2].item())
            y2 = int(tensor[3].item())
            conf = box.conf[0].item()  # Confidence score
            label = box.cls[0].item()  # Class label

            # Debugging output to ensure boxes are detected
            print(f"Box {i}: ({x1}, {y1}), ({x2}, {y2}), label: {label}, confidence: {conf}")

            # Only process if the detected class is "weeds"
            if class_names[int(label)] == "weeds":
                print("weed detected")
                # Draw bounding box on the image
                cv2.rectangle(img_array, (x1, y1), (x2, y2), (255, 0, 255), 3)
                # Save the bounding box coordinates
                weed_bboxes.append((x1, y1, x2, y2))

        # Save the image with bounding boxes
        detected_image_path = os.path.join(path_to_store_bounding_boxes, "detected_image.png")
        cv2.imwrite(detected_image_path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

        # Display the image with bounding boxes
        st.image(img_array, caption="Detected Weeds", use_column_width=True)

        # Create shapefile with bounding boxes
        create_shapefile_with_latlon(weed_bboxes, (image_width, image_height), image_coords, path_to_save_shapefile)

        # Create ZIP file of the shapefile components
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for filename in ['weed_detections.shp', 'weed_detections.shx', 'weed_detections.dbf']:
                zip_file.write(filename, os.path.basename(filename))
        zip_buffer.seek(0)

        # Download ZIP file
        st.download_button(
            label="Download Shapefile ZIP",
            data=zip_buffer,
            file_name="weed_detections.zip",
            mime="application/zip"
        )
