import bcrypt
from flask import Flask, request, jsonify
import jwt
import datetime
from flask_cors import CORS
from cassandra.cluster import Cluster
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Thay bằng secret key của bạn
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)
CORS(app)
jwt = JWTManager(app)



# Kết nối Cassandra
cluster = Cluster(['127.0.0.1'])  # Địa chỉ IP của cụm Cassandra
session = cluster.connect()
session.set_keyspace('fake_news_system')  # Tạo keyspace tương ứng


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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # Chạy ở cổng riêng cho service này
