'''Environmental variables provider'''
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CATALOG_URL = os.getenv("CATALOG_URL")
    PLANTS_ENDPOINT = os.getenv("PLANTS_ENDPOINT")
    DEVICES_ENDPOINT = os.getenv("DEVICES_ENDPOINT")
    GENERAL_ENDPOINT = os.getenv("GENERAL_ENDPOINT")
    USERS_ENDPOINT = os.getenv("USERS_ENDPOINT")
    THINGSPEAK_URL = os.getenv("THINGSPEAK_URL")
    THINGSPEAK_CHANNELS_ENDPOINT = os.getenv("THINGSPEAK_CHANNELS_ENDPOINT")
    USER_API_KEY = os.getenv("USER_API_KEY")
    AVAILABLE_MEASURE_TYPES = os.getenv("AVAILABLE_MEASURE_TYPES", "").split(",")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    FULL_GROWING_TIME = int(os.getenv("FULL_GROWING_TIME"))


    

