"""Pydantic models for validations and registration of plants and devices"""

from pydantic import BaseModel, ValidationError, ConfigDict
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime
from typing import List, Optional, Dict, Literal, Any
from config import Config
from utility import to_lower_camel_case, response_creator

client = MongoClient(Config.MONGO_URL)
db = client[Config.DB]
plants_collection = db[Config.PLANTS_COLLECTION]
devices_collection = db[Config.DEVICES_COLLECTION]
users_collection = db[Config.USERS_COLLECTION]


class BaseModelWithTimestamp(BaseModel):
    last_updated: Optional[str] = None
    # Lets the model to accept both camel and snake case. 
    # Plus, providing option to dump in both ways
    model_config = ConfigDict(
        alias_generator=to_lower_camel_case, populate_by_name=True
    )
    def model_dump_with_time(self, by_alias: bool = True, exclude_unset: bool = True) -> dict:
        """Adds a timestamp to the model before dumping"""
        self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Change the difult dump to be camelCase
        return self.model_dump(by_alias=by_alias, exclude_unset=exclude_unset)


class BaseModelAlias(BaseModel):
    # Lets the model to accept both camel and snake case. 
    # Plus, providing option to dump in both ways
    model_config = ConfigDict(
        alias_generator=to_lower_camel_case, populate_by_name=True
    )
    def model_dump(self, by_alias: bool = True, exclude_unset: bool = True) -> Dict[str, Any]:
        return super().model_dump(by_alias=by_alias, exclude_unset=exclude_unset)



class DeviceLocation(BaseModelAlias):
    plant_id: int

class ServicesDetail(BaseModelAlias):
    service_type: Literal["MQTT", "REST"]
    topics: Optional[List[str]] = None
    service_ip: Optional[str] = None

class Device(BaseModelWithTimestamp):
    device_id: int
    device_type: Literal["sensor", "actuator"]
    device_name: str
    device_location: DeviceLocation
    device_status: str
    status_options: List[str]
    measure_types: List[str]
    available_services: List[Literal["MQTT", "REST"]]
    services_details: List[ServicesDetail]

    @property
    def is_valid_status(self) -> bool:
        """Validate that device_status is one of status_options"""
        return self.device_status in self.status_options

    def save_to_db(self):
        print()
        try:
            # Add status validation before saving
            if not self.is_valid_status:
                raise ValueError(f"Invalid device status: {self.device_status}. Must be one of {self.status_options}")
                
            plant_id = self.device_location.plant_id

            # Check if the device's plant exists in the database
            self._check_plant_exists(plant_id)
            
            self._upsert_device()

            self._update_plant_device_inventory(plant_id)

        except Exception as e:
            print(f"Error saving device {self.device_id} to database: {str(e)}")
            return response_creator(False, message=f"Failed to registere the device: {str(e)}", status=500)

        return response_creator(True, message="Device registered successfully", status=200)


    ### Helper functions
    def _check_plant_exists(self, plant_id: int):
        plant = plants_collection.find_one({"plantId": plant_id})
        if not plant:
            print(f"Plant with id {plant_id} does not exist.")
            raise ValueError(f"Plant with id {plant_id} does not exist.")
    
        
    def _upsert_device(self):
        device_data = self.model_dump_with_time()
        device_update_result = devices_collection.update_one(
            {'deviceId': self.device_id},
            {'$set': device_data},
            upsert=True
        )
        if device_update_result.upserted_id:
            print(f"Inserted new device with ID {self.device_id}.")
        else:
            print(f"Updated existing device with ID {self.device_id}.")

    # Plus, updates plant's last update too
    def _update_plant_device_inventory(self, plant_id: int):
        plants_collection.update_one(
            {'plantId': plant_id},
            {
                '$addToSet': {'deviceInventory': self.device_id},
                '$set': {'lastUpdated': self.last_updated}
            }
        )
        print(f"Device id {self.device_id} upserted to plant {plant_id} device_inventory.")



