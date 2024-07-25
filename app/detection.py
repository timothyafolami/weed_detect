import os
import cv2
import zipfile
import shapefile
import numpy as np
from shapely.geometry import Polygon
from io import BytesIO
from PIL import Image
import rasterio
from rasterio.windows import Window
from ultralytics import YOLO
from db_bucket import upload_file_to_bucket  # Import the bucket upload function

# Paths and configurations
path_to_store_bounding_boxes = 'detect/'
path_to_save_shapefile = 'weed_detections'
slice_size = 3000

# Load YOLO model (update the path to your model)
model = YOLO('new_yolov8_best.pt')

class_names = ["citrus area", "trees", "weeds", "weeds and trees"]

# Function to initialize directories
def initialize_directories():
    os.makedirs(path_to_store_bounding_boxes, exist_ok=True)
    os.makedirs("slices", exist_ok=True)

# Function to slice the GeoTIFF
async def slice_geotiff(file_path, slice_size=3000):
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
async def detect_weeds_in_slices(slices):
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

async def create_zip():
    # Create a zip file
    zip_file_path = "weed_detections.zip"
    with zipfile.ZipFile(zip_file_path, 'w') as zip_file:
        for ext in ['shp', 'shx', 'dbf']:
            file_name = f"{path_to_save_shapefile}.{ext}"
            if os.path.exists(file_name):
                zip_file.write(file_name, os.path.basename(file_name))

    return zip_file_path

# Function to clean up created files and directories
def cleanup():
    # Remove the zip file
    if os.path.exists("weed_detections.zip"):
        os.remove("weed_detections.zip")
        
    # Remove the geotiff file
    if os.path.exists("uploaded_geotiff.tif"):
        os.remove("uploaded_geotiff.tif")
    
    # Remove shapefile components
    for ext in ['shp', 'shx', 'dbf']:
        file_name = f"{path_to_save_shapefile}.{ext}"
        if os.path.exists(file_name):
            os.remove(file_name)

    # Remove slices
    if os.path.exists("slices"):
        for file in os.listdir("slices"):
            file_path = os.path.join("slices", file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir("slices")

    # Remove detected bounding boxes
    if os.path.exists("detect"):
        for file in os.listdir("detect"):
            file_path = os.path.join("detect", file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir("detect")
