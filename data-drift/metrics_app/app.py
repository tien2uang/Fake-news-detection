#!/usr/bin/env python3

"""
This is a demo service for Evidently metrics integration with Prometheus and Grafana.

Read `README.md` for proper setup and installation.

The service gets a reference dataset from reference.csv file and process current data with HTTP API.

Metrics calculation results are available with `GET /metrics` HTTP method in Prometheus compatible format.
"""
import dataclasses
import datetime
from prometheus_client import REGISTRY
import logging
import os
from typing import Dict
from typing import List
from typing import Optional

import flask
import pandas as pd
import prometheus_client
import yaml
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from evidently.report import Report
from evidently.core import IncludeOptions
from evidently.metric_preset import DataDriftPreset
from evidently.pipeline.column_mapping import ColumnMapping
from evidently.runner.loader import DataLoader
from evidently.runner.loader import DataOptions

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler()]
)

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": prometheus_client.make_wsgi_app()})

CONFIG = None
PROD_SCANNER = prometheus_client.Gauge("evidentlyai:scan_count","Production record's scanned number")

@dataclasses.dataclass
class MonitoringServiceOptions:
    datasets_path: str
    min_reference_size: int
    use_reference: bool
    moving_reference: bool
    window_size: int
    calculation_period_sec: int


@dataclasses.dataclass
class LoadedDataset:
    name: str
    references: pd.DataFrame
    monitors: List[str]
    column_mapping: ColumnMapping


class MonitoringService:
    # names of monitoring datasets
    datasets: List[str]
    metric: prometheus_client.Gauge
    stats: prometheus_client.Gauge
    last_run: Optional[datetime.datetime]
    # collection of reference data
    reference: Dict[str, pd.DataFrame]
    # collection of current data
    current: Dict[str, Optional[pd.DataFrame]]
    calculation_period_sec: float = 15
    window_size: int

    def __init__(self, datasets: Dict[str, LoadedDataset], window_size: int):
        self.reference = {}
        self.current = {}
        self.column_mapping = {}
        self.window_size = window_size
        metric_key = f"evidently:data_drift"
        metric_key2 = f"evidently:column_drift"
        
        for dataset_info in datasets.values():
            self.reference[dataset_info.name] = dataset_info.references
            self.column_mapping[dataset_info.name] = dataset_info.column_mapping
        found = prometheus_client.Gauge(metric_key, "", ["key"])
        stats = prometheus_client.Gauge(metric_key2, "", ["key"])
        self.metric = found
        self.stats = stats
        # self.next_run_time = prometheus_client.Gauge("evidentlyai:next_record","Get all")
        # self.next_run_time.set(0)

    def iterate(self, dataset_name: str, new_rows: pd.DataFrame):
        """Add data to current dataset for specified dataset"""
        window_size = self.window_size

        current_data = new_rows

        current_size = current_data.shape[0]

        logging.info(current_data.head())
        self.current[dataset_name] = current_data
        try:
            if current_size < window_size:
                logging.info(f"Not enough data for measurement: {current_size} of {window_size}." f" Waiting more data")
                return
            data_report = Report([
                DataDriftPreset(drift_share=0.6)
            ],)
            data_report.run(reference_data=self.reference[dataset_name], current_data=current_data)
            result = data_report.as_dict()
            
            for feature, value in result["metrics"][0]["result"].items():
                self.metric.labels(key = feature).set(float(value))
            
            for feature, value in result["metrics"][1]["result"]["drift_by_columns"].items():
                self.stats.labels(key = feature).set(float(value['drift_score']))
            PROD_SCANNER.inc(current_size)
        except ValueError as error:
            # ignore errors sending other metrics
            logging.error("Value error for error: ", error)

SERVICE: Optional[MonitoringService] = None


def configure_service():
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)
    # pylint: disable=global-statement
    global SERVICE, CONFIG, PROD_SCANNER
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    # try to find a config file, it should be generated via the data preparation script
    if not os.path.exists(config_file_path):
        logging.error("File %s does not exist", config_file_path)
        exit("Cannot find a config file for the metrics service. Try to check README.md for setup instructions.")

    with open(config_file_path, "rb") as config_file:
        config = yaml.safe_load(config_file)
    CONFIG = config
    options = MonitoringServiceOptions(**config["service"])
    datasets_path = os.path.abspath(options.datasets_path)
    # datasets_path = os.path.abspath('../'+options.datasets_path)
    loader = DataLoader()
    datasets = {}
    
    for dataset_name in os.listdir(datasets_path):
        logging.info(f"Load reference data for dataset %s", dataset_name)
        reference_path = os.path.join(datasets_path, dataset_name, "reference.csv")

        if dataset_name in config["datasets"]:
            dataset_config = config["datasets"][dataset_name]
            reference_data = loader.load(
                reference_path,
                DataOptions(
                    date_column=dataset_config.get("date_column", None),
                    separator=dataset_config["data_format"]["separator"],
                    header=dataset_config["data_format"]["header"],
                ),
            )
            datasets[dataset_name] = LoadedDataset(
                name=dataset_name,
                references=reference_data,
                monitors=dataset_config["monitors"],
                column_mapping=ColumnMapping(**dataset_config["column_mapping"]),
            )
            logging.info("Reference is loaded for dataset %s: %s rows", dataset_name, len(reference_data))

        else:
            logging.info("Dataset %s is not configured in the config file", dataset_name)
    PROD_SCANNER.set(0)

    # Unregister all existing metrics before defining new ones
    
    SERVICE = MonitoringService(datasets=datasets, window_size=options.window_size)

with app.app_context():
    configure_service()

@app.route("/iterate-500/", methods=["GET"])
def iterate():
    n_row = 500
    global SERVICE, CONFIG, PROD_SCANNER
    if SERVICE is None:
        return "Internal Server Error: service not found", 500
    options = MonitoringServiceOptions(**CONFIG["service"])
    datasets_path = os.path.abspath(options.datasets_path)
    # datasets_path = os.path.abspath('../'+options.datasets_path)

    for dataset_name in os.listdir(datasets_path):
        current_path = os.path.join(datasets_path, dataset_name, "production.csv")
    current_scanning_number = int(PROD_SCANNER._value.get())

    current_data = pd.read_csv(current_path, skiprows=range(1, current_scanning_number), nrows=n_row)
    if current_data.shape[0] == 0:
        PROD_SCANNER.clear()
        return "All Data was scanned. please check it later!"
    SERVICE.iterate(dataset_name="fake_new_detection", new_rows=current_data)
    return "done"

if __name__ == "__main__":
    app.run(debug=True)
