from typing import List, Optional
from pydantic import BaseModel


### DATA ###############################################################################
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


class UploadDataPayload(BaseModel):
    datasets: List[Dataset]


class PresignedUrlResponseSuccess(BaseModel):
    url: str
    jobId: str
    message: str


class PresignedUrlResponseFailure(BaseModel):
    error: str
    message: str


### TRAINING ###########################################################################
class ParameterObject(BaseModel):
    datasetId: str
    frequency: str
    horizon: int


class StartTrainerPayload(BaseModel):
    parametersArray: List[ParameterObject]


### STATUS #############################################################################
class DatasetStatus(BaseModel):
    datasetId: str
    status: str
    message: str


class StatusResponseSuccess(BaseModel):
    status: str
    message: str
    datasetsStatus: List[DatasetStatus]


class StatusResponseFailure(BaseModel):
    error: str
    message: str
