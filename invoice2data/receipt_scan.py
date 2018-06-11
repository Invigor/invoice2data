#!/usr/bin/env python
# -*- coding: utf-8 -*-

from extract.loader import read_templates_s3
import boto3
import uuid
import io
import os
import requests
import logging as logger
from PIL import Image
from io import BytesIO
import json

logger.basicConfig(filename='receipt_scan.log',level=logger.DEBUG)

def to_text_azure(path):
    
    # Replace <Subscription Key> with your valid subscription key.
    subscription_key = "a4143eb2e01f421f9ee365e678086331"
    assert subscription_key
    
    # You must use the same region in your REST call as you used to get your
    # subscription keys. For example, if you got your subscription keys from
    # westus, replace "westcentralus" in the URI below with "westus".
    #
    # Free trial subscription keys are generated in the westcentralus region.
    # If you use a free trial subscription key, you shouldn't need to change
    # this region.
    vision_base_url = "https://australiaeast.api.cognitive.microsoft.com/vision/v2.0/"
    
    text_recognition_url = vision_base_url + "recognizeText"
    
    headers  = {'Ocp-Apim-Subscription-Key': subscription_key}
    # Note: The request parameter changed for APIv2.
    # For APIv1, it is 'handwriting': 'true'.
    params   = {'mode': 'Printed'}
    data     = {'url': path}
    response = requests.post(
        text_recognition_url, headers=headers, params=params, json=data)
    response.raise_for_status()
    
    # Extracting handwritten text requires two API calls: One call to submit the
    # image for processing, the other to retrieve the text found in the image.
    
    # Holds the URI used to retrieve the recognized text.
    # operation_url = response.headers["Operation-Location"]
    
    # The recognized text isn't immediately available, so poll to wait for completion.
    import time
    analysis = {}
    while "recognitionResult" not in analysis:
        response_final = requests.get(
            response.headers["Operation-Location"], headers=headers)
        analysis = response_final.json()
        time.sleep(1)

    # Build response from response object
    azure_text = ''
    for line in analysis['recognitionResult']['lines']:
        azure_text = azure_text + line['text']+' '
        
    return azure_text

def to_text_google(path):

#    import logging as logger
    
    # Set the environment variable where the Google Cloud Application credentials are stored
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "ReceiptScanning-3f4289905a3d.json"
    
    # Imports the Google Cloud client library
    from google.cloud import vision
    from google.cloud.vision import types
    
    # Instantiates a client
    client = vision.ImageAnnotatorClient()
    
    # Check if we have a URL or a file path
    if path.startswith('http'):
        
        # Get image from URI
        response = requests.get(path)
        img = Image.open(BytesIO(response.content))
        width,height = img.size
        
        # Check if image needs to be rotated
        if width > height:
           img  = img.rotate(90,expand=1 )
        
        buffer = BytesIO()
        img.save(buffer, "PNG")
        content = buffer.getvalue()
        
    else:

        # The name of the image file to annotate
        file_name = os.path.join(
            os.path.dirname(__file__),path)
        
        # Loads the image into memory
        with io.open(file_name, 'rb') as image_file:
            content = image_file.read()
        
    image = types.Image(content=content)
        
    # Perform OCR detection on the image file
    text_response = client.text_detection(image=image)
    return text_response.full_text_annotation.text

def extract_data(invoicefile):

    templates = read_templates_s3()

    # Call Google Cloud Vision API
    try:
        extracted_str_google = to_text_google(invoicefile).decode('utf-8')
    except:
        extracted_str_google = to_text_google(invoicefile)
        
    logger.debug(extracted_str_google)
    print('Google:')
    print(extracted_str_google)

    # Check if Google has returned anything
    if extracted_str_google:
        for t in templates:
            optimized_str = t.prepare_input(extracted_str_google)
    
            if t.matches_input(optimized_str):
                google_results = t.extract(optimized_str)
                
                # Check if there are any 'Not Found'
                if 'Not Found' in google_results.values():
                    
                    # Call Azure OCR API
                    try:
                        extracted_str_azure = to_text_azure(invoicefile).decode('utf-8')
                    except:
                        extracted_str_azure = to_text_azure(invoicefile)
    
                    print('Azure:')
                    print(extracted_str_azure)
        
                    optimized_str = t.prepare_input(extracted_str_azure)
                    azure_results = t.extract(optimized_str)
                    
                    # Loop through google_results to find keys which were not found
                    for key, value in google_results.items():
                        if value == 'Not Found':
                            
                            # If Azure has found a value, replace the Google value
                            if azure_results[key] != 'Not Found':
                                google_results[key] = azure_results[key]
                                
                return google_results
        
    else:
        
        # Try Azure
        try:
            extracted_str_azure = to_text_azure(invoicefile).decode('utf-8')
        except:
            extracted_str_azure = to_text_azure(invoicefile)
            
        print('Azure:')
        print(extracted_str_azure)

        for t in templates:
            optimized_str = t.prepare_input(extracted_str_azure)
    
            if t.matches_input(optimized_str):
                azure_results = t.extract(optimized_str)
                
                return azure_results
            

    logger.debug('No template for %s', invoicefile)
    return False

def handler(event, context):

    logger.info('Starting:')

    s3_client = boto3.client('s3')

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        path = '/tmp/{}{}'.format(uuid.uuid4(), key)

        logger.info('Processing object name: %s',key)

        # Download file to temporary storage
        s3_client.download_file(bucket, key, path)

        # Extract data from image
        res = extract_data(path)

        if res:

            logger.info('Result: %s',json.dumps(res))

            upload_path = '/tmp/analysed-{}'.format(key)+'.json'
            with open(upload_path, 'w+') as file:
                file.write(json.dumps(res))
                file.close()

            logger.debug('/tmp directory: %s',os.listdir('/tmp'))

            s3_client.upload_file(upload_path, bucket + '-analysed', key + '.json')

            logger.debug('Written results to %s',format(key))

        else:
            logger.info('No results from extract')