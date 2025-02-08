#!/bin/bash

# Start MLflow server with nohup
nohup mlflow server --backend-store-uri sqlite:///mlflow.db \
                    --default-artifact-root ./mlruns \
                    --host 0.0.0.0 --port 5000 > mlflow.log 2>&1 &

# Start Flask server
python3 model_serving.py
