import random
from config import SensorConfig

class SoilSen():
    def __init__(self):
        self.MIN = int(SensorConfig.MIN_SOIL_MOISTURE)
        self.MAX = int(SensorConfig.MAX_SOIL_MOISTURE)
        self.unit = "percentage"
        self.senKind = "soilMoisture"
        self.last_value = random.randint(self.MIN, self.MAX)  # Initialize with a first value

    def sense(self):
        # Gradually change the soil moisture value based on the last value
        delta = random.randint(-3, 3)  # Small change in moisture percentage
        new_value = self.last_value + delta
        
        # Ensure the new value stays within the valid range
        new_value = max(self.MIN, min(self.MAX, new_value))
        
        # Update the last value
        self.last_value = new_value
        
        return new_value

    def get_info(self):
        return (self.senKind, self.unit)