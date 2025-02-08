from dataclasses import dataclass
from typing import List
import pandas as pd
from confluent_kafka.admin import AdminClient
from flask import Flask, request, jsonify
from confluent_kafka import Producer, Consumer, KafkaError
import os
from dotenv import load_dotenv
import threading
import uuid
from flask_cors import CORS
import json
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from cassandra.cluster import Cluster
from logger import Logger

load_dotenv()

# Initial setup for Flask app and Kafka
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Thay bằng secret key của bạn
CORS(app)
jwt = JWTManager(app)
logger = Logger(False)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
INFERENCE_TOPIC = os.getenv("INFERENCE_TOPIC")
CASSANDRA_HOST = os.getenv('CASSANDRA_HOST', '127.0.0.1')
# Create a Kafka consumer, producer

# Ensure "http://" is not accidentally included
KAFKA_BOOTSTRAP_SERVERS = KAFKA_BOOTSTRAP_SERVERS.replace("http://", "").replace("https://", "")
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'training_group',
    'auto.offset.reset': 'earliest'
})
admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
#Fetch broker information
cluster_metadata = admin_client.list_topics(timeout=5)

if cluster_metadata.brokers:
    print(f"✅ Connected to Kafka broker at {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"🔹 Available brokers: {cluster_metadata.brokers}")
    # List available topics
    topics = cluster_metadata.topics
    print("📌 Kafka Topics:")
    for topic in topics:
        print(f"  - {topic}")
else:
    print(f"❌ Failed to connect to Kafka broker at {KAFKA_BOOTSTRAP_SERVERS}")
# Kết nối Cassandra
cluster = Cluster([CASSANDRA_HOST])  # Địa chỉ IP của cụm Cassandra
session = cluster.connect()
session.set_keyspace('fake_news_system')  # Tạo keyspace tương ứng

# Luu ket qua cua request suy luan mo hinh
# 1 request sẽ có 2 trạng thái: Not Ready, hoặc Completed
results_store = {}


@app.route('/health', methods=['GET'])
def health_check():

    # You can add any health check logic here (e.g., database connectivity check)
    return jsonify(status='healthy'), 200




@app.route('/api/inference', methods=['POST'])
@jwt_required()
def inference():
    try:

        current_user = get_jwt_identity()
        if current_user['role'] not in ["admin", "user"]:
            return jsonify({"error": "User access only"}), 403

        current_user_name = current_user['username']
        request_id = str(uuid.uuid4())

        # Prepare the message
        message = {
            'id': request_id,
            'inference_input': request.json  # Assumes input data is provided as JSON
        }
        logger.append("-------------------REQUEST /api/inference POST------------------")
        logger.append("Payload: "+ json.dumps(request.json))
        # Lưu thông tin vào Cassandra
        query = "INSERT INTO inference_requests (request_id, request_data, status, result,username) VALUES (%s,%s, %s, %s,%s)"
        session.execute(query, [request_id, json.dumps(request.json), 0, None, current_user_name])
        results_store[request_id] = {
            'status': 'Not Ready',
            'result': None
        }
        logger.append("-------------------RESPONSE /api/inference POST ------------------")
        logger.append(json.dumps({"id": request_id}))

        # Send the message to Kafka
        producer.produce(INFERENCE_TOPIC, value=json.dumps(message))
        producer.flush()

        return jsonify({"id": request_id}), 202
    except Exception as e:
    # Xử lý các ngoại lệ khác
        print(f"An unexpected error occurred: {e}")
        logger.append("/api/inference POST "+e)


@app.route ("/api/requests/list",methods=['GET'])
@jwt_required()
def list_requests():
    try:

        current_user = get_jwt_identity()
        if current_user == None:
            return jsonify({"error": "User access only"}), 403
        logger.append("-------------------REQUEST /api/requests/list GET------------------")
        username = current_user['username']
        query = "SELECT request_data,status,result, request_id FROM inference_requests WHERE username=%s  ALLOW FILTERING"
        raw_list_requests = session.execute(query, [username]).all()
        output_list_requests = []
        for raw_request in raw_list_requests:
            request_json_data = json.loads(raw_request[0])
            statement = request_json_data['statement']
            speaker = request_json_data['speaker']

            if raw_request[1] == 1:
                status = "Completed"
            elif raw_request[1] == 0:
                status = "Not Ready"
            result = raw_request[2]
            request_id = raw_request[3]
            output_list_requests.append(
                {"statement": statement, "speaker": speaker, "result": result, "id": request_id})
        logger.append("-------------------RESPONSE /api/requests/list GET------------------")
        logger.append(json.dumps(output_list_requests))
        return jsonify(output_list_requests), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.append("/api/requests/list GET "+e)
@app.route('/api/result/<request_id>', methods=['GET'])
@jwt_required()
def get_result(request_id):
    try:

        current_user = get_jwt_identity()
        if current_user == None:
            return jsonify({"error": "User access only"}), 403
        logger.append("-------------------REQUEST /api/requests/list GET------------------")
        logger.append("Parameter: "+request_id)
        query = "SELECT result, request_id FROM inference_requests WHERE request_id=%s  ALLOW FILTERING"
        result = session.execute(query, [request_id]).one()
        if result[0] is None:
            return jsonify({"status": "Not ready"}), 200
        return jsonify({"status": "Completed", "result": result[0]}), 200

    except Exception as e:

        print(f"An unexpected error occurred: {e}")
        logger.append("/api/result/<request_id> GET "+e)
@app.route("/api/telemetry", methods=['POST'])
@jwt_required()
def create_telemetry_data():
    try:
        current_user = get_jwt_identity()
        if current_user == None:
            return jsonify({"error": "User access only"}), 403
        current_user_name = current_user['username']
        telemetry_content = request.json['telemetry_content']
        # Lưu thông tin vào Cassandra
        logger.append("-------------------REQUEST /api/telemetry POST------------------")
        logger.append("Payload: "+ json.dumps(request.json))
        query = "INSERT INTO telemetry_data (user, event_time, content) VALUES (%s,toTimestamp(now()), %s)"
        session.execute(query, [current_user_name, telemetry_content])

        return jsonify({"message": "Add telemetry successfully"}), 200
    except Exception as e:

        print(f"An unexpected error occurred: {e}")
        logger.append("/api/telemetry POST "+e)

def load_latest_model():
    # Load the latest model from the experiment
    from mlflow.pyfunc import load_model

    model_name = "Fake_News_Detection"
    model_uri = f"models:/{model_name}/latest"  # Use the latest registered version
    predictor = load_model(model_uri)
    return predictor


@dataclass
class ExecuteData:
    label: str
    statement: str
    subject: str
    speaker: str
    speaker_job_title: str
    state_info: str
    # party_affiliation: str
    # barely_true_counts: str
    # false_counts: str
    # half_true_counts: str
    # mostly_true_counts: str
    # pants_on_fire_counts: str
    context: str

def convert_to_object_data(obj: dict) -> ExecuteData:
    """
    Convert a dictionary to a TrainingData object.

    Args:
        obj (dict): Dictionary containing the keys matching TrainingData fields.

    Returns:
        ExecuteData: An instance of TrainingData.
    """
    try:
        return ExecuteData(
            label="",
            statement=obj['statement'],
            subject=obj['subject'],
            speaker=obj['speaker'],
            speaker_job_title=obj['speaker_job_title'],
            state_info=obj['state_info'],
            # party_affiliation=obj['party_affiliation'],
            # barely_true_counts=obj['barely_true_counts'],
            # false_counts=obj['false_counts'],
            # half_true_counts=obj['half_true_counts'],
            # mostly_true_counts=obj['mostly_true_counts'],
            # pants_on_fire_counts=obj['pants_on_fire_counts'],
            context=obj['context']
        )
    except KeyError as e:
        raise ValueError(f"Missing key in the input data: {e}")



def create_dataframe_from_object_data(data_list: List[ExecuteData]) -> pd.DataFrame:
    data_dicts = [data.__dict__ for data in data_list]
    return pd.DataFrame(data_dicts)

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
            print("ID: ",request_id,"Result: ",result)
            query = ("UPDATE inference_requests "
                     "SET status = %s, result = %s WHERE request_id = %s")
            session.execute(query, [1, result, request_id])
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

    # Drop the "label" column if it exists
    test_data = test_df.drop(columns=["label"], errors="ignore")
    # Dự đoán
    y_pred = model.predict(test_data)
    return y_pred[0]




if __name__ == '__main__':
    # Start the Kafka consumer in a separate thread
    consumer_thread = threading.Thread(target=process_inference_requests, daemon=True)
    consumer_thread.start()
    app.run(host='0.0.0.0', port=5002,debug=True)




