# -*- coding: utf-8 -*-
"""ALPR.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/171_OC4UYNsoQHZ7Gn7vwc3YCVujYc79D
"""

!pip install arabic_reshaper
!pip install easyocr
!pip install python-bidi
!pip install networkx
# !sudo apt install tesseract-ocr
# !sudo apt-get install tesseract-ocr-ara
# !pip install pytesseract
!python -m pip install paddlepaddle-gpu==2.3.1.post116 -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html
!pip install paddleocr

# from google.colab import drive
# drive.mount('/content/drive')

# !nvidia-smi

import paddle
paddle.utils.run_check()

import torch
import cv2
import time
import re
import numpy as np
import easyocr
import matplotlib.pyplot as plt
from pathlib import Path
import os
from PIL import ImageFont, ImageDraw, Image
import arabic_reshaper 
from bidi.algorithm import get_display
import matplotlib.gridspec as gridspec
from paddleocr import PaddleOCR

#EASY_OCR = easyocr.Reader(['ar']) ### ar for arabic
OCR_TH = 0.5
ocr = PaddleOCR(lang="arabic", use_angle_cls=True)

print(f"[INFO] Loading model... ")
    
model =  torch.hub.load('ultralytics/yolov5', 'custom', path= '/content/drive/MyDrive/Task/best.pt',force_reload=True) 

classes = model.names 

print(f"[INFO] Model loaded!")

plates = []
def detectx (frame, model):
    frame = [frame]
    print(f"[INFO] Detecting. . . ")
    results = model(frame)
 

    labels, cordinates = results.xyxyn[0][:, -1], results.xyxyn[0][:, :-1]

    return labels, cordinates


def plot_boxes(results, frame,classes):

    """
    --> This function takes results, frame and classes
    --> results: contains labels and coordinates predicted by model on the given frame
    --> classes: contains the strting labels

    """
    labels, cord = results
    n = len(labels)
    x_shape, y_shape = frame.shape[1], frame.shape[0]

    print(f"[INFO] Total {n} detections. . . ")
    print(f"[INFO] Looping through all detections. . . ")


    
    for i in range(n):
        row = cord[i]
        if row[4] >= 0.5: 
            print(f"[INFO] Extracting BBox coordinates. . . ")
            x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape) ## BBOx coordniates
            text_d = classes[int(labels[i])]

            coords = [x1,y1,x2,y2]

            plate_num = recognize_plate_easyocr(img = frame, coords= coords, reader= ocr, region_threshold= OCR_TH)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2) ## BBox
            cv2.rectangle(frame, (x1-30, y1-30), (x2+50, y1), (0, 255,0), -1) ## for text label background
            reshaped_text = arabic_reshaper.reshape(plate_num)
            bidi_text = get_display(reshaped_text)
            fontpath = "/content/drive/MyDrive/Task/arial.ttf"
            font = ImageFont.truetype(fontpath, 24)
            img_pil = Image.fromarray(frame)
            draw = ImageDraw.Draw(img_pil)
            draw.text((x1, y1-30),bidi_text, font = font, fill="black")
            frame = np.array(img_pil)




    return frame




def recognize_plate_easyocr(img, coords,reader,region_threshold):
    # separate coordinates from box
    xmin, ymin, xmax, ymax = coords
    
    nplate = img[int(ymin)+10:int(ymax), int(xmin)-10:int(xmax)+10]
    
   
    kernel = np.ones((1, 1), np.uint8)
    dilated = cv2.dilate(nplate, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)
 
    
    ocr_result = ocr.ocr(nplate, det=False, cls=True)
    
    cv2_imshow(nplate)

    text = filter_text(region=nplate, ocr_result=ocr_result, region_threshold= region_threshold)

    if len(text) ==1:
        text = text[0].upper()
    return text



def filter_text(region, ocr_result, region_threshold):
    rectangle_size = region.shape[0]*region.shape[1]
    
    plate = [] 
    print(ocr_result)
    for result in ocr_result:
   
        if result[0][1] >= region_threshold and result[0][0] != "مصر":
            plate.append(result[0][0].replace(":",""))
    plate = plate[::-1]
    plate = [" ".join(plate)]
    print(plate)
    plates.append(plate)
    return plate

# from google.colab.patches import cv2_imshow
def main(img_path=None, vid_path=None):


    if img_path != None:
        print(f"[INFO] Working with image: {img_path}")
        img_out_name = f"./output/result_{img_path.split('/')[-1]}"

        
        frame = cv2.imread(img_path) 
        frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        
        results = detectx(frame, model = model)   

        frame = cv2.cvtColor(frame,cv2.COLOR_RGB2BGR)

        frame = plot_boxes(results, frame,classes = classes)
        

        while True:

            cv2_imshow(frame)

            
            print(f"[INFO] Exiting. . . ")

            cv2.imwrite(f"{img_out_name}",frame)

            break


    elif vid_path !=None:
        print(f"[INFO] Working with video: {vid_path}")

        
        cap = cv2.VideoCapture(vid_path)

        vid_out = f"{Path(vid_path).stem}_temp{Path(vid_path).suffix}"
        if vid_out:

            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            codec = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(vid_out, codec, fps, (width, height))

        # assert cap.isOpened()
        frame_no = 1

        while cap.isOpened():
            # start_time = time.time()
            ret, frame = cap.read()
            if ret  and frame_no %1 == 0:
                print(f"[INFO] Working with frame {frame_no} ")

                frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                results = detectx(frame, model = model)
                frame = cv2.cvtColor(frame,cv2.COLOR_RGB2BGR)


                frame = plot_boxes(results, frame,classes = classes)
                

                if vid_out:
                    print(f"[INFO] Saving output video. . . ")
                    out.write(frame)

                frame_no += 1
            if ret != True:
                break
                
        
        print(f"[INFO] Cleaning up. . . ")
        out.release()
