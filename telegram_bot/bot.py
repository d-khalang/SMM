import requests, time, json, os
import re
import telepot
from datetime import date, datetime
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config


class DataManager():
    """Handles data operations and API interactions for plant information and sensing data"""
    def __init__(self):
        self.config = Config
        self.channels_detail = {}


    def get_plant(self, plant_id=None):
        """
        Fetches plant information from the catalog API
        Args:
            plant_id (str, optional): Specific plant ID to fetch. If None, fetches all plants
        Returns:
            list: List of plant dictionaries containing plant details
        """
        url = f"{self.config.CATALOG_URL}/{self.config.PLANTS_ENDPOINT}"
        if plant_id:
            url += f"/{plant_id}"
        output = []
        try:    
            print(f"Fetching plant information from: {url}")
            response = requests.get(url)
            plants_response = response.json()

            if plants_response.get("success"):
                plants_list = plants_response["content"]
                if plants_list:
                    output = plants_list
                    print(f"Successfully retrieved plant data for ID: {plant_id}")
            else:
                print(f"Failed to get plant data. Response: {plants_response}")
        
        except requests.RequestException as e:
            print(f"Failed to fetch plant's information: {e}")
            
        return output


    def get_sensing_data(self, plant_id: str):
        """
        Retrieves sensor data from ThingSpeak API for a specific plant
        Args:
            plant_id (str): ID of the plant to fetch sensor data for
        Returns:
            dict: Formatted sensor readings with timestamps, empty dict if failed
        """
        url = self.config.THINGSPEAK_URL + self.config.THINGSPEAK_CHANNELS_ENDPOINT + self.config.USER_API_KEY
        response = requests.get(url)
        channels = response.json()
        # """ channels example: 
        # [{"id":2828493,"name":"101","description":null,"latitude":"0.0","longitude":"0.0","created_at":"2025-02-03T20:47:58Z","elevation":null,
        # "last_entry_id":6,"public_flag":true,"url":null,"ranking":30,"metadata":null,"license_id":0,"github_url":null,"tags":[],
        # "api_keys":[{"api_key":"TXQ7HQ155T4WBXY5","write_flag":true},{"api_key":"PNIQ1GYBHY8WZ09Y","write_flag":false}]}]"""
        channel_id = next((channel.get("id") for channel in channels if channel.get("name") == str(plant_id)), None)
        if channel_id is None:
                print(f"No channel found with name: {plant_id}")
                return {}

        # requests thingSpeak for the last data points
        try:
            # https://api.thingspeak.com/channels/<2425367>/feeds.json?results=4
            url = f"{self.config.THINGSPEAK_URL}/channels/{str(channel_id)}/feeds.json"
            params = {'results': 5}
            req_g = requests.get(url, params=params)
            print(f"Get request of sensing data for plant {plant_id} with params {params}")
            
            data = req_g.json()
            if not data or 'channel' not in data or 'feeds' not in data:
                return {}
            
            # Create a formatted output dictionary
            output = {}
            
            # Get field names from channel data
            fields = {k: v for k, v in data['channel'].items() if k.startswith('field')}
            
            # Process each feed entry
            for field_key, field_name in fields.items():
                readings = []
                for feed in data['feeds']:
                    if feed.get(field_key):
                        timestamp = datetime.strptime(feed['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        readings.append(f"📊 {feed[field_key]} (🕒 {formatted_time})")
                
                if readings:
                    output[field_name] = "\n".join(readings)
            
            return output
        
        except requests.exceptions.RequestException as e:
            print(f"Failed to get sensing data from ThingSpeak. Error: {e}")
            return {}
        except KeyError as e:
            print(f"Key error: {e}")
            return {}





class TeleBot():
    """
    Telegram bot implementation for plant monitoring system
    Handles user interactions and displays plant/sensor information
    """
    def __init__(self, token):
        """
        Initialize bot with token and set up message handlers
        Args:
            token (str): Telegram bot API token
        """
        self.token = token
        self.botManager = DataManager()
        self.bot = telepot.Bot(self.token)

        callback_dict = {'chat': self.on_chat_message,
                         'callback_query': self.on_callback_query}
        MessageLoop(self.bot, callback_dict).run_as_thread()
        print("Bot is up!")


    # Triggered when recieving text messages
    def on_chat_message(self, msg):
        """
        Handles incoming chat messages and commands
        Supported commands:
        - /start: Welcome message
        - /plant_information: Request plant details
        - 3-digit number: Show specific plant info
        - /sensing_data: Request sensor data
        - data_<plant_id>: Show sensor data for specific plant
        """
        content_type, chat_type, chat_id = telepot.glance(msg)
        cmd = msg['text']
        print(f"Received message from chat_id {chat_id}: {cmd}")

        if cmd == "/start":
            self.bot.sendMessage(chat_id, "Wellcome to Intelligent Planting bot")
            print(f"New user started bot: {chat_id}")


        elif cmd == "/plant_information":
            self.bot.sendMessage(chat_id, "Enter your plant's ID: ")

        # Uses regular expression to fillter the 3 digit numbers intered
        elif re.fullmatch(r"\d{3}", cmd):
            plant = self.botManager.get_plant(cmd)
            if not plant:
                self.bot.sendMessage(chat_id, "Could not find plant with that ID")
            else:
                self.show_plant_info_msg(chat_id, plant[0])
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Get Sensing Data', callback_data=f'data_{plant[0]["plantId"]}')]
                ])
                self.bot.sendMessage(chat_id, "Would you like to see sensing data?", reply_markup=keyboard)

        elif cmd == "/sensing_data":
            self.bot.sendMessage(chat_id, "Enter your plant's ID to get sensing data with format: data_plantId, exp: data_101")

        elif cmd.startswith('data_'):
            plant_id = cmd.split('_')[1]
            self.show_sensing_data(chat_id, plant_id)

        else:
            self.bot.sendMessage(chat_id, "Sorry your message is invalid 😣")



    def on_callback_query(self, msg):
        """
        Handles callback queries from inline keyboard buttons
        Currently supports:
        - data_<plant_id>: Show sensor data for specific plant
        """
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        
        if query_data.startswith('data_'):
            plant_id = query_data.split('_')[1]
            self.show_sensing_data(from_id, plant_id)


    
    def show_plant_info_msg(self, telegram_id, plant_dict: dict):
        """
        Formats and sends plant information messages to user
        Displays: Plant ID, Connected Devices, Last Update, Plant Date
        Also calculates and shows days until harvest
        """
        plant_id = plant_dict.get("plantId")
        device_inventory = plant_dict.get("deviceInventory")
        last_update = plant_dict.get("lastUpdated")
        plant_date = plant_dict.get("plantDate")
        
        self.bot.sendMessage(telegram_id, f"🌱 Plant ID: {plant_id}")
        self.bot.sendMessage(telegram_id, f"📱 Connected Devices: {device_inventory}")
        self.bot.sendMessage(telegram_id, f"🕒 Last Updated: {last_update}")
        self.bot.sendMessage(telegram_id, f"📅 Planting Date: {plant_date}")
        FULL_GROWING_TIME = Config.FULL_GROWING_TIME
        
        # Calculate days until harvest
        plant_date_obj = datetime.strptime(plant_date, "%Y-%m-%d")
        days_since_planting = (datetime.now() - plant_date_obj).days
        days_until_harvest = FULL_GROWING_TIME - days_since_planting
        
        if days_until_harvest > 0:
            self.bot.sendMessage(telegram_id, f"🌾 Your plant will be ready for harvest in {days_until_harvest} days")
        else:
            self.bot.sendMessage(telegram_id, "🌾 Your plant is ready for harvest!")


    def show_sensing_data(self, telegram_id, plant_id):
        """
        Fetches and displays sensing data for a specific plant
        Formats the data in a readable message with timestamps
        """
        print(f"Fetching sensing data for plant {plant_id} requested by user {telegram_id}")
        sensing_data = self.botManager.get_sensing_data(plant_id)
        if sensing_data:
            message = "📊 Latest Sensing Data:\n"
            for sensor, value in sensing_data.items():
                message += f"\n{sensor}: \n{value}"
            self.bot.sendMessage(telegram_id, message)
            print(f"Successfully sent sensing data for plant {plant_id}")
        else:
            self.bot.sendMessage(telegram_id, "❌ Could not retrieve sensing data")
            print(f"Failed to retrieve sensing data for plant {plant_id}")



if __name__ == "__main__":
    bot = TeleBot(Config.BOT_TOKEN)

    while 1:
        time.sleep(10)

