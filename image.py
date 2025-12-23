# image.py
import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import os

def get_photo_tags(image_path: str, clarifai_pat: str = None) -> str:
    """
    Image classification function using a pre-trained VLM (Vision-Language Model).
    Uses BLIP model for image understanding and description.
    """
    try:
        # Check if image file exists
        if not os.path.exists(image_path):
            return "image file does not exist"
        
        # Load a pre-trained BLIP model and processor
        # Using BLIP for image-to-text generation
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        
        # Load and process the image
        raw_image = Image.open(image_path).convert('RGB')
        
        # Generate image caption
        inputs = processor(raw_image, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=50)
        caption = processor.decode(out[0], skip_special_tokens=True)
        
        return caption
            
    except Exception as e:
        print(f"Error processing image with VLM: {str(e)}")
        # Fallback to a simple description
        return "object"