#!/bin/bash

# Initialize SQLite database if it doesn't exist
if [ ! -f ./mlflow.db ]; then
    echo "Creating SQLite database..."
    sqlite3 ./mlflow.db ".databases"
fi

# Start the MLflow server
mlflow server \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root ./mlruns \
    --host 0.0.0.0 \
    --port 5000
