from autogluon.common import TabularDataset
from flask import Flask, request, jsonify
from confluent_kafka import Producer, Consumer, KafkaError
import mlflow.pyfunc
import os
from dotenv import load_dotenv
import threading
import uuid
from flask_cors import CORS
import json
from training import convert_to_object_data, create_dataframe_from_object_data
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from cassandra.cluster import Cluster
import bcrypt
import pusher
load_dotenv()

# Initial setup for Flask app and Kafka
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Thay bằng secret key của bạn
CORS(app)
# Initialize Pusher
pusher_client = pusher.Pusher(

    ssl=True,
    app_id = "1934100",
    key = "b40cd313ac5885723c8a",
    secret = "a5cc83ea0db07731c87c",
    cluster = "ap1",
)
jwt = JWTManager(app)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
INFERENCE_TOPIC = os.getenv("INFERENCE_TOPIC")

# Create a Kafka consumer, producer
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'training_group',
    'auto.offset.reset': 'earliest'
})

# Kết nối Cassandra
cluster = Cluster(['127.0.0.1'])  # Địa chỉ IP của cụm Cassandra
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
    current_user = get_jwt_identity()
    if current_user['role'] not in ["admin","user"]:
        return jsonify({"error": "User access only"}), 403
    current_user_name = current_user['username']
    # Create a unique ID for the inference request
    request_id = str(uuid.uuid4())

    # Prepare the message
    message = {
        'id': request_id,
        'inference_input': request.json  # Assumes input data is provided as JSON
    }



    # Store initial state as "Not reafdy"


    # Lưu thông tin vào Cassandra
    query = "INSERT INTO inference_requests (request_id, request_data, status, result,username) VALUES (%s,%s, %s, %s,%s)"
    session.execute(query, [request_id, json.dumps(request.json), 0, None,current_user_name])
    results_store[request_id] = {
        'status': 'Not Ready',
        'result': None
    }

    # Send the message to Kafka
    producer.produce(INFERENCE_TOPIC, value=json.dumps(message))
    producer.flush()

    return jsonify({"id": request_id}), 202


@app.route ("/api/requests/list",methods=['GET'])
@jwt_required()
def list_requests():
    current_user = get_jwt_identity()
    if current_user == None:
        return jsonify({"error": "User access only"}), 403
    username = current_user['username']
    query = "SELECT request_data,status,result, request_id FROM inference_requests WHERE username=%s  ALLOW FILTERING"
    raw_list_requests = session.execute(query, [username]).all()
    output_list_requests=[]
    for request in raw_list_requests:
        request_json_data = json.loads(request[0])
        statement = request_json_data['statement']
        speaker = request_json_data['speaker']

        if request[1]==1:
            status = "Completed"
        elif request[1]==0:
            status = "Not Ready"
        result = request[2]
        request_id = request[3]
        output_list_requests.append({"statement": statement, "speaker": speaker, "result": result,"id": request_id})

    return jsonify(output_list_requests),200
@app.route('/api/result/<request_id>', methods=['GET'])
def get_result(request_id):
    result = results_store.get(request_id)
    if not result:
        return jsonify({"error": "Request ID not found"}), 404

    if result['status'] == 'Not Ready':
        return jsonify({"status": "Not Ready"}), 200

    return jsonify({"status": "Completed", "result": result['result']}), 200


@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')  # Mặc định là người dùng

    # Kiểm tra username tồn tại
    query = "SELECT * FROM users WHERE username=%s"
    user = session.execute(query, [username]).one()
    if user:
        return jsonify({"error": "Username already exists"}), 400

    # Mã hóa mật khẩu
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Lưu thông tin vào Cassandra
    query = "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)"
    session.execute(query, [username, hashed_password.decode('utf-8'), role])

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/signin', methods=['POST'])
def signin():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Tìm người dùng trong Cassandra
    query = "SELECT * FROM users WHERE username=%s"
    user = session.execute(query, [username]).one()
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    # Kiểm tra mật khẩu
    if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"error": "Invalid username or password"}), 401

    # Tạo JWT
    access_token = create_access_token(identity={"username": username, "role": user.role})
    return jsonify({"username":user.username,"access_token": access_token}), 200


@app.route('/admin', methods=['GET'])
@jwt_required()
def admin_only():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"error": "Admin access only"}), 403

    return jsonify({"message": "Welcome, Admin!"}), 200

@app.route('/user', methods=['GET'])
@jwt_required()
def user_only():
    current_user = get_jwt_identity()
    return jsonify({"message": f"Welcome, {current_user['username']}!"}), 200


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
            # Push update to Pusher
            pusher_client.trigger("fake-news-channel", "new-detection", {
               "need_refresh":True
            })
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


