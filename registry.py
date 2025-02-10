import cherrypy
import datetime
import time
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config import Config
from models import Plant, Device, User
from utility import response_creator

# MongoDB Configuration
client = MongoClient(Config.MONGO_URL)
db = client[Config.DB]
plants_collection = db[Config.PLANTS_COLLECTION]
general_collection = db[Config.GENERAL_COLLECTION]
devices_collection = db[Config.DEVICES_COLLECTION]
users_collection = db[Config.USERS_COLLECTION]



class Catalog():
    """
    A REST service that manages the registration and status of plants, devices, and users.
    Provides CRUD operations via HTTP endpoints and handles automatic cleanup of stale entries.
    """
    exposed = True
    def __init__(self):
        self.plants = []
        self.devices = []
        # Excludes MongoDB id
        self.defult_projection = {"_id":0}

        self.threshold = Config.CLEANUP_THRESHOLD
        self.interval = Config.CLEANUP_INTERVAL

        self.get_broker()
        self.get_main_topic()


    def get_broker(self):
        try:
            result = general_collection.find_one({"broker": {"$exists": True}}, {"_id": 0, "broker": 1})
            if result and "broker" in result:
                self.broker = result["broker"]
                print(f"Broker found: {self.broker}")
            else:
                print("Broker not found in general collection.")
        except Exception as e:
            print(F"An error occurred while retrieving the broker: {e}")


    def get_main_topic(self):
        try:
            result = general_collection.find_one({"mainTopic": {"$exists": True}}, {"_id": 0, "mainTopic": 1})
            if result and "mainTopic" in result:
                self.main_topic = result["mainTopic"]
                print(f"MainTopic found: {self.main_topic}")
            else:
                print("Main topic not found in general collection.")
        except Exception as e:
            print(F"An error occurred while retrieving the Main topic: {e}")


    # Get plants list
    def get_all_plants(self):
        plants = plants_collection.find({}, self.defult_projection)
        return list(plants)

    def get_all_devices(self):
        devices = devices_collection.find({}, self.defult_projection)
        return list(devices)    
    
    def get_all_users(self):
        users = users_collection.find({}, self.defult_projection)
        return list(users)

    def delete_plant(self, plant_id: int):
        plants_collection.delete_one({"plantId": plant_id})

    def delete_device(self, device_id: int):
        devices_collection.delete_one({"deviceId": device_id})

    def delete_user(self, user_id: int):
        users_collection.delete_one({"userId": user_id})

    @cherrypy.tools.json_out()
    def GET(self, *uri, **params):
        """
        Handles GET requests for various resources:
        - /broker: Returns MQTT broker details
        - /devices or /device/{id}: Returns all devices or specific device
        - /plants or /plant/{id}: Returns all plants or specific plant
        - /users or /user/{id}: Returns all users or specific user
        """
        if len(uri) == 0:
            return response_creator(True, message="Enter a valid URL among: broker, devices, device/{id}, plants, plant/{plantId}, users, user/{userId}", status=404)
        else:
            end_point = uri[0].lower()

            if end_point == "broker":
                self.get_broker()
                return response_creator(True, content=self.broker, status=200)

            elif end_point == "devices":
                if len(uri) > 1:
                    try:
                        device_Id = int(uri[1])
                        for device in self.get_all_devices():
                            if str(device.get("deviceId")) == device_Id:
                                return response_creator(True, content=[device], status=200)
                        return response_creator(False, message="device not present", status=404)
                    except:
                        return response_creator(False, message="Enter a valid device id, device/{device id}", status=404)
                else:   
                    return response_creator(True, content=self.get_all_devices(), status=200)

                    

            elif end_point == "plants":
                if len(uri) > 1:
                    try:
                        plant_id = int(uri[1])
                        for plant in self.get_all_plants():
                            if plant.get("plantId") == plant_id:
                                return response_creator(True, content=[plant], status=200)
                        return response_creator(False, message="plant not present", status=404)
                    except:
                        return response_creator(False, message="Enter a valid plant id, plant/{plant id}", status=404)
                else:   
                    return response_creator(True, content=self.get_all_plants(), status=200)

            
            elif end_point == "main_topic":
                self.get_main_topic()
                return response_creator(True, content=self.main_topic, status=200)

            elif end_point == "users":
                if len(uri) > 1:
                    try:
                        user_id = int(uri[1])
                        for user in self.get_all_users():
                            if user.get("userId") == user_id:
                                return response_creator(True, content=[user], status=200)
                        return response_creator(False, message="user not present", status=404)
                    except:
                        return response_creator(False, message="Enter a valid user id, user/{user id}", status=404)
                else:   
                    return response_creator(True, content=self.get_all_users(), status=200)

            else:
                return response_creator(False, message="No valid url. Enter a valid url among: broker, devices, device/{id}, plants, plant/{plantId}, users, user/{userId}", status=404)






    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def POST(self, *uri, **params):
        if len(uri) == 0:
            return response_creator(False, message="Specify what to add: /plants, /devices, /users", status=404)
        else:
            end_point = uri[0].lower()
            data = cherrypy.request.json
            data["lastUpdated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Supposed to get a plant dictionary
            if end_point == "plants":
                if plants_collection.find_one({"plantId": data["plantId"]}):
                    print(f"Plant {data['plantId']} already exists")

                try:
                    plant = Plant(**data)
                    return plant.save_to_db()
                except ValueError as ve:
                    cherrypy.response.status = 400
                    return response_creator(False, message=f"ValueError: {str(ve)}", status=400)
                except PyMongoError as pe:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"DatabaseError: {str(pe)}", status=500)
                except Exception as e:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"UnknownError: {str(e)}", status=500)
                    
            elif end_point == "devices":
                try:
                    device = Device(**data)
                    return device.save_to_db()
                except ValueError as ve:
                    cherrypy.response.status = 400
                    return response_creator(False, message=f"ValueError: {str(ve)}", status=400)

            elif end_point == "users":
                if users_collection.find_one({"userId": data["userId"]}):
                    print(f"User {data['userId']} already exists")

                try:
                    user = User(**data)
                    return user.save_to_db()
                except ValueError as ve:
                    cherrypy.response.status = 400
                    return response_creator(False, message=f"ValueError: {str(ve)}", status=400)
                except PyMongoError as pe:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"DatabaseError: {str(pe)}", status=500)
                except Exception as e:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"UnknownError: {str(e)}", status=500)



    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def PUT(self, *uri, **params):
        """
        Handles PUT requests to update existing resources:
        - /devices/status: Updates device online/offline status
        - /plants: Updates plant information (creates if doesn't exist)
        - /devices: Updates device information (creates if doesn't exist)
        - /users: Updates user information (creates if doesn't exist)
        """
        if len(uri) == 0:
            return response_creator(False, message="Specify what to update: /plants, /devices, /users", status=404)
        else:
            end_point = uri[0].lower()
            data = cherrypy.request.json
            data["lastUpdated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"Data to be updated: {data}")

            # Supposed to get a plant dictionary
            if end_point == "plants":
                db_response = plants_collection.find_one({"plantId": data["plantId"]})
                if not db_response:
                    print(f"Plant {data['plantId']} does not exists, it will be inserted...")

                try:
                    plant = Plant(**data)
                    return plant.save_to_db()
                except ValueError as ve:
                    cherrypy.response.status = 400
                    return response_creator(False, message=f"ValueError: {str(ve)}", status=400)
                except PyMongoError as pe:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"DatabaseError: {str(pe)}", status=500)
                except Exception as e:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"UnknownError: {str(e)}", status=500)


            elif end_point == "devices":
                if len(uri) > 1:
                    if uri[1] == "status":
                        device_id, new_status = data.get("deviceId"), data.get("status")
                        try:
                            # Update device status using upsert
                            result = devices_collection.update_one(
                                {"deviceId": device_id},
                                {"$set": {
                                    "deviceStatus": new_status,
                                    "lastUpdated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }},
                                upsert=True
                            )
                            if result.modified_count > 0 or result.upserted_id:
                                print(f"Device {device_id} status updated to {new_status}")
                                return response_creator(True, message="Device status updated successfully", status=200)
                            print(f"Device {device_id} status not updated")
                            return response_creator(False, message="Failed to update device status", status=500)
                        except PyMongoError as pe:
                            cherrypy.response.status = 500
                            print(f"DatabaseError: {str(pe)}")
                            return response_creator(False, message=f"DatabaseError: {str(pe)}", status=500)
                        except Exception as e:
                            cherrypy.response.status = 500
                            print(f"UnknownError: {str(e)}")
                            return response_creator(False, message=f"UnknownError: {str(e)}", status=500)
                        
                else:
                    # Check if the device already exists
                    db_response = devices_collection.find_one({"deviceId": data["deviceId"]})
                    if db_response:
                        print(f"Device {data['deviceId']} already exists")

                    try:
                        device = Device(**data)
                        return device.save_to_db()
                    except ValueError as ve:
                        cherrypy.response.status = 400
                        return response_creator(False, message=f"ValueError: {str(ve)}", status=400)
                    except PyMongoError as pe:
                        cherrypy.response.status = 500
                        return response_creator(False, message=f"DatabaseError: {str(pe)}", status=500)
                    except Exception as e:
                        cherrypy.response.status = 500
                        return response_creator(False, message=f"UnknownError: {str(e)}", status=500)


            elif end_point == "users":
                db_response = users_collection.find_one({"userId": data["userId"]})
                if not db_response:
                    print(f"User {data['userId']} does not exist, it will be inserted...")

                try:
                    user = User(**data)
                    return user.save_to_db()
                except ValueError as ve:
                    cherrypy.response.status = 400
                    return response_creator(False, message=f"ValueError: {str(ve)}", status=400)
                except PyMongoError as pe:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"DatabaseError: {str(pe)}", status=500)
                except Exception as e:
                    cherrypy.response.status = 500
                    return response_creator(False, message=f"UnknownError: {str(e)}", status=500)

            else:
                return response_creator(False, message="No valid url. Enter a valid url among: broker, devices, device/{id}, plants, plant/{plantId}, users, user/{userId}", status=404)



    def cleanup(self):
        """
        Periodic cleanup task that removes plants and devices that haven't been
        updated within the configured threshold time (indicating they're offline/inactive)
        """
        print("Cleaning up outdated Plants and Devices...")
        self._cleanup_plants()
        self._cleanup_devices()
        print("Clean up completed.")

    
    # Removes outdated plants
    def _cleanup_plants(self):
        a_threshold_ago = datetime.datetime.now() - datetime.timedelta(minutes=self.threshold)
        plants = self.get_all_plants()

        for plant in plants:
            last_updated = datetime.datetime.strptime(plant['lastUpdated'], "%Y-%m-%d %H:%M:%S")
            if last_updated < a_threshold_ago:
                self.delete_plant(plant['plantId'])
                print(f"Plant {plant['plantId']} deleted")


    # Removes outdated devices
    def _cleanup_devices(self):
        a_threshold_ago = datetime.datetime.now() - datetime.timedelta(minutes=self.threshold)
        devices = self.get_all_devices()

        for device in devices:
            last_updated = datetime.datetime.strptime(device['lastUpdated'], "%Y-%m-%d %H:%M:%S")
            if last_updated < a_threshold_ago:
                self.delete_device(device['deviceId'])
                print(f"Device {device['deviceId']} deleted")

if __name__ == "__main__":
    # Configure CherryPy to handle RESTful requests
    conf = {"/": {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True
    }}
    
    # Start the web service and periodic cleanup task
    web_service = Catalog()
    cherrypy.tree.mount(web_service, '/', conf)
    cherrypy.engine.start()

    # Run cleanup check every CLEANUP_INTERVAL seconds
    counter = 0
    try:
        while True:
            if counter % Config.CLEANUP_INTERVAL == 0:
                web_service.cleanup()
            counter += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Shutting down...")
        cherrypy.engine.stop()




