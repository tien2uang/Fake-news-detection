#Setup docker kafka
docker-compose up

#Access to docker kafka CLI
docker exec -it kafka bash


#Setup training topic
kafka-console-consumer --topic training_data --bootstrap-server localhost:9092
kafka-console-producer --topic training_data --bootstrap-server localhost:9092
#Setup inferrence topic
kafka-console-consumer --topic inferrence_data --bootstrap-server localhost:9092
kafka-console-producer --topic inferrence_data --bootstrap-server localhost:9092

#Setup MLFlow server
mlflow server \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root ./mlruns \
    --host 0.0.0.0 \
    --port 5000

#Run continuous training service


#Run Flask server
python3 backend-service.py

{"label": "true", "statement": "The earth revolves around the sun.", "subject": "science", "speaker": "astronomer", "speaker_job_title": "researcher", "state_info": "global", "party_affiliation": "none", "barely_true_counts": "1", "false_counts": "0", "half_true_counts": "2", "mostly_true_counts": "3", "pants_on_fire_counts": "0", "context": "scientific knowledge"}