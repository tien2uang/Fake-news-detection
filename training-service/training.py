import argparse
import json
import os
from datetime import datetime

import kagglehub
import mlflow
import pandas as pd
from autogluon.common import TabularDataset
from autogluon.tabular import TabularPredictor
from confluent_kafka import Consumer, KafkaError,Producer
from dotenv import load_dotenv
from mlflow.pyfunc import PythonModel
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
load_dotenv()
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
DATA_TOPIC = os.getenv("DATA_TOPIC")
# Tên cột nhãn
label_column = "label"
# Create a Kafka consumer, producer
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
# Create a Kafka consumer
consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'training_group',
    'auto.offset.reset': 'earliest'
})

# MLFlow setup
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("Fake News Detection 20250802")

model_save_path = "../serving-service/AutogluonModels"
# Đường dẫn đến folder chứa dataset trên Kaggle:
path = kagglehub.dataset_download("doanquanvietnamca/liar-dataset")
DATA_PATH = path + "/"  # Thay đổi nếu cần


# Define relevant columns
RELEVANT_COLUMNS = [
    "label", "statement", "subject", "speaker", "speaker_job_title",
    "state_info", "context"
]

# Training Service
class AutoGluonModelWrapper(PythonModel):
    def __init__(self, model_dir):
        self.model_dir = model_dir

    def load_context(self, context):
        self.model = TabularPredictor.load(self.model_dir)

    def predict(self, context, model_input):
        return self.model.predict(model_input)


from dataclasses import dataclass
from typing import List


@dataclass
class ExecuteData:
    label: str
    statement: str
    subject: str
    speaker: str
    speaker_job_title: str
    state_info: str
    # party_affiliation: str
    # barely_true_counts: str
    # false_counts: str
    # half_true_counts: str
    # mostly_true_counts: str
    # pants_on_fire_counts: str
    context: str



def create_dataframe_from_object_data(data_list: List[ExecuteData]) -> pd.DataFrame:
    data_dicts = [data.__dict__ for data in data_list]
    return pd.DataFrame(data_dicts)


def convert_to_object_data(obj: dict) -> ExecuteData:
    """
    Convert a dictionary to a TrainingData object.

    Args:
        obj (dict): Dictionary containing the keys matching TrainingData fields.

    Returns:
        ExecuteData: An instance of TrainingData.
    """
    try:
        return ExecuteData(
            label=obj['label'],
            statement=obj['statement'],
            subject=obj['subject'],
            speaker=obj['speaker'],
            speaker_job_title=obj['speaker_job_title'],
            state_info=obj['state_info'],
            # party_affiliation=obj['party_affiliation'],
            # barely_true_counts=obj['barely_true_counts'],
            # false_counts=obj['false_counts'],
            # half_true_counts=obj['half_true_counts'],
            # mostly_true_counts=obj['mostly_true_counts'],
            # pants_on_fire_counts=obj['pants_on_fire_counts'],
            context=obj['context']
        )
    except KeyError as e:
        raise ValueError(f"Missing key in the input data: {e}")


def continous_consume_data_and_training():
    """Consume data from Kafka topic and save it locally."""
    all_data = []
    consumer.subscribe([DATA_TOPIC])
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
            all_data.append(convert_to_object_data(data))
            print(all_data)
            if len(all_data) == 1:
                train_and_log_model(all_data)
                all_data.clear()
        except json.JSONDecodeError:
            print(msg.value(), " is not valid JSON")
            continue

    consumer.close()


def train_and_log_model(training_raw_data: List[ExecuteData]):
    """Train a model using AutoGluon and log it to MLFlow."""
    print("Starting training process...")
    if training_raw_data is not None:
        continuous_train_df = create_dataframe_from_object_data(training_raw_data)
        original_train_df = pd.read_csv(
            DATA_PATH + "train.tsv",
            sep='\t',
            header=None,
            names=[
                "label", "statement", "subject", "speaker", "speaker_job_title",
                "state_info", "party_affiliation", "barely_true_counts",
                "false_counts", "half_true_counts", "mostly_true_counts",
                "pants_on_fire_counts", "context"
            ]
        )[RELEVANT_COLUMNS]
        continuous_train_df = continuous_train_df[RELEVANT_COLUMNS]
        train_raw_data = pd.concat([original_train_df, continuous_train_df], axis=0).reset_index(drop=True)
    else:
        original_train_df = pd.read_csv(
            DATA_PATH + "train.tsv",
            sep='\t',
            header=None,
            names=[
                "label", "statement", "subject", "speaker", "speaker_job_title",
                "state_info", "party_affiliation", "barely_true_counts",
                "false_counts", "half_true_counts", "mostly_true_counts",
                "pants_on_fire_counts", "context"
            ]
        )[RELEVANT_COLUMNS]

        train_raw_data = pd.concat([original_train_df], axis=0).reset_index(drop=True)
    # Chuyển DataFrame sang TabularDataset
    train_data = TabularDataset(train_raw_data)

    model_dir = os.path.join(model_save_path, datetime.now().strftime("%Y%m%d_%H%M%S"))
    # Khởi tạo và huấn luyện
    predictor = TabularPredictor(
        label=label_column,
        eval_metric='accuracy',
        path=model_dir
    ).fit(
        train_data=train_data,
        presets='medium_quality_faster_train',  # Lighter training setup
        time_limit=600,  # Limit training to 10 minutes
        hyperparameters={
            'GBM': {},  # Use Gradient Boosting Machine (lightweight)
        },

    )

    # Load test data
    test_df = pd.read_csv(
        DATA_PATH + "test.tsv",
        sep='\t',
        header=None,
        names=[
            "label", "statement", "subject", "speaker", "speaker_job_title",
            "state_info", "party_affiliation", "barely_true_counts",
            "false_counts", "half_true_counts", "mostly_true_counts",
            "pants_on_fire_counts", "context"
        ]
    )[RELEVANT_COLUMNS]
    test_data = TabularDataset(test_df)

    # Ground truth labels
    y_true = test_data[label_column]

    # Predict on test set
    y_pred = predictor.predict(test_data)

    # Calculate evaluation metrics
    accuracy = accuracy_score(y_true, y_pred)
    # precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    # recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    # f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)

    predictor.save(model_dir)
    print(f"Model saved to {model_dir}")
    if accuracy >0:

        # Log model to MLFlow
        with mlflow.start_run() as run:
            # Wrap and log as a PyFunc model
            mlflow.pyfunc.log_model(
                artifact_path="model",
                python_model=AutoGluonModelWrapper(model_dir),
                artifacts={"model_dir": model_dir},
            )
            mlflow.log_metric("accuracy", accuracy)
            # mlflow.log_metric("precision", precision)
            # mlflow.log_metric("recall", recall)
            # mlflow.log_metric("f1_score", f1)
            print(f"Model logged to MLFlow with run ID: {run.info.run_id}")

            # Register model in the MLFlow Model Registry
            model_uri = f"runs:/{run.info.run_id}/model"
            model_name = "Fake_News_Detection"
            mlflow.register_model(model_uri=model_uri, name=model_name)
            print(f"Model registered in MLFlow with name: {model_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train or consume training data.")
    parser.add_argument("--retrain", type=bool, default=True, help="Set to False for online consume_train mode.")
    args = parser.parse_args()

    print("Starting Training Service...")
    if args.retrain:
        train_and_log_model(None)
    continous_consume_data_and_training()
