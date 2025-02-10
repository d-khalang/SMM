from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27018/")

# Specify the database
db_name = 'catalog'
db = client[db_name]

# Create collections 'plants' and 'general'
plants_collection = db['plants']
general_collection = db['general']
devices_collection = db['devices']

# Primary info to insert into 'general' collection
broker = {
    "broker": {
        "IP": "mqtt.eclipseprojects.io",
        "port": 1883
    }
}

mainTopic = {
    "mainTopic": "SMM"
}

def check_insert(update_result):
    # Check if update was successful
    if update_result.acknowledged:
        print("Update successful.")
        if update_result.upserted_id:
            print(f"Inserted new document with ID: {update_result.upserted_id}")
        else:
            print("Existing document was updated")
    else:
        print("Update failed.")





if __name__ == "__main__":
    # Update or insert documents into 'general' collection
    update_result = general_collection.update_one(
        {"broker": {"$exists": True}},
        {"$set": broker},
        upsert=True
    )
    check_insert(update_result)
    
    update_result = general_collection.update_one(
        {"mainTopic": {"$exists": True}},
        {"$set": mainTopic},
        upsert=True
    )
    check_insert(update_result)
    
    # Confirmation message
    print(f"Database '{db_name}' with collections 'plants' and 'general' has been set up.")