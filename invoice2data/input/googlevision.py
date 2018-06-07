# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 16:07:11 2018

@author: michael.stone
"""

def to_text(path):
    """Wrapper around Google Vision API.

    Parameters
    ----------
    path : str
        path of receipt

    Returns
    -------
    out : str
        returns extracted text from pdf

    Raises
    ------
    EnvironmentError:
        If pdftotext library is not found
    """
        

    import io
    import os
#    import logging as logger
    
    # Set the environment variable where the Google Cloud Application credentials are stored
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "D:\Dropbox\Dropbox\Invigor\ReceiptScanning\ReceiptScanning-3f4289905a3d.json"
    
    # Imports the Google Cloud client library
    from google.cloud import vision
    from google.cloud.vision import types
    
    # Instantiates a client
    client = vision.ImageAnnotatorClient()
    
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

#    else:
#        raise EnvironmentError('pdftotext not installed. Can be downloaded from https://poppler.freedesktop.org/')
