import datetime
import json

class Event:
    def __init__(self, plate, image, created_date):
        self.plate = plate
        self.image = image
        self.created_date = created_date