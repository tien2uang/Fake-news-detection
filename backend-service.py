from flask import Flask, request, jsonify
from kafka import KafkaProducer, KafkaConsumer
import mlflow.pyfunc
import threading
import time
import queue
import uuid
import json

# Initial setup for Flask app and Kafka
app = Flask(__name__)
producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=lambda v: json.dumps(v).encode('utf-8'))
consumer = KafkaConsumer('model_inference', bootstrap_servers=['localhost:9092'], group_id='model_group',
                         value_deserializer=lambda m: json.loads(m.decode('utf-8')))

# Luu ket qua cua request suy luan mo hinh
# 1 request sẽ có 2 trạng thái: Not Ready, hoặc Completed
results_store = {}

@app.route('/api/inference', methods=['POST'])
def inference():
    # Create a unique ID for the inference request
    request_id = str(uuid.uuid4())

    # Prepare the message
    message = {
        'id': request_id,
        'data': request.json  # Assumes input data is provided as JSON
    }

    # Send the message to Kafka
    producer.send('model_inference', message)

    # Store initial state as "Not ready"
    results_store[request_id] = {
        'status': 'Not Ready',
        'result': None
    }

    return jsonify({"id": request_id}), 202


@app.route('/api/result/<request_id>', methods=['GET'])
def get_result(request_id):
    result = results_store.get(request_id)
    if not result:
        return jsonify({"error": "Request ID not found"}), 404

    if result['status'] == 'Not Ready':
        return jsonify({"status": "Not Ready"}), 200

    return jsonify({"status": "Completed", "result": result['result']}), 200



def load_latest_model():
    # Load the latest model from the experiment
    experiment_name = "Fake News Detection"
    mlflow.set_tracking_uri("http://localhost:5000")  # MLFlow server URL
    experiment = mlflow.get_experiment_by_name(experiment_name)

    if not experiment:
        raise ValueError(f"Experiment {experiment_name} not found.")

    # Get the latest run for the experiment
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=1,
    )

    if not runs:
        raise ValueError("No runs found for the experiment.")

    # Get the run ID of the latest run
    latest_run_id = runs[0].info.run_id

    # Load the model from MLFlow
    model_uri = f"runs:/{latest_run_id}/model"
    model = mlflow.pyfunc.load_model(model_uri)
    print(f"Loaded model from {model_uri}")
    return model




def process_inference_requests():
    while True:
        raw_messages = consumer.poll(timeout_ms=1000)  # Poll messages with a timeout
        if not raw_messages:  # No messages received
            print("No messages in topic, waiting...")
            continue

        for topic_partition, messages in raw_messages.items():
            for message in messages:
                message_value = message.value

                request_id = message_value['id']
                # Trích xuat noi dung can check
                input_data = message_value['data']

                # Simulate model processing
                time.sleep(5)
                result = predict_with_latest_model(input_data)

                results_store[request_id] = {
                    'status': 'Completed',
                    'result': result
                }


def predict_with_latest_model(input_text):
    # Load the latest model
    model = load_latest_model()

    # Prepare input as a Pandas DataFrame
    import pandas as pd
    input_df = pd.DataFrame({"text": [input_text]})

    # Perform prediction
    prediction = model.predict(input_df)
    return prediction


# Start the Kafka consumer in a separate thread
consumer_thread = threading.Thread(target=process_inference_requests, daemon=True)
consumer_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# NGINX Configuration Example
# Save this configuration as /etc/nginx/conf.d/ml_service.conf
#
# upstream model_service {
#     server 127.0.0.1:5000;
#     server 127.0.0.1:5001;
#     server 127.0.0.1:5002;
# }
#
# server {
#     listen 80;
#
#     location /api/ {
#         proxy_pass http://model_service;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#     }
# }
