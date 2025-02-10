# Instructions to Set Up MongoDB on Docker

## 1. Install Docker
Ensure Docker is installed and running on your system. You can download Docker from the [official website](https://www.docker.com/).

## 2. Pull the MongoDB Image
Open your terminal and run the following command to pull the MongoDB image version `7.0`:

```bash
docker pull mongo:7.0
```

## 3. Create and Run the MongoDB Container
Use the following command to create and run a MongoDB container with the specified configuration:

```bash
docker run -d \
  --name catalog_mongo \
  -p 27018:27017 \
  -v catalog_mongo_data:/data/db \
  mongo:7.0
```

### Explanation:
- `--name catalog_mongo`: Sets the container name as `catalog_mongo`.
- `-p 27018:27017`: Maps the MongoDB container's default port (`27017`) to port `27018` on your host machine.
- `-v catalog_mongo_data:/data/db`: Creates a persistent volume named `catalog_mongo_data` to store MongoDB data.

## 4. Verify the Setup
Run the following command to ensure the container is running:

```bash
docker ps
```

You should see a container named `catalog_mongo` in the list.

## 5. Connect to MongoDB
You can connect to your MongoDB instance on `localhost:27018` using MongoDB tools or libraries, such as:
- [`mongosh`](https://www.mongodb.com/try/download/shell)
- GUI clients like [MongoDB Compass](https://www.mongodb.com/try/download/compass)

---

# How to Run the Project

Follow these steps to set up and run the project:

## 1. Clone or Download the Repository
Clone the repository using Git:

```bash
git clone SMM
```

Or download the repository as a ZIP file and extract it.

## 2. Navigate to the Root of the Repository
Change to the root directory of the repository:

```bash
cd SMM
```

## 3. Run the Setup Scripts in Order and using different terminals in the root directory

### Step 1: Set up MongoDB
Run the MongoDB setup script:

```bash
python mongo_setup.py
```

### Step 2: Run the Registry Service
Start the registry service:

```bash
python registry.py
```

### Step 3: Run the Device Connector
Run the device connector script:

```bash
python device_connector/DC.py
```

### Step 4: Run the Control Unit
Run the control unit script:

```bash
python controller/control_unit.py
```

### Step 5: Run the ThingSpeak Adaptor
Start the ThingSpeak adaptor:

```bash
python thingspeak/adaptor.py
```

### Step 6: Run the Telegram Bot
Finally, start the Telegram bot:

```bash
python telegram_bot/bot.py
```

**Telegram Bot ID:** `@SMM4IoT_bot`

---

After completing these steps, your IoT system should be up and running!
