# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 16:07:11 2018

@author: michael.stone
"""

import io
import os

# Set the environment variable where the Google Cloud Application credentials are stored
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "D:/Dropbox/Dropbox/Invigor/ReceiptScanning/ReceiptScanning-3f4289905a3d.json"

# Imports the Google Cloud client library
from google.cloud import vision
from google.cloud.vision import types

# Instantiates a client
client = vision.ImageAnnotatorClient()

# The name of the image file to annotate
file_name = os.path.join(
    os.path.dirname(__file__),
    'D:/Dropbox/Dropbox/Invigor/ReceiptScanning/receipts/Pepper_Lunch_1.png')

# Loads the image into memory
with io.open(file_name, 'rb') as image_file:
    content = image_file.read()

image = types.Image(content=content)

# Perform OCR detection on the image file
text_response = client.text_detection(image=image)
text = text_response.full_text_annotation.text

# Perform logo detection on the image file
logo_response = client.logo_detection(image=image)
logo = logo_response.logo_annotations[0].description

