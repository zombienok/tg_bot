from clarifai.rest import ClarifaiApp, client, Image
from dotenv import load_dotenv
import os
load_dotenv()
clarifai_pat = os.getenv('CLARIFAI_PAT')
app = ClarifaiApp(api_key=clarifai_pat)
model = app.public_models.general_model 
filename = 'C:\\Users\\sanya\\Pictures\\котьеки\\_Y5zJ6qsNEM.jpg'
image = Image(file_obj=open(filename, 'rb'))
response = model.predict([image])
concepts = response['outputs'][0]['data']['concepts']
for concept in concepts:
    print(concept['name'], concept['value'])