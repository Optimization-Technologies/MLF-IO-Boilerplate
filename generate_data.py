import random
from datetime import datetime
import json
from dateutil.relativedelta import relativedelta

import data_models as dm


def generate_upload_data_payload(nbr_datasets: int = 1) -> dm.UploadDataPayload:
    print("Generating dummy data...")
    datasets = []
    for i in range(nbr_datasets):
        dataset_id = f"dummy-dataset-{i + 1}"
        nbr_txns = int(random.uniform(24, 36))
        min_quantity = random.uniform(50.0, 300.0)
        max_quantity = random.uniform(min_quantity, min_quantity * 3.0)
        unit_cost = random.uniform(50.0, 150.0)
        unit_price = random.uniform(unit_cost * 1.5, unit_cost * 4.0)
        date = datetime.now()
        transactions = []
        for i in range(nbr_txns):
            formatted_date = date.strftime("%Y-%m-%d")
            quantity = random.uniform(min_quantity, max_quantity)
            txn = dm.Transaction(
                quantity=quantity,
                departureDate=formatted_date,
                transactionId=f"txn{i}",
                unitCost=unit_cost,
                unitPrice=unit_price,
            )
            transactions.append(txn)
            date -= relativedelta(months=1)
        dataset = dm.Dataset(datasetId=dataset_id, transactions=transactions)
        datasets.append(dataset)
    return dm.UploadDataPayload(datasets=datasets)


def load_data_from_json(file_path) -> dm.UploadDataPayload:
    print("Loading data from JSON file...")
    datasets = []

    with open(file_path, "r") as file:
        json_data = json.load(file)
        dataset_data = json_data["datasets"]  # Extract the datasets array

        for data in dataset_data:
            dataset_id = data["datasetId"]
            transactions_data = data["transactions"]
            transactions = []

            for txn_data in transactions_data:
                txn = dm.Transaction(
                    quantity=txn_data["quantity"],
                    departureDate=txn_data["departureDate"],
                    transactionId=txn_data["transactionId"],
                    unitCost=txn_data["unitCost"],
                    unitPrice=txn_data["unitPrice"],
                )
                transactions.append(txn)

            dataset = dm.Dataset(datasetId=dataset_id, transactions=transactions)
            datasets.append(dataset)

    return dm.UploadDataPayload(datasets=datasets)


def generate_start_trainer_payload(dataset_ids) -> dm.StartTrainerPayload:
    return dm.StartTrainerPayload(
        **{
            "parametersArray": [
                dm.StartTrainerParameterObject(
                    **{
                        "datasetId": dataset_id,
                        "frequency": "M",
                        "horizon": 4,
                    }
                )
                for dataset_id in dataset_ids
            ]
        }
    )


def generate_create_prediction_payload(
    dataset_ids: list[str],
) -> dm.CreatePredictionPayload:
    return dm.CreatePredictionPayload(
        **{
            "parametersArray": [
                dm.CreatePredictionParameterObject(
                    **{
                        "datasetId": dataset_id,
                        "currentInventoryLevel": 50.0,
                        "wantedServiceLevel": 0.95,
                        "replenishmentInterval": dm.ReplenishmentInterval(
                            **{
                                "value": 1,
                                "granularity": "M",
                            }
                        ),
                        "supplier": dm.Supplier(
                            **{
                                "supplierId": "supplier-1",
                                "leadTime": dm.LeadTime(
                                    **{
                                        "value": 2,
                                        "granularity": "W",
                                    }
                                ),
                            }
                        ),
                    }
                )
                for dataset_id in dataset_ids
            ],
        }
    )


def generate_start_inventory_classification_payload(
    dataset_ids: list[str],
) -> dm.StartInventoryClassificationPayload:
    return dm.StartInventoryClassificationPayload(
        **{
            "datasetIds": dataset_ids,
            "abcDriver": "revenue",
        }
    )
