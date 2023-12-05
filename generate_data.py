import random
from datetime import datetime
from typing import List

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel


class Transaction(BaseModel):
    quantity: float
    requestedDeliveryDate: str
    salesDate: str
    departureDate: str
    transactionId: str
    unitCost: float
    unitPrice: float


class Dataset(BaseModel):
    datasetId: str
    transactions: List[Transaction]


class Body(BaseModel):
    datasets: List[Dataset]


def generate_data():
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
    body = Body(datasets=[dataset])
    return body.model_dump()
