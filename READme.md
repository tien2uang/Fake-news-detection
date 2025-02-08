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

![Kiến trúc hệ thống](https://github.com/user-attachments/assets/978151ac-367f-4055-b65d-d7971e586f8d)

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

# Deploy lên AKS

## 1. Giới Thiệu Các Công Cụ

Hệ thống được triển khai sử dụng các công cụ sau:

- **Terraform**: Dùng để provision hạ tầng trên Azure, tạo Resource Group, AKS Cluster và các tài nguyên liên quan.
- **Azure CLI**: Quản lý tài nguyên trên Azure và cấu hình kết nối đến AKS.
- **Docker**: Xây dựng image container cho các service.
- **Kubernetes (AKS)**: Nền tảng orchestrator cho container, nơi triển khai các service.
- **kubectl**: Quản lý và deploy các file YAML lên cluster.
- **Evidently**: Công cụ phát hiện data drift (giám sát sự thay đổi dữ liệu theo thời gian) được tích hợp trong hệ thống.
- **Grafana & Prometheus**: Dùng để giám sát và trực quan hóa các metric, bao gồm các metric của Evidently.

## 2. Provision Hạ Tầng Với Terraform

Trong thư mục Terraform của dự án, có các file cấu hình hạ tầng. Để provision hạ tầng, chạy các lệnh sau:

```bash
terraform init
terraform plan
terraform apply
```

Sau khi Terraform hoàn tất, cấu hình AKS sẽ được tạo ra và lấy thông tin kết nối bằng lệnh:

```bash
az aks get-credentials --resource-group <resource-group-name> --name <aks-cluster-name>
```

## 3. Deploy Lên AKS

Trong repository dự án, bạn có sẵn các file deployment YAML sau:

- **auth-service.yaml**: Chứa cấu hình Deploy, Service, Configmap cho Auth Service.
- **k8s-data-drift.yaml**: Chứa các Deployments, Service, ConfigMap cho Evidently, Grafana và Prometheus.
- **k8s-manifest.yaml**: Chứa các Deployments, Service, ConfigMap cho NGINX, Cassandra, Zookeeper, Kafka.
- **model-service.yaml**: Chứa cấu hình Deploy và Service cho Model Service (Serving Service).

Để deploy, cần kết nối đến cụm AKS và chạy các lệnh sau ở local:

1. **Deploy Auth Service:**

   ```bash
   kubectl apply -f auth-service.yaml
   ```

2. **Deploy Evidently & Các Dịch Vụ Giám Sát (Grafana, Prometheus) cùng với các thành phần hạ tầng (NGINX, Cassandra, Zookeeper, Kafka):**

   ```bash
   kubectl apply -f k8s-manifest.yaml
   kubectl apply -f k8s-data-drift.yaml
   ```

3. **Deploy Model Service (Serving Service):**

   ```bash
   kubectl apply -f model-service.yaml
   ```

*Lưu ý:* Nếu một số service đã được deploy rồi, các lệnh `kubectl apply` sẽ cập nhật hoặc bỏ qua thay đổi tương ứng.

## 5. Kiểm Tra

Sau khi deploy, hãy kiểm tra trạng thái các tài nguyên:

- **Kiểm tra Namespace và Pod:**

  ```bash
  kubectl get ns
  kubectl get pods --all-namespaces
  ```

- **Kiểm tra các Service:**

  ```bash
  kubectl get svc --all-namespaces
  ```

- **Kiểm tra Endpoints của Kafka (ví dụ):**

  ```bash
  kubectl get endpoints kafka -n <namespace>
  ```

- **Xem Log của các Pod (Auth Service, Model Service, Kafka, Evidently, …):**

  ```bash
  kubectl logs -n <namespace> <pod-name>
  ```

- **Port-forward để test API nội bộ (ví dụ Model Service):**

  ```bash
  kubectl port-forward svc/model-service 5002:5002
  ```
  
  Sau đó, truy cập API inference tại:
  
  ```
  http://localhost:5002/api/inference
  ```

## 6. Các Khó Khăn Gặp Phải

- **Cấu Hình Kafka:**  
  Ban đầu gặp khó khăn với việc cấu hình Kafka (SASL, advertised listeners). Sau nhiều vòng điều chỉnh, nhóm chuyển sang sử dụng PLAINTEXT và cấu hình advertised listener với FQDN đầy đủ (ví dụ: `kafka.kafka-conf.svc.cluster.local:9092`) để đảm bảo các client kết nối thành công.

- **Triển Khai Nhiều Namespace:**  
  Ban đầu gặp phải các vấn đề liên quan đến việc truy xuất các secret và kết nối giữa các namespace. Cuối cùng, nhóm cấu hình đúng FQDN và đảm bảo rằng các service được triển khai trong namespace phù hợp.

- **Terraform & AKS:**  
  Quá trình provision hạ tầng với Terraform đòi hỏi cấu hình chính xác và sau khi chạy `terraform apply`, việc lấy thông tin kết nối AKS qua Azure CLI là bước quan trọng.

- **Cấu Hình Evidently:**  
  Việc tích hợp Evidently để phát hiện data drift cần đảm bảo rằng các metric được publish đúng và Grafana có thể lấy dữ liệu từ Prometheus. Một số khó khăn ban đầu liên quan đến cấu hình datasource và dashboard đã được khắc phục sau nhiều vòng thử nghiệm.

- **Các Công Cụ Hỗ Trợ:**  
  Sử dụng Docker, kubectl, Azure CLI và Git để quản lý quy trình deploy, cùng với Terraform để provision hạ tầng đã giúp tối ưu quy trình triển khai.

---

*README này cung cấp tổng quan về quá trình triển khai và hướng dẫn sử dụng các lệnh cần thiết để chạy hệ thống trên AKS.*
