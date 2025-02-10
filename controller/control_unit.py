import json
import requests
import time
from typing import List
from config import Config
from MyMQTT import MyMQTT

class Controller:
    """
    Controller class that manages the automated watering system.
    It monitors soil moisture sensors and sends commands to water pump actuators
    when moisture levels are outside the desired range.
    """
    def __init__(self, config: Config):
        self.config = config
        self.mqtt_client = None
        
        # SenML message template for sending commands to actuators
        # bn: base name (topic)
        # e: array of events containing:
        #   n: name of the measurement/command
        #   u: unit (in this case, command type)
        #   t: timestamp
        #   v: value/command to send
        self.msg = {
            "bn": "",
            "e": [
                {
                    "n": 'controller',
                    "u": 'command',
                    "t": None,
                    "v": None
                }
            ]
        }
        
        print("Initiating the controller...")
        self.set_broker()
        self.set_main_topic()
        self.initiate_mqtt()


    def initiate_mqtt(self):
        """Initialize MQTT client and connect to broker"""
        self.mqtt_client = MyMQTT(
            clientID=self.config.MQTT_CLIENT_ID,
            broker=self.broker,
            port=self.port,
            notifier=self
        )
        self.mqtt_client.start()
        time.sleep(0.5)
        self.mqtt_client.mySubscribe(f"{self.main_topic}/sensors/#")


    def set_broker(self, retries=3, delay=5):
        """
        Retrieve broker connection details from the catalog service.
        Implements retry logic in case of connection failures.
        
        Args:
            retries: Number of connection attempts
            delay: Time to wait between retries in seconds
        """
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

    

    def notify(self, topic, payload):
        """
        MQTT callback function that processes incoming sensor messages.
        Parses SenML formatted messages and routes soil moisture readings
        to the appropriate handler.
        
        Args:
            topic: MQTT topic the message was received on
            payload: Message content in SenML format
        """
        try:
            msg = json.loads(payload)
            # Part of the message related to the event happened
            event = msg["e"][0]
        except Exception as e:
            self.logger.warning(f"Unrecognized payload received over mqtt: {str(e)}.")
            return
        
        print(f"{topic} measured a {event['n']} of {event['v']} {event['u']} at time {event['t']}")
        if event["n"] in ["soil_moisture", "soilMoisture"]:
            self.handle_moisture_reading(topic, event["v"])


    def handle_moisture_reading(self, sensor_topic, moisture_value):
        """
        Process soil moisture readings and determine if watering is needed.
        Looks up the corresponding actuator for the sensor's plant and
        sends watering commands based on moisture thresholds.
        
        Args:
            sensor_topic: Topic the reading came from, contains plant ID
            moisture_value: Current soil moisture level
        """
        print()
        try:
            # Extract plant ID from topic (format: "greenhouse/sensors/101/soil_moisture")
            plant_id = sensor_topic.split("/")[2]
            
            # Find the actuator (water pump) associated with this plant
            response = requests.get(f"{self.config.CATALOG_URL}/devices")
            devices = response.json().get("content", [])
            actuator = next(
                (device for device in devices if 
                 device["deviceLocation"]["plantId"] == int(plant_id) 
                 and 
                 device["deviceType"] == "actuator"), 
                {}
                )
            
            if not actuator:
                print(f"Actuator for plant {plant_id} not found")
                return

            if actuator["deviceStatus"] == "DISABLE":
                print(f"Actuator for plant {plant_id} is disabled")
                return
            
            # Check moisture level against thresholds and send appropriate command
            if moisture_value < self.config.SOIL_MOSTURE_MIN:
                self.send_water_command(actuator, command="POUR_WATER")
            elif moisture_value > self.config.SOIL_MOSTURE_SUITABLE:
                self.send_water_command(actuator, command="STOP_WATER")
            else:
                print(f"Soil moisture is optimal for plant{plant_id}")

        except requests.RequestException as e:
            print(f"Error handling moisture reading: {e}")


    def send_water_command(self, actuator, command):
        """
        Send watering commands to an actuator via MQTT.
        Checks current actuator state to avoid sending redundant commands.
        
        Args:
            actuator: Dictionary containing actuator details
            command: Either "POUR_WATER" or "STOP_WATER"
        """
        print(f"Actuator: {actuator}")
        if actuator.get("deviceStatus") == command:
            print(f"Actuator for plant {actuator.get('deviceLocation', {}).get('plantId', '')} is already in the desired state")
            return
        
        try:
            # Get MQTT topic from actuator services or use default format
            topic = next(
                (service_detail.get("topics", [""])[0] for service_detail in actuator["servicesDetails"] if service_detail.get("serviceType") == "MQTT"), 
                f"{self.main_topic}/actuators/{actuator.get('deviceLocation', {}).get('plantId', '')}/water_pump"
            )
            
            # Prepare and send SenML formatted command
            msg = self.msg.copy()
            msg["bn"] = topic
            msg["e"][0]["t"] = str(time.time())
            msg["e"][0]["v"] = command
            
            self.mqtt_client.myPublish(topic, msg)
            print(f'Sent watering command {msg["e"][0]["v"]} to {topic}')
            
        except Exception as e:
            print(f"Error sending water command: {e}")

    def stop(self):
        """Stop the MQTT client"""
        if self.mqtt_client:
            self.mqtt_client.stop()



if __name__ == "__main__":
    config = Config()
    controller = Controller(config)
    while True:
        time.sleep(1)   
    controller.stop()
