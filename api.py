import json
import os
from functools import wraps
from time import sleep
from typing import Any, Callable

import requests
from dotenv import find_dotenv, load_dotenv

from data_models import *
from generate_data import *
from token_manager import TokenManager

load_dotenv(find_dotenv())

# Environment variables
VISMA_CONNECT_CLIENT_ID = os.getenv("VISMA_CONNECT_CLIENT_ID")
VISMA_CONNECT_CLIENT_SECRET = os.getenv("VISMA_CONNECT_CLIENT_SECRET")
VISMA_CONNECT_GRANT_TYPE = os.getenv("VISMA_CONNECT_GRANT_TYPE")
VISMA_CONNECT_SCOPE = os.getenv("VISMA_CONNECT_SCOPE")
VISMA_CONNECT_URL = os.getenv("VISMA_CONNECT_URL")
IO_BASE_URL = os.getenv("IO_BASE_URL")
TENANT_ID = os.getenv("TENANT_ID")

# Constants
MAX_RETRIES = 5
SLEEP_DURATION_SHORT = 3
SLEEP_DURATION_LONG = 6


TM = TokenManager()


def handle_token_expiry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OutdatedAccessTokenException:
            print("Access token expired. Refreshing...")
            update_access_token()
            print("Retrying request...")
            return func(*args, **kwargs)
        except Exception as e:
            raise e

    return wrapper


### UPLOAD DATA ########################################################################
def upload_data_from_json(tenant_id: str, path: str):
    return upload_data(tenant_id, load_data_from_json, path)


def upload_dummy_data(tenant_id: str, nbr_datasets: int = 1):
    return upload_data(tenant_id, generate_upload_data_payload, nbr_datasets)


