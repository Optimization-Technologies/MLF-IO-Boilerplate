from typing import List
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


### TRAINING ###########################################################################
class StartTrainerParameterObject(BaseModel):
    datasetId: str
    frequency: str
    horizon: int


class StartTrainerPayload(BaseModel):
    parametersArray: List[StartTrainerParameterObject]


class StartTrainerResponseSuccess(BaseModel):
    jobId: str
    message: str


### PREDICTION #########################################################################
class ReplenishmentInterval(BaseModel):
    value: int
    granularity: str


class LeadTime(BaseModel):
    value: int
    granularity: str


class Supplier(BaseModel):
    supplierId: str
    leadTime: LeadTime


class SupplierInfo(BaseModel):
    supplierId: str
    supplierName: str
    minimumOrderValue: float


class CreatePredictionParameterObject(BaseModel):
    datasetId: str
    currentInventoryLevel: float
    wantedServiceLevel: float
    replenishmentInterval: ReplenishmentInterval
    suppliers: List[Supplier]
    supplierInfoArray: List[SupplierInfo]


class CreatePredictionPayload(BaseModel):
    parametersArray: List[CreatePredictionParameterObject]


class CreatePredictionResponseSuccess(BaseModel):
    jobId: str
    message: str


### STATUS #############################################################################
class DatasetStatus(BaseModel):
    datasetId: str
    status: str
    message: str


class StatusResponseSuccess(BaseModel):
    status: str
    message: str
    datasetsStatus: List[DatasetStatus]


### GENERAL ############################################################################
class FailureResponse(BaseModel):
    error: str
    message: str
