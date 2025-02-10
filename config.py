'''Environmental variables provider'''
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URL = os.getenv("MONGO_URL")
    DB = os.getenv("DB")
    GENERAL_COLLECTION = os.getenv("GENERAL_COLLECTION")
    PLANTS_COLLECTION = os.getenv("PLANTS_COLLECTION")
    DEVICES_COLLECTION = os.getenv("DEVICES_COLLECTION")
    USERS_COLLECTION = os.getenv("USERS_COLLECTION")
    CLEANUP_THRESHOLD = int(os.getenv("CLEANUP_THRESHOLD"))
    CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL"))


    