@handle_token_expiry
def upload_data_v2(
    tenant_id: str,
    payload: UploadDataPayload,
) -> List[str]:
    # Start by getting the presigned url to upload data to and the job ID
    presigned_url_response: PresignedUrlResponseSuccess = get_presigned_url(tenant_id)

    # Prepare headers and payload for the request to the presigned url
    headers: dict = TM.generate_headers(include_token=False, tenant_id=tenant_id)

    # Make the request to the presigned url
    print("Uploading data...")
    res = requests.put(
        presigned_url_response.url,
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # Poll the status endpoint until the job is complete
    poll_job_status(tenant_id, presigned_url_response.jobId)

    # Return the dataset IDs that were uploaded
    return [dataset.datasetId for dataset in payload.datasets]


@handle_token_expiry
def upload_data(
    tenant_id: str,
    payload_function: Callable[[Any], UploadDataPayload],
    arg,
) -> List[str]:
    # Start by getting the presigned url to upload data to and the job ID
    presigned_url_response: PresignedUrlResponseSuccess = get_presigned_url(tenant_id)

    # Prepare headers and payload for the request to the presigned url
    headers: dict = TM.generate_headers(include_token=False, tenant_id=tenant_id)
    payload: UploadDataPayload = payload_function(arg)

    # Make the request to the presigned url
    print("Uploading data...")
    res = requests.put(
        presigned_url_response.url,
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # Poll the status endpoint until the job is complete
    poll_job_status(tenant_id, presigned_url_response.jobId)

    # Return the dataset IDs that were uploaded
    return [dataset.datasetId for dataset in payload.datasets]


@handle_token_expiry
def get_presigned_url(tenant_id: str) -> PresignedUrlResponseSuccess:
    # Prepare headers for the request to the /presigned_url endpoint
    url = f"{IO_BASE_URL}/presigned_url"
    headers: dict = TM.generate_headers(tenant_id=tenant_id)

    # Make the request to the /presigned_url endpoint
    print("Getting presigned url...")
    res = requests.get(url, headers=headers)

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # If the request was successful, return the success response
    if res.status_code == 200:
        return PresignedUrlResponseSuccess(**res.json())

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "presigned_url")


### TRAINING ###########################################################################
@handle_token_expiry
def start_trainer(
    tenant_id: str, dataset_ids: list[str] = ["dummy-dataset-1"]
) -> StartTrainerResponseSuccess:
    # Get the headers and payload for the request to the /start_trainer endpoint
    headers = TM.generate_headers(include_content_type=True, tenant_id=tenant_id)
    payload: StartTrainerPayload = generate_start_trainer_payload(dataset_ids)

    # Make the request to the /start_trainer endpoint
    print("Starting trainer...")
    res = requests.post(
        url=f"{IO_BASE_URL}/start_trainer",
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # If the request was successful, poll the status endpoint until the job is complete
    if res.status_code == 202:
        start_trainer_response = StartTrainerResponseSuccess(**res.json())
        poll_job_status(tenant_id, start_trainer_response.jobId)
        return start_trainer_response

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "start_trainer")


### PREDICTION #########################################################################
@handle_token_expiry
def create_prediction(
    tenant_id: str, dataset_ids=["dummy-dataset-1"]
) -> CreatePredictionResponseSuccess:
    # Get the headers and payload for the request to the /create_prediction endpoint
    headers = TM.generate_headers(include_content_type=True, tenant_id=tenant_id)
    payload: CreatePredictionPayload = generate_create_prediction_payload(dataset_ids)

    # Make the request to the /create_prediction endpoint
    print("Creating prediction...")
    res = requests.post(
        url=f"{IO_BASE_URL}/create_prediction",
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # If the request was successful, poll the status endpoint until the job is complete
    if res.status_code == 202:
        create_prediction_response = CreatePredictionResponseSuccess(**res.json())
        poll_job_status(tenant_id, create_prediction_response.jobId)
        print(create_prediction_response.jobId)
        return create_prediction_response

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "create_prediction")


@handle_token_expiry
def get_results(tenant_id: str, job_id: str) -> ResultsResponseSuccess:
    # Get the headers for the request to the /results endpoint
    headers = TM.generate_headers(tenant_id=tenant_id, job_id=job_id)

    # Make the request to the /results endpoint
    print("Getting results...")
    res = requests.get(
        url=f"{IO_BASE_URL}/results",
        headers=headers,
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # If the request was successful, return the success response
    if res.status_code == 200:
        results_response = ResultsResponseSuccess(**res.json())
        msg = (
            results_response.message
            if results_response.message != ""
            else "Job completed successfully!"
        )
        print(f"Results retrieved! Message: {msg}\n")
        return results_response

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "results")


### INVENTORY CLASSIFICATION ###########################################################
@handle_token_expiry
def start_inventory_classification(
    tenant_id: str,
    dataset_ids: List[str],
) -> StartInventoryClassificationResponseSuccess:
    # Get the headers and payload for the request to /start_inventory_classification
    headers = TM.generate_headers(include_content_type=True, tenant_id=tenant_id)
    payload = generate_start_inventory_classification_payload(dataset_ids)

    # Make the request to the /start_inventory_classification endpoint
    print("Starting inventory classification...")
    res = requests.post(
        url=f"{IO_BASE_URL}/start_inventory_classification",
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # If the request was successful, poll the status endpoint until the job is complete
    if res.status_code == 202:
        res = StartInventoryClassificationResponseSuccess(**res.json())
        poll_job_status(tenant_id, res.jobId)
        return res

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "start_inventory_classification")


@handle_token_expiry
def get_inventory_classification_results(
    tenant_id: str,
    job_id: str,
) -> InventoryClassificationResultsResponse:
    # Get the headers for the request to the /inventory_classification_results endpoint
    headers = TM.generate_headers(tenant_id=tenant_id, job_id=job_id)

    # Make the request to the /inventory_classification_results endpoint
    print("Getting inventory classification results...")
    res = requests.get(
        url=f"{IO_BASE_URL}/inventory_classification_results",
        headers=headers,
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # If the request was successful, return the success response
    if res.status_code == 200:
        results_response = InventoryClassificationResultsResponse(**res.json())
        msg = (
            results_response.message
            if results_response.message != ""
            else "NOT IMPLEMENTED"
        )
        print(f"Results retrieved! Message: {msg}\n")
        return results_response

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "inventory_classification_results")


### DELETE DATA ########################################################################
@handle_token_expiry
def delete_data(
    tenant_id: str,
    dataset_id: str,
    from_date: str = "",
    to_date: str = "",
):
    # Get the headers for the request to the /data endpoint
    headers = TM.generate_headers(include_content_type=True, tenant_id=tenant_id)

    # Set the URL and query parameters for the request to the /data endpoint
    url = (
        f"{IO_BASE_URL}/data/{dataset_id}"
        f"{'?fromDate=' + from_date if from_date else ''}"
        f"{'&toDate=' + to_date if to_date else ''}"
    )

    # Make the request to the /data endpoint
    print("Deleting data...")
    res = requests.delete(
        url=url,
        headers=headers,
    )

    # If response status code is 403, raise exception to trigger access token update
    if res.status_code == 403:
        raise OutdatedAccessTokenException("Outdated access token!", res)

    # If the request was successful, return the success response
    if res.status_code == 200:
        data_response = DeleteDataResponseSuccess(**res.json())
        print(f"Data deleted! Message: {data_response.message}\n")
        return data_response

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "data")


