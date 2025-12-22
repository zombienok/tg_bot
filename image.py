# image.py
import cv2
import numpy as np
from PIL import Image
import os

def get_photo_tags(image_path: str, clarifai_pat: str = None) -> str:
    """
    Simple image analysis function using OpenCV to detect basic features in the image.
    This is a lightweight alternative to heavy VLM models.
    """
    try:
        # Load image using OpenCV
        img = cv2.imread(image_path)
        
        if img is None:
            return "unable to read image"
        
        # Get basic image properties
        height, width, channels = img.shape
        
        # Convert BGR to RGB (OpenCV loads in BGR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Simple color-based analysis to identify common objects
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Define some common color ranges for object detection
        lower_red = np.array([0, 50, 50])
        upper_red = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([80, 255, 255])
        
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        
        lower_yellow = np.array([20, 50, 50])
        upper_yellow = np.array([30, 255, 255])
        
        # Create masks for different colors
        red_mask1 = cv2.inRange(hsv, lower_red, upper_red)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = red_mask1 + red_mask2
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # Calculate the area of each color region
        total_pixels = height * width
        red_area = cv2.countNonZero(red_mask) / total_pixels
        green_area = cv2.countNonZero(green_mask) / total_pixels
        blue_area = cv2.countNonZero(blue_mask) / total_pixels
        yellow_area = cv2.countNonZero(yellow_mask) / total_pixels
        
        # Basic shape detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze shapes based on contour properties
        circular_shapes = 0
        rectangular_shapes = 0
        
        for contour in contours:
            # Calculate contour area and perimeter
            area = cv2.contourArea(contour)
            if area > total_pixels * 0.001:  # Only consider contours larger than 0.1% of image
                perimeter = cv2.arcLength(contour, True)
                if perimeter != 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    
                    # Approximate contour to polygon
                    approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
                    vertices = len(approx)
                    
                    if circularity > 0.7:  # More circular
                        circular_shapes += 1
                    elif vertices >= 4:  # Likely rectangular/square
                        rectangular_shapes += 1
        
        # Make educated guesses about the image content based on detected features
        dominant_colors = []
        if red_area > 0.1:
            dominant_colors.append("red")
        if green_area > 0.1:
            dominant_colors.append("green")
        if blue_area > 0.1:
            dominant_colors.append("blue")
        if yellow_area > 0.1:
            dominant_colors.append("yellow")
        
        # Combine findings to describe the image
        if circular_shapes > rectangular_shapes and "red" in dominant_colors:
            return "food item, likely pizza or round food"
        elif circular_shapes > rectangular_shapes and ("green" in dominant_colors or "red" in dominant_colors):
            return "fruit or vegetable, possibly tomato or apple"
        elif circular_shapes > 0:
            return "circular object"
        elif rectangular_shapes > 0:
            return "rectangular object"
        elif len(dominant_colors) > 0:
            return f"{dominant_colors[0]} colored object"
        else:
            return "object"
            
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return "object"