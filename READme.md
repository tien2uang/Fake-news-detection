# 📰 Giới thiệu Hệ thống Fake News Detection
Hệ thống **Fake News Detection** được phát triển để xác định các phát biểu giả mạo, sử dụng dữ liệu từ **LIAR Dataset**.

Mã nguồn hệ thống được chia thành hai phần:
- **Backend**: Được phát triển trên repository này.
- **Frontend**: Được phát triển tại [đây](https://github.com/tien2uang/Fake-news-detection--FE).

---

## 🏗️ Thiết kế Hệ thống
Hệ thống sử dụng kiến trúc **Microservice**, gồm 3 service chính:

1. **Training Service**: Phụ trách huấn luyện và quản lý phiên bản của mô hình.
2. **Model Serving Service**: Phụ trách suy luận và phục vụ mô hình.
3. **Auth Service**: Quản lý xác thực và phân quyền người dùng.

Hệ thống sử dụng:
- **NGINX** đóng vai trò **API Gateway**.
- **Cassandra** làm cơ sở dữ liệu lưu trữ dữ liệu.

![Kiến trúc hệ thống](https://github.com/user-attachments/assets/870761eb-03af-4702-b5f8-b935b137fbd9)

---

## 🛠️ Cài đặt Môi trường
### **Yêu cầu hệ thống**
- **Docker**
- **Ubuntu**

### **Cài đặt các thành phần**
1. Cài đặt các dependencies:
   ```sh
   pip install -r requirements.txt
   ```
   (Thực hiện cài đặt trong từng thư mục của từng service.)

2. Cấu hình **Cassandra** với schema từ file:
   ```sh
   serving-service/db_init.cql
   ```

3. Cấu hình **Kafka** với hai topic:
   - `inferrence_data`
   - `training_data`

4. Thiết lập địa chỉ deploy của các service trong file:
   ```sh
   nginx.conf
   ```

5. Cấu hình địa chỉ các service trong các file **.env** hoặc **config** hoặc **docker-compose** phù hợp với môi trường deploy.

---

## 🚀 Chạy Hệ thống


Chạy file **docker-compose** để khởi tạo Kafka, Cassandra, NGINX

Chạy từng service với các lệnh sau:

- **Auth Service**:
  ```sh
  python ./auth-service/authorization.py
  ```
- **Model Serving Service**:
  ```sh
  sh ./serving-service/entrypoint.sh
  ```
- **Training Service**:
  ```sh
  python ./training-service/training.py
  ```

---

📌 *Hãy đảm bảo tất cả các service, Kafka, Cassandra và NGINX được thiết lập đúng trước khi chạy hệ thống.*

