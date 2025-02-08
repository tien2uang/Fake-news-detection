# Use the official Python base image
FROM python:3.11-slim

# Set environment variables
ENV INFERENCE_TOPIC=inferrence_data \
    KAFKA_BOOTSTRAP_SERVERS=http://172.20.208.234:9092 \
    DATA_TOPIC=training_data \
    MLFLOW_ARTIFACT_ROOT=./mlruns

# Install required dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install MLflow
RUN pip install --no-cache-dir mlflow==2.0.1

# Create a working directory
WORKDIR /app
COPY ../training-service/requirements.txt .
RUN pip install -r requirements.txt

COPY . .




# Ensure the script has execution permissions
RUN chmod +x entrypoint.sh

# Expose necessary ports
EXPOSE 5000 5002

# Use the entrypoint script to start both services
CMD ["./entrypoint.sh"]