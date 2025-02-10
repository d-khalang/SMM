import requests
import json
import time
from MyMQTT import MyMQTT
from config import Config



class Adaptor():
    def __init__(self, config: Config):
        self.config = config
        self.catalog_address = self.config.CATALOG_URL
        self.broker = ""
        self.port = None
        self.rooms = []
        self.main_topic = ""
        self.channels_detail = {}
        self.user_API_key = self.config.USER_API_KEY
        self.available_measure_types = self.config.AVAILABLE_MEASURE_TYPES
        print("Initiating the adaptor...")

        self.set_broker()
        self.set_main_topic()
        self.initiate_mqtt()
        self.subscribe_to_topic()
        self.check_and_create_channel()
        print()



    def check_and_create_channel(self):
        """
        Creates or retrieves ThingSpeak channels for each plant.
        Each channel corresponds to one plant and contains multiple fields for different sensor types.
        """
        self.update_devices_by_plant()
        # Step 1: Send request to retrieve list of channels
        url = self.config.THINGSPEAK_URL + self.config.THINGSPEAK_CHANNELS_ENDPOINT + self.config.USER_API_KEY
        # url = self.config.CHANNELS_API.replace("{API_key}", self.user_API_key)
        response = requests.get(url)
        channels = response.json()

        for plant_id, device_list in self.devices_by_plant.items():
            channel_name = str(plant_id)

            # Create a mapping between ThingSpeak field numbers and sensor types
            # Example: field1 -> soil_moisture, field2 -> humidity, etc.
            field_names_dict = {}
            fieldNum = 1
            for device in device_list:
                for measure_type in device["measureTypes"]:
                    if measure_type in self.available_measure_types:
                        field_names_dict[f"field{fieldNum}"] = measure_type
                        fieldNum += 1
                    

            # Adding the information of channels' fields to the channel detail dict
            self.channels_detail[channel_name] = {"fields" : field_names_dict}

            # Step 2: Check if the channel exists
            channel_exists = any(channel['name'] == channel_name for channel in channels)

            if channel_exists:
                print(f"Channel '{channel_name}' already exists.")
                channel_id, write_api_key = next((channel['id'], channel["api_keys"][0]["api_key"]) for channel in channels if channel['name'] == channel_name)
                self.channels_detail[channel_name]["writeApiKey"] = write_api_key
                self.channels_detail[channel_name]["channelId"] = channel_id

            else:
                # Step 3: Create the channel
                create_channel_url = self.config.THINGSPEAK_URL + self.config.THINGSPEAK_CHANNELS_ENDPOINT.rstrip("?")
                create_channel_payload = {"api_key": self.user_API_key.split("=")[1], "name": channel_name, "public_flag":"true"}

                # Creating the fields of the channel
                for fieldID, fieldName in field_names_dict.items():
                    create_channel_payload[fieldID] = fieldName

                # ADD TRY AND except
                try:
                    create_channel_response = requests.post(create_channel_url, params=create_channel_payload)
                    created_channel = create_channel_response.json()
                    channel_id, write_api_key = created_channel['id'], created_channel["api_keys"][0]["api_key"]
                    print(f"Channel '{channel_name}' created with ID {channel_id}")
                    self.channels_detail[channel_name]["writeApiKey"] = write_api_key
                    self.channels_detail[channel_name]["channelId"] = channel_id
                except requests.exceptions.RequestException as e:
                    print(f"Failed to create channel {channel_name}: {e}")


    # To get the channels and fields information for user interface
    def get_channel_detail(self, plant_id: str=None):
        return self.channels_detail.get(plant_id, self.channels_detail)



    def set_broker(self, retries=3, delay=5):
        for attempt in range(retries):
            try:
                req_b = requests.get(self.config.CATALOG_URL + "/broker")
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
        req = requests.get(self.config.CATALOG_URL + "/main_topic")
        self.main_topic = req.json().get("content", {})


    def initiate_mqtt(self):
        self.mqtt_client = MyMQTT(clientID = self.config.MQTT_CLIENT_ID,
                                broker=self.broker,
                                port=self.port,
                                notifier=self)
        self.mqtt_client.start()
        time.sleep(0.5)


    def _get_devices(self, plant_id: int):
        try: 
            url = f"{self.catalog_address}/{self.config.DEVICES_ENDPOINT}"
            response = requests.get(url)
            response.raise_for_status()
            devices_response = response.json()
            
            if devices_response.get("success"):
                devices_list = devices_response["content"]
                # Filter devices by plant_id
                filtered_devices = [
                    device for device in devices_list 
                    if device.get("deviceLocation", {}).get("plantId") == plant_id
                ]
                return filtered_devices
            return []
            
        except requests.RequestException as e:
            print(f"Failed to fetch devices list: {e}")


    def update_devices_by_plant(self):
        """Creates a dictionary mapping plant IDs to their associated devices"""
        self.devices_by_plant = {}
        
        # Get all plant IDs
        plant_ids = self.get_plants()
        if not plant_ids:
            print("No plants found")
            return
        
        # For each plant, get its devices
        for plant_id in plant_ids:
            devices = self._get_devices(plant_id)
            if devices:
                self.devices_by_plant[plant_id] = devices
            else:
                print(f"No devices found for plant {plant_id}")
        
        if not self.devices_by_plant:
            print("No devices found for any plant")
            return
            
        print(f"Found devices for plants: {list(self.devices_by_plant.keys())}")


    def get_plants(self):
        try:
            url = f"{self.catalog_address}/{self.config.PLANTS_ENDPOINT}"
            print(f"Fetching plants information from {url}.")
            response = requests.get(url)
            response.raise_for_status()
            plants_response = response.json()

            if plants_response.get("success"):
                plants_list = plants_response["content"]
                # Extract just the plant IDs
                plant_ids = [plant["plantId"] for plant in plants_list]
                return plant_ids
            return []
            
        except requests.RequestException as e:
            print(f"Failed to fetch plants information: {e}")


    def stop_mqtt(self):
        self.mqtt_client.stop()


    def subscribe_to_topic(self):
        self.mqtt_client.mySubscribe(topic=f"{self.main_topic}/sensors/#")


    def notify(self, topic, payload):
        """
        MQTT callback that processes incoming sensor data and forwards it to ThingSpeak.
        The topic format should be: main_topic/sensors/plant_id/measure_type
        Example: greenhouse/sensors/1/temperature
        """
        msg = json.loads(payload)
        event = msg["e"][0]
        print(f"{topic} measured a {event['n']} of {event['v']} {event['u']} at time {event['t']}")

        # Parse the MQTT topic to extract plant ID and measurement type
        try:
            seperatedTopic = topic.strip().split("/")
            if len(seperatedTopic) < 4:
                print("Unrecognized topic: ", topic)
                return
            
            plant_id, measure_type = seperatedTopic[2], seperatedTopic[3]
        except Exception as e:
            print(f"Topic {topic} not operable.")
            return

        # Find the corresponding ThingSpeak channel and field for this sensor reading
        field_available = False
        for channel_name, channel_detail in self.channels_detail.items():
            if channel_name == plant_id:
                channel_API = channel_detail["writeApiKey"]
                for field, sensor_name in channel_detail["fields"].items():  
                    target_field_name = measure_type
                    if sensor_name == target_field_name:
                        channedlField = field
                        field_available = True
                        break
            if field_available:
                break
                
        # Post the sensor reading to ThingSpeak if a matching field was found
        if field_available:
            try:
                # print(f"{self.config.THINGSPEAK_URL}\n{self.config.THINGSPEAK_UPDATE_ENDPOINT}\n&{channedlField}={str(event['v'])}")
                body = {channedlField: str(event['v'])}
                url = self.config.THINGSPEAK_URL+self.config.THINGSPEAK_UPDATE_ENDPOINT+f"api_key={channel_API}"
                response = requests.post(url, json=body)     
                print(f"{measure_type} on channel {channel_name} and {field} is writen on thinkspeak with code {response.text}\n")
            
            except (requests.exceptions.RequestException, UnboundLocalError) as e:
                print(f"Error during writing {sensor_name} on thinkspeak channel: {e}")


if __name__ == "__main__":
    adaptor = Adaptor(Config)
    # adaptor.get_sensing_data('1', 20, '101')
    while True:
        time.sleep(1)
