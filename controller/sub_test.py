from MyMQTT import MyMQTT
import time

class Sub():
    def __init__(self):
        self.mqtt = MyMQTT("test986784634747479744", "mqtt.eclipseprojects.io", 1883, self)
        self.mqtt.start()
        time.sleep(1)
        self.mqtt.mySubscribe("SMM/#")

    def notify(self, topic, payload):
        print(f"Received message: {payload}")

if __name__ == "__main__":
    suber = Sub()
    for _ in range(100):
        time.sleep(1)
    suber.mqtt.stop()