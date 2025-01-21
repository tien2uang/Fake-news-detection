from autogluon.common import TabularDataset
from flask import Flask, request, jsonify
from confluent_kafka import Producer, Consumer, KafkaError
import mlflow.pyfunc
import os
from dotenv import load_dotenv
import threading
import time
import queue
import uuid
import json
from training import convert_to_object_data, create_dataframe_from_object_data

load_dotenv()

# Initial setup for Flask app and Kafka
app = Flask(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
INFERENCE_TOPIC = os.getenv("INFERENCE_TOPIC")
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
# Create a Kafka consumer
consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'training_group',
    'auto.offset.reset': 'earliest'
})

# Luu ket qua cua request suy luan mo hinh
# 1 request sẽ có 2 trạng thái: Not Ready, hoặc Completed
results_store = {}


@app.route('/health', methods=['GET'])
def health_check():
    # You can add any health check logic here (e.g., database connectivity check)
    return jsonify(status='healthy'), 200
@app.route('/api/inference', methods=['POST'])
def inference():
    # Create a unique ID for the inference request
    request_id = str(uuid.uuid4())

    # Prepare the message
    message = {
        'id': request_id,
        'inference_input': request.json  # Assumes input data is provided as JSON
    }

    # Send the message to Kafka
    producer.produce(INFERENCE_TOPIC, value=json.dumps(message).encode('utf-8'))
    producer.flush()

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
    from mlflow.pyfunc import load_model

    model_name = "FakeNewsDetection"
    model_uri = f"models:/{model_name}/latest"  # Use the latest registered version
    predictor = load_model(model_uri)
    return predictor




def process_inference_requests():
    print("Starting inference requests!!!!!!!!!!!!")
    consumer.subscribe([INFERENCE_TOPIC])
    while True:
        msg = consumer.poll(1.0)  # Poll every 1 second
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Consumer error: {msg.error()}")
                break
        try:

            data = json.loads(msg.value().decode('utf-8'))
            print(f"Received data: {data}")
            request_id = data['id']
            # Trích xuat noi dung can check
            input_data = data['inference_input']

            result = predict_with_latest_model(input_data)
            print(result)
            results_store[request_id] = {
                'status': 'Completed',
                'result': result
            }
        except json.JSONDecodeError:
            print(msg.value()," is not valid JSON")
            continue



def predict_with_latest_model(input_json):
    # Load the latest model
    model = load_latest_model()
    inference_data = convert_to_object_data(input_json)
    test_df = create_dataframe_from_object_data([inference_data])
    # Tạo TabularDataset từ test_df
    test_data = TabularDataset(test_df)

    test_data_nolab = test_data.drop(columns=["label"], errors="ignore")  # Bỏ cột label để predictor dự đoán

    # Dự đoán
    y_pred = model.predict(test_data_nolab)

    print(y_pred)
    return y_pred[0]




if __name__ == '__main__':
    # Start the Kafka consumer in a separate thread
    consumer_thread = threading.Thread(target=process_inference_requests, daemon=True)
    consumer_thread.start()
    app.run(host='0.0.0.0', port=5001)


