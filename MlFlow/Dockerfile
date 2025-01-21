# Use the official Python base image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    MLFLOW_TRACKING_URI=http://0.0.0.0:5000 \
    MLFLOW_BACKEND_STORE_URI=sqlite:///mlflow.db \
    MLFLOW_ARTIFACT_ROOT=./mlruns

# Install required dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install MLflow
RUN pip install --no-cache-dir mlflow==2.0.1

# Create a working directory
WORKDIR /app

# Expose port 5000 for the MLflow server
EXPOSE 5000

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
