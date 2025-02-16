from PIL import Image
import cv2
import torch
import math 
import function.utils_rotate as utils_rotate
from IPython.display import display
import os
import time
import argparse
import function.helper as helper
import json
from bson import json_util
import datetime
from kafka import KafkaProducer
import Event
from datetime import datetime

import requests
import json

# load model
yolo_LP_detect = torch.hub.load('yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=True, source='local')
yolo_license_plate = torch.hub.load('yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=True, source='local')
yolo_license_plate.conf = 0.60

prev_frame_time = 0
new_frame_time = 0

producer = KafkaProducer(bootstrap_servers='localhost:9092')
# vid = cv2.VideoCapture(0)
vid = cv2.VideoCapture("video.gif")
while(True):
    ret, frame = vid.read()
    
    plates = yolo_LP_detect(frame, size=640)
    list_plates = plates.pandas().xyxy[0].values.tolist()
    list_read_plates = set()
    for plate in list_plates:
        flag = 0
        x = int(plate[0]) # xmin
        y = int(plate[1]) # ymin
        w = int(plate[2] - plate[0]) # xmax - xmin
        h = int(plate[3] - plate[1]) # ymax - ymin  
        crop_img = frame[y:y+h, x:x+w]
        cv2.rectangle(frame, (int(plate[0]),int(plate[1])), (int(plate[2]),int(plate[3])), color = (0,0,225), thickness = 2)
        cv2.imwrite("crop.jpg", crop_img)
        rc_image = cv2.imread("crop.jpg")
        lp = ""
        for cc in range(0,2):
            for ct in range(0,2):
                lp = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                if lp != "unknown":
                    list_read_plates.add(lp)
                    cv2.putText(frame, lp, (int(plate[0]), int(plate[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
                    flag = 1
                    break
            if flag == 1:
                break
    new_frame_time = time.time()
    fps = 1/(new_frame_time-prev_frame_time)
    prev_frame_time = new_frame_time
    fps = int(fps)
    print("aaaaaaaaaaa: ", list_read_plates)
    cv2.putText(frame, str(fps), (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)
    cv2.imshow('frame', frame)
    
    if(list_read_plates != set()):
        image_name = datetime.today().strftime('%Y%m%d_%H%M%S')
        cv2.imwrite("./result/" + image_name + ".jpg", frame)
        created_date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        # upload image
        url = "http://103.21.151.166:8683/v1.0/upload/file"

        payload={}
        files=[
        ('file',('crop.jpg',open("./result/" + image_name + ".jpg",'rb'),'image/png'))
        ]
        headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'Authorization': 'Bearer '
        }

        response = requests.request("POST", url, headers=headers, data=payload, files=files)

        print(response.text)
        response = json.loads(response.text)
        image_name = ''
        for employee in response["data"]: 
            image_name = employee["fileDownloadUri"]
        
        data = Event.Event(list(list_read_plates)[0], image_name, created_date).__dict__
        producer.send('event-request-topic', json.dumps(data).encode("utf-8"))
        producer.flush()    
 
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

vid.release()
cv2.destroyAllWindows()