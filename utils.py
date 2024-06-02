import os
import cv2
import zipfile
import shapefile
import numpy as np
from io import BytesIO
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from PIL import Image


def convert_pixel_to_latlon(x, y, image_width, image_height, image_coords):
    top_left, top_right, bottom_right, bottom_left = image_coords
    
    lon_top = top_left[0] + (top_right[0] - top_left[0]) * (x / image_width)
    lon_bottom = bottom_left[0] + (bottom_right[0] - bottom_left[0]) * (x / image_width)
    lat_left = top_left[1] + (bottom_left[1] - top_left[1]) * (y / image_height)
    lat_right = top_right[1] + (bottom_right[1] - top_right[1]) * (y / image_height)
    
    lon = lon_top + (lon_bottom - lon_top) * (y / image_height)
    lat = lat_left + (lat_right - lat_left) * (x / image_width)
    
    return lon, lat

# Function to create a shapefile with image dimensions and bounding boxes
def create_shapefile_with_latlon(bboxes, image_shape, image_coords, shapefile_path):
    w = shapefile.Writer(shapefile_path)
    w.field('id', 'C')

    img_width, img_height = image_shape

    # Add bounding boxes for weeds
    for idx, (x1, y1, x2, y2) in enumerate(bboxes):
        top_left = convert_pixel_to_latlon(x1, y1, img_width, img_height, image_coords)
        top_right = convert_pixel_to_latlon(x2, y1, img_width, img_height, image_coords)
        bottom_left = convert_pixel_to_latlon(x1, y2, img_width, img_height, image_coords)
        bottom_right = convert_pixel_to_latlon(x2, y2, img_width, img_height, image_coords)

        poly = Polygon([top_left, top_right, bottom_right, bottom_left, top_left])
        w.poly([poly.exterior.coords])
        w.record(f'weed_{idx}')

    w.close()