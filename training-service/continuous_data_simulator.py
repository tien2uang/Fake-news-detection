import os
import json
import time
from confluent_kafka import Producer
import kagglehub
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
# Environment variables for Kafka setup
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
DATA_TOPIC = os.getenv("DATA_TOPIC")

# Create a Kafka producer
producer = Producer({'bootstrap.servers': '172.20.208.234:9092'})

# Download the dataset using Kaggle Hub
path = kagglehub.dataset_download("doanquanvietnamca/liar-dataset")


df = pd.read_csv(
    path + "/train.tsv",
    sep='\t',
    header=None,
    names=[
        "label", "statement", "subject", "speaker", "speaker_job_title",
        "state_info", "party_affiliation", "barely_true_counts",
        "false_counts", "half_true_counts", "mostly_true_counts",
        "pants_on_fire_counts", "context"
    ]
)
# Get the last half of the rows
half_index = len(df) // 2  # Integer division to get the midpoint
df_last_half = df.iloc[half_index:]  # Select rows from half_index to the end
# Function to deliver messages to Kafka
def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition}]")

# Iterate over each row in the dataset
for index, row in df_last_half.iterrows():
    # Convert row to dictionary, then to JSON
    row_dict = row.to_dict()
    json_data = json.dumps(row_dict)

    # Produce the JSON data to Kafka with the specified topic
    producer.produce(DATA_TOPIC, json_data, callback=delivery_report)

    # Wait for 5 minutes (300 seconds) before sending the next message
    print(f"Sent row {index} to Kafka.")
    time.sleep(300)  # 5 minutes delay

# Flush the producer to ensure all messages are sent
    producer.flush()
