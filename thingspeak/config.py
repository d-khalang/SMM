'''Environmental variables provider'''
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CATALOG_URL = os.getenv("CATALOG_URL")
    PLANTS_ENDPOINT = os.getenv("PLANTS_ENDPOINT")
    DEVICES_ENDPOINT = os.getenv("DEVICES_ENDPOINT")
    MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID")
    AVAILABLE_MEASURE_TYPES = os.getenv("AVAILABLE_MEASURE_TYPES", "").split(",")

    UPDATE_INTERVAL = int(os.getenv("TOPICS_UPDATE_INTERVAL", 600))  # seconds
    THINGSPEAK_URL = os.getenv("THINGSPEAK_URL")
    THINGSPEAK_UPDATE_ENDPOINT = os.getenv("THINGSPEAK_UPDATE_ENDPOINT")
    THINGSPEAK_CHANNELS_ENDPOINT = os.getenv("THINGSPEAK_CHANNELS_ENDPOINT")
    USER_API_KEY = os.getenv("USER_API_KEY")


