'''Environmental variables provider'''
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CATALOG_URL = os.getenv("CATALOG_URL")
    PLANTS_ENDPOINT = os.getenv("PLANTS_ENDPOINT")
    DEVICES_ENDPOINT = os.getenv("DEVICES_ENDPOINT")
    GENERAL_ENDPOINT = os.getenv("GENERAL_ENDPOINT")
    MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID")
    SOIL_MOSTURE_MIN = int(os.getenv("SOIL_MOSTURE_MIN"))
    SOIL_MOSTURE_SUITABLE = int(os.getenv("SOIL_MOSTURE_SUITABLE"))



