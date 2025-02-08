FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn vào container
COPY . .

# Đặt biến môi trường cho địa chỉ IP của Cassandra
ENV CASSANDRA_HOST="127.0.0.1"

# Expose cổng ứng dụng Flask
EXPOSE 5001

# Chạy ứng dụng
CMD ["python", "authorization.py"]