class Plant(BaseModelWithTimestamp):
    plant_id: int
    plant_date: str
    device_inventory: list 

    def __init__(self, **data):
        super().__init__(**data)
        self.device_inventory = []

    @property
    def is_valid_date(self) -> bool:
        """Validate plant_date format"""
        try:
            datetime.strptime(self.plant_date, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def save_to_db(self) -> dict:
        print(f"Entering save_to_db method for plant_id: {self.plant_id}")
        print()
        try:
            if not self.is_valid_date:
                raise ValueError(f"Invalid plant_date format: {self.plant_date}. Must be YYYY-MM-DD")
            print(f"""Starting update/insert for plant {self.plant_id}...""")

            # Check if the plant already exists in the database
            existing_plant = plants_collection.find_one({"plantId": self.plant_id})
    
            # Prepare the data to update, excluding device_inventory if the plant already exists
            updated_data = self.model_dump_with_time()

            if existing_plant:
                print(f"Plant {self.plant_id} already exists in the database. Preparing to update.")
                # If the plant exists, we want to update only specific fields excluding device_inventory
                updated_data.pop("deviceInventory", None)
            
            # Perform the update or insert (upsert) for the plant in the transaction
            self._upsert_plant(updated_data)

        except PyMongoError as e:
            print(f"Error occurred durring update/insert: {e}.")
            return response_creator(False, message=f"Failed to registere the plant: {str(e)}", status=500)

        # print(f"Exiting save_to_db method for plant_id: {self.plant_id}\n")
        return response_creator(True, message="Plant registered successfully", status=200)

    def _upsert_plant(self, updated_data: dict) -> None:
        plant_update_result = plants_collection.update_one(
            {"plantId": self.plant_id},
            {"$set": updated_data},
            upsert=True,
        )
        if plant_update_result.upserted_id:
            print(f"Inserted new plant with ID {self.plant_id}.")
        else:
            print(f"Updated existing plant with ID {self.plant_id}.")

        
class User(BaseModelWithTimestamp):
    user_id: int
    user_name: str
    telegram_id: str
    device_inventory: list=[]

    def save_to_db(self):
        print()
        try:
            self._upsert_user()

        except Exception as e:
            print(f"Error saving user {self.user_id} to database: {str(e)}")
            return response_creator(False, message=f"Failed to register the user: {str(e)}", status=500)

        return response_creator(True, message="User registered successfully", status=200)

    def _upsert_user(self):
        user_data = self.model_dump_with_time()
        user_update_result = users_collection.update_one(
            {'userId': self.user_id},
            {'$set': user_data},
            upsert=True
        )
        if user_update_result.upserted_id:
            print(f"Inserted new user with ID {self.user_id}.")
        else:
            print(f"Updated existing user with ID {self.user_id}.")



if __name__ == "__main__":
    ## test plant
    def p():
        plant_dict = {
        "plantId": 201,
        "plantKind": "Lettuce",
        "plantDate": "2024-07-28",
        "deviceInventory": [],
        "lastUpdated": "2024-03-14 12:41:45"
    }       
        try:
            plant1 = Plant(**plant_dict)
            print(plant1.model_dump(by_alias=False))
            plant1.save_to_db()
        except ValidationError as e:
            print(e.json())

    ### test device
    def d():
        device_dict = {
            "deviceId": 20009,
            "deviceType": "sensor", 
            "deviceName": "tempsen",
            "deviceStatus": "ON",
            "statusOptions": [
                "DISABLE",
                "ON"
            ],
            "deviceLocation": {
                "plantId": 102
            },
            "measureTypes": [
                "temperature"
            ],
            "availableServices": [
                "MQTT"
            ],
            "servicesDetails": [
                {
                    "serviceType": "MQTT",
                    "topic": [
                        "SC4SS/sensor/101/temperature"
                    ]
                }
            ],
            "lastUpdate": "2024-03-14 12:41:45"
        }
        device1 = Device(**device_dict)
        print(device1.model_dump_with_time())
        device1.save_to_db()
    
    def pa():
        params ={
            "device_type": "sensor",
            "deviceLocation": {
                "plantId": 102
            },
            "measureType": "temperature",
            "noDetail":"True"
        }
        # param1 = DeviceParam(**params)
        # print(param1.model_dump())

    def dparam():
        dparams = {
            'device_type': 'sensor'
        }
        # param = DeviceParam(**dparams)
        # print(param.model_dump())
    # plant1 = Plant(**camel_snake_handler_for_dict(plant_dict, from_type="camel"))
    # plant_dict =plant1.model_dump()
    # plant_dict_updated = plant1.model_dump_with_time()
    # child_logger.info(plant_dict)
    # child_logger.info(plant_dict_updated)
    
    # plant1.remove_from_db()
    # p()
    # d()
    # pa()
    # dparam()
