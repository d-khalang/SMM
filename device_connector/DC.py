from soil_sen import SoilSen
from MyMQTT import MyMQTT
import requests
import time
import json
from typing import Literal
from config import Config




class DC():
    def __init__(self):
        # Initialize Device Connector that manages communication between sensors, 
        # actuators and the MQTT broker
        print("Initializing Device Connector...")
        with open(Config.CONFIG_FILE) as f:
            file_data = json.load(f)
        self.plants_list = file_data.get("plants")
        self.devices_list = file_data.get("devices")
        self.catalog_url = Config.CATALOG_URL
        print(f"Loaded configuration from {Config.CONFIG_FILE}")
        print(f"Catalog URL: {self.catalog_url}")

        # Get broker connection details and main topic from catalog service
        self.set_broker()
        self.set_main_topic()

        # Set up MQTT topics for sensors and actuators
        self.sen_topic = self.main_topic + "/sensors/"
        self.act_topic = self.main_topic + "/actuators/"
        self.client = MyMQTT(Config.MQTT_CLIENT_ID, self.broker, self.port, self)
        self.client.start()
        time.sleep(0.3)  # Brief delay to ensure MQTT connection is established
        # Subscribe to all actuator messages using wildcard (#)
        self.client.mySubscribe(self.act_topic + "#")

        # Initialize soil sensor and prepare SenML message template
        self.soil_sen = SoilSen()
        self.msg = {
            "bn": f"{self.main_topic}/sensors/",  # Base name for the sensor
            "e": [
                {
                    "n": self.soil_sen.get_info()[0],  # Sensor name
                    "u": self.soil_sen.get_info()[1],  # Unit of measurement
                    "t": None,  # Timestamp (filled during data collection)
                    "v": None   # Value (filled during data collection)
                }
            ]
        }



    # Registering the plant and its devices
    def registerer(self, type: Literal['plant', 'devices'], ntry: int):
        print(f"\nAttempting to register {type} (attempt {ntry})")
        # Determine which list and endpoint to use based on type
        items = self.plants_list if type == "plant" else self.devices_list
        endpoint = f"/{Config.PLANTS_ENDPOINT}" if type == "plant" else f"/{Config.DEVICES_ENDPOINT}"
        
        # Choose request method based on ntry
        method = requests.put if ntry > 1 else requests.post
        
        # Make request for each item
        for item in items:
            try:
                print(f"Registering {type}: {item}")
                req = method(self.catalog_url + endpoint, json=item)
                print(f"Registration successful for {type}")

            except requests.exceptions.RequestException as e:
                print(f"Registration failed for {type}: {e}")



    def set_broker(self, retries=3, delay=5):
        for attempt in range(retries):
            try:
                req_b = requests.get(self.catalog_url + "/broker")
                req_b.raise_for_status()  # Raise an exception for HTTP errors
                req_data = req_b.json()
                broker_info = req_data.get("content", {})
                self.broker, self.port = broker_info.get("IP"), int(broker_info.get("port", 1883))
                print("Broker's info received")
                return {"success": True}
                # Exit the function if successful

            except (TypeError, ValueError, requests.exceptions.RequestException, json.JSONDecodeError) as e:
                print(
                    f"Failed to get the broker's information. Attempt {attempt + 1} of {retries}. Error: {e}")
                if attempt < retries - 1:  # If not the last attempt, wait before retrying
                    time.sleep(delay)
                else:
                    print("All attempts to get the broker's information have failed.")
                    raise ConnectionError("All attempts to get the broker's information have failed.")


    def set_main_topic(self):
        req = requests.get(self.catalog_url + "/main_topic")
        self.main_topic = req.json().get("content", {})


    def data_collector(self):
        """
        Collects sensor data by taking multiple readings and publishing their average.
        This helps reduce noise and provide more stable measurements.
        """
        print("\nStarting data collection...")

        for device in self.devices_list:
            if device.get("deviceType") == "sensor":
                device_id = device.get("deviceId")
                plant_id = device["deviceLocation"].get("plantId")
                # Take multiple readings and average them for more stable measurements
                sensor_data_points = []
                
                for _ in range(Config.DATA_POINTS_FOR_AVERAGE):
                    sensor_value = self.soil_sen.sense()
                    sensor_data_points.append(sensor_value)
                    time.sleep(Config.DATA_COLLECTION_INTERVAL)
                
                avg_value = sum(sensor_data_points) / len(sensor_data_points)
                print(f"Average value: {avg_value:.2f}")
                
                # Prepare and publish SenML message
                self.msg["e"][0]["t"] = int(time.time())
                self.msg["e"][0]["v"] = avg_value
                # Format topic as: main_topic/sensors/plant_id/soil_moisture
                self.msg["bn"] = f"{self.main_topic}/sensors/{str(plant_id)}/soil_moisture"
                
                try:
                    topic = f"{self.sen_topic}{str(plant_id)}/soil_moisture"
                    self.client.myPublish(topic, self.msg)
                    print(f"Published data to topic: {topic} with payload: {self.msg}")
                except Exception as e:
                    print(f"Error publishing data: {e}")
            
            

    def notify(self, topic, payload):
        """
        Callback function for MQTT messages.
        Processes incoming actuator commands and updates device status in catalog.
        """
        msg = json.loads(payload)
        event = msg["e"][0]
        print(f"{topic} measured a {event['n']} of {event['v']} {event['u']} at time {event['t']}")

        # Parse topic structure: main_topic/device_type/plant_id
        splitted_topic = topic.split("/")
        try:
            main_topic, device_type, plant_id = splitted_topic[0], splitted_topic[1], splitted_topic[2]
        except Exception as e:
            print(f"Unrecognized topic detected: {str(e)}.")
            return

        # Validate command type
        if event['v'] not in ["STOP_WATER", "POUR_WATER"]:
            print("Detected status is unrecognized. No registration on catalog.")
            return
        
        command = event['v']
        print(f"Command received: {command}")
        self.handle_status_change(plant_id, command)

        

    def handle_status_change(self, plant_id, command):
        # Get device with matching plant ID from catalog
        try:
            response = requests.get(f"{self.catalog_url}/{Config.DEVICES_ENDPOINT}")
            if response.json().get("success"):
                devices = response.json().get("content", [])
                matching_device = None
                for device in devices:
                    if (device.get("deviceLocation", {}).get("plantId") == int(plant_id) and 
                        device.get("deviceType") == "actuator"):
                        matching_device = device
                        break
                
                if matching_device:
                    device_id = matching_device.get("deviceId")
                    # Update device status in catalog
                    status_data = {
                        "deviceId": device_id,
                        "status": command
                    }
                    update_response = requests.put(f"{self.catalog_url}/{Config.DEVICES_ENDPOINT}/status", json=status_data)
                    if update_response.json().get("success"):
                        print(f"Successfully updated device {device_id} status to {command}")
                    else:
                        print(f"Failed to update device status: {update_response.json().get('message')}")
                else:
                    print(f"No matching device found for plant ID {plant_id}")
            else:
                print(f"Failed to get devices from catalog: {response.json().get('message')}")
        except Exception as e:
            print(f"Error updating device status: {str(e)}")


if __name__ == "__main__":
    print("\n=== Starting Device Connector ===\n")
    device_connector = DC()
    
    # Perform initial registration of plants and devices
    print("\nInitial registration...")
    device_connector.registerer("plant", ntry=1)
    device_connector.registerer("devices", ntry=1)
    
    # Main loop: Collect data and re-register devices periodically
    print("\nEntering registration and data collection loop...")
    counter = 0
    while True:
        # Collect data when counter aligns with collection interval
        if counter % Config.DATA_COLLECTION_INTERVAL == 0:
            device_connector.data_collector()
            print()
        counter += 1
        # Re-register devices periodically to maintain presence in catalog
        if counter % Config.REGISTRATION_INTERVAL == 0:
            device_connector.registerer("devices", ntry=2)
        
    