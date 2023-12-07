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


class CreatePredictionPayload(BaseModel):
    parametersArray: List[CreatePredictionParameterObject]
    supplierInfoArray: List[SupplierInfo]


class CreatePredictionResponseSuccess(BaseModel):
    jobId: str
    message: str


class ValidDateInterval(BaseModel):
    startDate: str
    endDate: str


class Suggestion(BaseModel):
    quantity: float
    validDateInterval: ValidDateInterval


class ForecastObject(BaseModel):
    date: str
    predictedQuantity: float
    predictedSeason: float
    predictedTrend: float
    predictedNoise: float
    lowerQuantity: float
    upperQuantity: float


class HistoricalDataObject(BaseModel):
    date: str
    quantity: float


class ResultsObject(BaseModel):
    datasetId: str
    supplierId: str
    safetyStockSuggestion: Suggestion
    reorderPointSuggestion: Suggestion
    replenishmentSuggestion: Suggestion
    forecast: List[ForecastObject]
    historicalData: List[HistoricalDataObject]


class ResultsResponseSuccess(BaseModel):
    results: List[ResultsObject]


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
