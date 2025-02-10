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
    GAP_BETWEEN_PUBLISHES = int(os.getenv("GAP_BETWEEN_PUBLISHES", 10))
    DATA_COLLECTION_INTERVAL = int(os.getenv("DATA_COLLECTION_INTERVAL", 3))  # seconds
    DATA_POINTS_FOR_AVERAGE = int(os.getenv("DATA_POINTS_FOR_AVERAGE", 10))
    CONFIG_FILE = os.getenv("CONFIG_FILE")
    REGISTRATION_INTERVAL = int(os.getenv("REGISTRATION_INTERVAL"))


class SensorConfig:
    MIN_SOIL_MOISTURE = os.getenv("MIN_SOIL_MOISTURE")
    MAX_SOIL_MOISTURE = os.getenv("MAX_SOIL_MOISTURE")
