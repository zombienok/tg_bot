# image.py
from clarifai.client.model import Model
import os

def get_photo_tags(image_path: str, clarifai_pat: str) -> str:
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    model = Model("https://clarifai.com/clarifai/main/models/general-image-recognition", pat=clarifai_pat)
    resp = model.predict_by_bytes(image_bytes, input_type="image")
    concepts = resp.outputs[0].data.concepts
    return concepts[0].name if concepts else "something"