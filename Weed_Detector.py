import os
import cv2
import zipfile
import shapefile
import numpy as np
import streamlit as st
from io import BytesIO
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from PIL import Image
import rasterio
from rasterio.windows import Window
from ultralytics import YOLO

# Define paths
path_to_store_bounding_boxes = 'detect/'
path_to_save_shapefile = 'weed_detections.shp'
slice_size = 3000

# Ensure the output directories exist
os.makedirs(path_to_store_bounding_boxes, exist_ok=True)
os.makedirs("slices", exist_ok=True)

# Load YOLO model (update the path to your model)
model = YOLO('new_yolov8_best.pt')

class_names = ["citrus area", "trees", "weeds", "weeds and trees"]

# Function to slice the GeoTIFF
def slice_geotiff(file_path, slice_size=3000):
    slices = []
    with rasterio.open(file_path) as dataset:
        img_width = dataset.width
        img_height = dataset.height
        transform = dataset.transform

        for i in range(0, img_height, slice_size):
            for j in range(0, img_width, slice_size):
                window = Window(j, i, slice_size, slice_size)
                transform_window = rasterio.windows.transform(window, transform)
                slice_data = dataset.read(window=window)
                slice_img = Image.fromarray(slice_data.transpose(1, 2, 0))  # Convert to HWC format
                slice_filename = f"slices/slice_{i}_{j}.png"
                slice_img.save(slice_filename)
                slices.append((slice_filename, transform_window))
    return slices

# Function to create a shapefile with image dimensions and bounding boxes
def create_shapefile_with_latlon(bboxes, shapefile_path="weed_detections.shp"):
    w = shapefile.Writer(shapefile_path)
    w.field('id', 'C')
    
    for idx, (x1, y1, x2, y2, transform) in enumerate(bboxes):
        top_left = rasterio.transform.xy(transform, y1, x1, offset='center')
        top_right = rasterio.transform.xy(transform, y1, x2, offset='center')
        bottom_left = rasterio.transform.xy(transform, y2, x1, offset='center')
        bottom_right = rasterio.transform.xy(transform, y2, x2, offset='center')

        poly = Polygon([top_left, top_right, bottom_right, bottom_left, top_left])
        w.poly([poly.exterior.coords])
        w.record(f'weed_{idx}')
    
    w.close()

# Function to detect weeds in image slices
def detect_weeds_in_slices(slices):
    weed_bboxes = []
    img_width, img_height = slice_size, slice_size  # Assuming fixed slice size

    for slice_filename, transform in slices:
        img_array = np.array(Image.open(slice_filename))
        results = model.predict(slice_filename, imgsz=640, conf=0.2, iou=0.4)
        results = results[0]
        
        for i, box in enumerate(results.boxes):
            tensor = box.xyxy[0]
            x1 = int(tensor[0].item())
            y1 = int(tensor[1].item())
            x2 = int(tensor[2].item())
            y2 = int(tensor[3].item())
            conf = box.conf[0].item()
            label = box.cls[0].item()

            if class_names[int(label)] == "weeds":
                cv2.rectangle(img_array, (x1, y1), (x2, y2), (255, 0, 255), 3)
                weed_bboxes.append((x1, y1, x2, y2, transform))
        
        # Save the image with bounding boxes
        detected_image_path = os.path.join(path_to_store_bounding_boxes, os.path.basename(slice_filename))
        cv2.imwrite(detected_image_path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

    create_shapefile_with_latlon(weed_bboxes)

# Streamlit UI
st.title("Weed Detection and Shapefile Creation")

# Upload GeoTIFF file
uploaded_file = st.file_uploader("Upload a GeoTIFF file", type=["tif", "tiff"])

if uploaded_file is not None:
    with open("uploaded_geotiff.tif", "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("GeoTIFF file uploaded successfully!")
    
    # Slice GeoTIFF
    slices = slice_geotiff("uploaded_geotiff.tif", slice_size)
    
    # Display one of the slices
    if slices:
        sample_slice_path, _ = slices[0]
        sample_slice = Image.open(sample_slice_path)
        st.image(sample_slice, caption="Sample Slice", use_column_width=True)
    
    if st.button("Detect Weeds"):
        # Detect weeds in slices
        detect_weeds_in_slices(slices)
        
        # Display one of the detected images with bounding boxes
        sample_detected_image_path = os.path.join(path_to_store_bounding_boxes, os.path.basename(sample_slice_path))
        sample_detected_image = cv2.imread(sample_detected_image_path)
        st.image(cv2.cvtColor(sample_detected_image, cv2.COLOR_BGR2RGB), caption="Detected Weeds", use_column_width=True)
        
        # Create Shapefile
        create_shapefile_with_latlon()
        
        st.success("Weed detection complete. Shapefile generated.")
        
        # Display shapefile plot
        fig, ax = plt.subplots()
        sf = shapefile.Reader(path_to_save_shapefile)
        for shape in sf.shapes():
            poly = Polygon(shape.points)
            x, y = poly.exterior.xy
            ax.plot(x, y)
        plt.show()
        st.pyplot(fig)
        
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
