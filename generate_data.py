import os
import random
from datetime import datetime

from dateutil.relativedelta import relativedelta

from data_models import *


def generate_upload_data() -> UploadDataPayload:
    print("Generating dummy data...")
    dataset_id = "dummy-dataset"
    nbr_txns = 30
    min_quantity = 150.0
    max_quantity = 250.0
    date = datetime.now()
    transactions = []
    for i in range(nbr_txns):
        formatted_date = date.strftime("%Y-%m-%d")
        quantity = random.uniform(min_quantity, max_quantity)
        txn = Transaction(
            quantity=quantity,
            requestedDeliveryDate=formatted_date,  # TODO: Remove
            salesDate=formatted_date,  # TODO: Remove
            departureDate=formatted_date,
            transactionId=f"txn{i}",
            unitCost=104.25,
            unitPrice=608.75,
        )
        transactions.append(txn)
        date -= relativedelta(months=1)
    dataset = Dataset(datasetId=dataset_id, transactions=transactions)
    return UploadDataPayload(datasets=[dataset])


def generate_start_trainer_payload() -> StartTrainerPayload:
    return StartTrainerPayload(
        **{
            "parametersArray": [
                {
                    "datasetId": "dummy-dataset",
                    "frequency": "M",
                    "horizon": 4,
                }
            ]
        }
    )


def generate_headers(
    include_token: bool = True,
    include_content_type: bool = False,
    tenant_id: str = "",
    job_id: str = "",
) -> dict:
    headers = {}
    if include_token:
        headers["Authorization"] = f'Bearer {os.getenv("ACCESS_TOKEN")}'
    if include_content_type:
        headers["Content-Type"] = "application/json"
    if tenant_id:
        headers["tenantId"] = tenant_id
    if job_id:
        headers["jobId"] = job_id
    return headers