### STATUS #############################################################################
def poll_job_status(tenant_id: str, job_id: str):
    print("Polling job status...")
    url = f"{IO_BASE_URL}/status"
    headers: dict = TM.generate_headers(tenant_id=tenant_id, job_id=job_id)
    status_response: StatusResponseSuccess = _start_status_poll(url, headers)
    status_response: StatusResponseSuccess = _call_status_endpoint(url, headers)
    while status_response.status == "inProgress":
        print(f"\tResponse status: {status_response.status}")
        sleep(SLEEP_DURATION_LONG)
        status_response: StatusResponseSuccess = _call_status_endpoint(url, headers)
    print(f"Job complete! Message: {status_response.message}\n")


def _start_status_poll(url: str, headers: dict) -> StatusResponseSuccess:
    res = requests.get(url, headers=headers)
    tries = 0
    while res.status_code == 404 and tries < MAX_RETRIES:
        tries += 1
        sleep(SLEEP_DURATION_SHORT)
        res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return StatusResponseSuccess(**res.json())
    _handle_failed_request(res, "status")


def _call_status_endpoint(url: str, headers: dict) -> StatusResponseSuccess:
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return StatusResponseSuccess(**res.json())
    _handle_failed_request(res, "status")


### ACCESS #############################################################################
def update_access_token():
    res = requests.post(
        url=VISMA_CONNECT_URL,
        data={
            "client_id": VISMA_CONNECT_CLIENT_ID,
            "client_secret": VISMA_CONNECT_CLIENT_SECRET,
            "grant_type": VISMA_CONNECT_GRANT_TYPE,
            "scope": VISMA_CONNECT_SCOPE,
        },
    ).json()
    access_token = res["access_token"]
    TM.update_token(access_token)
    _update_env_file(access_token)


def _update_env_file(access_token: str):
    with open(".env", "r") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith("ACCESS_TOKEN"):
            lines[i] = f"ACCESS_TOKEN={access_token}"
            break
    else:
        lines.append(f"\nACCESS_TOKEN={access_token}")
    with open(".env", "w") as f:
        f.writelines(lines)


### HELPERS ############################################################################
def _handle_failed_request(res: requests.Response, endpoint_name: str):
    failure_resposnse = FailureResponse(**res.json())
    print(
        f"Call to {endpoint_name} failed."
        f"\nError: {failure_resposnse.error}"
        f"\nMessage: {failure_resposnse.message}"
    )
    raise Exception(f"Call to {endpoint_name} failed. See Error and Message above.")


def basic_flow():
    upload_dummy_data(TENANT_ID)
    start_trainer(TENANT_ID)
    res: CreatePredictionResponseSuccess = create_prediction(TENANT_ID)
    get_results(TENANT_ID, job_id=res.jobId)
    delete_data(TENANT_ID, dataset_id="dummy-dataset-1")


def inventory_classification_flow():
    dataset_ids = upload_dummy_data(TENANT_ID, nbr_datasets=10)
    res = start_inventory_classification(TENANT_ID, dataset_ids)
    get_inventory_classification_results(TENANT_ID, res.jobId)
    for dataset_id in dataset_ids:
        delete_data(TENANT_ID, dataset_id=dataset_id)


if __name__ == "__main__":
    basic_flow()
    inventory_classification_flow()
