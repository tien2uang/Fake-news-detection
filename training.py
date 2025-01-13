import os
import time
import json
import uuid
from kafka import KafkaProducer, KafkaConsumer
from autogluon.text import TextPredictor
import mlflow
from datetime import datetime

# Kafka setup
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
DATA_TOPIC = 'training_data'

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    DATA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id='training_group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

# MLFlow setup
MLFLOW_TRACKING_URI = "http://localhost:5000"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("Fake News Detection")

# Path for saving data and models
data_save_path = "data/training_data.json"
model_save_path = "models/autogluon_model/"

# Training Service
def consume_training_data():
    """Consume data from Kafka topic and save it locally."""
    all_data = []
    for message in consumer:
        data = message.value
        all_data.append(data)
        print(f"Received data: {data}")

        # Save data every hour
        if len(all_data) >= 1:  # Simulating hourly data collection
            with open(data_save_path, 'w') as f:
                json.dump(all_data, f)
            print(f"Saved {len(all_data)} entries to {data_save_path}")
            all_data.clear()

            # Trigger training
            train_model()


def train_model():
    """Train a model using AutoGluon and log it to MLFlow."""
    print("Starting training process...")

    # Load data
    with open(data_save_path, 'r') as f:
        training_data = json.load(f)

    # Convert data to AutoGluon format
    import pandas as pd
    df = pd.DataFrame(training_data)

    if 'text' not in df.columns or 'label' not in df.columns:
        print("Invalid data format. Ensure 'text' and 'label' columns are present.")
        return

    # Train AutoGluon model
    predictor = TextPredictor(label='label')
    predictor.fit(train_data=df)

    # Save the model
    model_dir = os.path.join(model_save_path, datetime.now().strftime("%Y%m%d_%H%M%S"))
    predictor.save(model_dir)
    print(f"Model saved to {model_dir}")

    # Log the model in MLFlow
    mlflow.start_run()
    mlflow.log_param("model_path", model_dir)
    mlflow.log_artifacts(model_dir, artifact_path="model")
    mlflow.end_run()
    print("Model logged to MLFlow.")

if __name__ == "__main__":
    print("Starting Training Service...")
    consume_training_data()
