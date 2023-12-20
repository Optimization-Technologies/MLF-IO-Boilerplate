import os
import random
from datetime import datetime

from dateutil.relativedelta import relativedelta

from data_models import *


def generate_upload_data_payload(nbr_datasets: int = 1) -> UploadDataPayload:
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
            txn = Transaction(
                quantity=quantity,
                departureDate=formatted_date,
                transactionId=f"txn{i}",
                unitCost=unit_cost,
                unitPrice=unit_price,
            )
            transactions.append(txn)
            date -= relativedelta(months=1)
        dataset = Dataset(datasetId=dataset_id, transactions=transactions)
        datasets.append(dataset)
    return UploadDataPayload(datasets=datasets)


def generate_start_trainer_payload() -> StartTrainerPayload:
    return StartTrainerPayload(
        **{
            "parametersArray": [
                StartTrainerParameterObject(
                    **{
                        "datasetId": "dummy-dataset",
                        "frequency": "M",
                        "horizon": 4,
                    }
                )
            ]
        }
    )


def generate_create_prediction_payload() -> CreatePredictionPayload:
    return CreatePredictionPayload(
        **{
            "parametersArray": [
                CreatePredictionParameterObject(
                    **{
                        "datasetId": "dummy-dataset",
                        "currentInventoryLevel": 50.0,
                        "wantedServiceLevel": 0.95,
                        "replenishmentInterval": ReplenishmentInterval(
                            **{
                                "value": 1,
                                "granularity": "M",
                            }
                        ),
                        "suppliers": [
                            Supplier(
                                **{
                                    "supplierId": "supplier-1",
                                    "leadTime": LeadTime(
                                        **{
                                            "value": 2,
                                            "granularity": "W",
                                        }
                                    ),
                                }
                            )
                        ],
                    }
                )
            ],
            "supplierInfoArray": [
                SupplierInfo(
                    **{
                        "supplierId": "supplier-1",
                        "supplierName": "Supplier 1",
                        "minimumOrderValue": 1000.0,
                    }
                )
            ],
        }
    )


def generate_start_inventory_classification_payload(
    dataset_ids: List[str],
) -> StartInventoryClassificationPayload:
    return StartInventoryClassificationPayload(
        **{
            "datasetIds": dataset_ids,
            "abcDriver": "revenue",
        }
    )
