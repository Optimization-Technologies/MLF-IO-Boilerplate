import json
import os
from time import sleep

import requests
from dotenv import find_dotenv, load_dotenv

from generate_data import *
from data_models import *

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


"""
TODO Stuff identified to fix later:
- Required fields in responses - make sure all fields that we list in responses are actually there anyway
- We do not seem to always return a message from the Results endpoint (not for 200 OK)
"""


### DATA ###############################################################################
def upload_data(tenant_id: str):
    # Start by getting the presigned url to upload data to and the job ID
    presigned_url_response: PresignedUrlResponseSuccess = get_presigned_url(tenant_id)

    # Prepare headers and payload for the request to the presigned url
    headers: dict = generate_headers(include_token=False, tenant_id=tenant_id)
    payload: UploadDataPayload = generate_upload_data_payload()

    # Make the request to the presigned url
    print("Uploading data...")
    res = requests.put(
        presigned_url_response.url,
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # Check the status code to see if access token is outdated (re-run script if so)
    update_access_token(res.status_code)

    # Wait for a bit, then start polling the status endpoint
    sleep(SLEEP_DURATION_SHORT)
    poll_job_status(tenant_id, presigned_url_response.jobId)


def get_presigned_url(tenant_id: str) -> PresignedUrlResponseSuccess:
    # Prepare headers for the request to the /presigned_url endpoint
    url = f"{IO_BASE_URL}/presigned_url"
    headers: dict = generate_headers(tenant_id=tenant_id)

    # Make the request to the /presigned_url endpoint
    print("Getting presigned url...")
    res = requests.get(url, headers=headers)

    # Check the status code to see if access token is outdated (re-run script if so)
    update_access_token(res.status_code)

    # If the request was successful, return the success response
    if res.status_code == 200:
        return PresignedUrlResponseSuccess(**res.json())

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "presigned_url")


### TRAINING ###########################################################################
def start_trainer(tenant_id: str) -> StartTrainerResponseSuccess:
    # Get the headers and payload for the request to the /start_trainer endpoint
    headers = generate_headers(include_content_type=True, tenant_id=tenant_id)
    payload: StartTrainerPayload = generate_start_trainer_payload()

    # Make the request to the /start_trainer endpoint
    print("Starting trainer...")
    res = requests.post(
        url=f"{IO_BASE_URL}/start_trainer",
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # Check the status code to see if access token is outdated (re-run script if so)
    update_access_token(res.status_code)

    # If the request was successful, poll the status endpoint until the job is complete
    if res.status_code == 202:
        start_trainer_response = StartTrainerResponseSuccess(**res.json())
        sleep(SLEEP_DURATION_SHORT)
        poll_job_status(tenant_id, start_trainer_response.jobId)
        return start_trainer_response

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "start_trainer")


### PREDICTION #########################################################################
def create_prediction(tenant_id: str) -> CreatePredictionResponseSuccess:
    # Get the headers and payload for the request to the /create_prediction endpoint
    headers = generate_headers(include_content_type=True, tenant_id=tenant_id)
    payload: CreatePredictionPayload = generate_create_prediction_payload()

    # Make the request to the /create_prediction endpoint
    print("Creating prediction...")
    res = requests.post(
        url=f"{IO_BASE_URL}/create_prediction",
        headers=headers,
        data=json.dumps(payload.model_dump()),  # NB! Need to stringify
    )

    # Check the status code to see if access token is outdated (re-run script if so)
    update_access_token(res.status_code)

    # If the request was successful, poll the status endpoint until the job is complete
    if res.status_code == 202:
        create_prediction_response = CreatePredictionResponseSuccess(**res.json())
        sleep(SLEEP_DURATION_SHORT)
        poll_job_status(tenant_id, create_prediction_response.jobId)
        return create_prediction_response

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "create_prediction")


def get_results(tenant_id: str, job_id: str) -> ResultsResponseSuccess:
    # Get the headers and payload for the request to the /prediction_results endpoint
    headers = generate_headers(tenant_id=tenant_id, job_id=job_id)

    # Make the request to the /prediction_results endpoint
    print("Getting prediction results...")
    res = requests.get(
        url=f"{IO_BASE_URL}/results",
        headers=headers,
    )

    # Check the status code to see if access token is outdated (re-run script if so)
    update_access_token(res.status_code)

    # If the request was successful, return the success response
    if res.status_code == 200:
        return ResultsResponseSuccess(**res.json())

    # If not, handle the failure by printing the error message and raising an exception
    _handle_failed_request(res, "results")


### STATUS #############################################################################
def poll_job_status(tenant_id: str, job_id: str):
    print("Polling job status...")
    url = f"{IO_BASE_URL}/status"
    headers: dict = generate_headers(tenant_id=tenant_id, job_id=job_id)
    status_response: StatusResponseSuccess = _start_status_poll(url, headers)
    status_response: StatusResponseSuccess = _call_status_endpoint(url, headers)
    while status_response.status == "inProgress":
        print(f"\tResponse status: {status_response.status}")
        sleep(SLEEP_DURATION_LONG)
        status_response: StatusResponseSuccess = _call_status_endpoint(url, headers)
    print(f"Job complete! Message: {status_response.message}")


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
def update_access_token(status_code: int):
    if status_code != 403:
        return
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
    _update_env_file(access_token)
    raise Exception("Access token had expired. New token generated. Try again.")


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


### GENERAL ############################################################################
def _handle_failed_request(res: requests.Response, endpoint_name: str):
    failure_resposnse = FailureResponse(**res.json())
    print(
        f"Call to {endpoint_name} failed."
        f"\nError: {failure_resposnse.error}"
        f"\nMessage: {failure_resposnse.message}"
    )
    raise Exception(f"Call to {endpoint_name} failed. See Error and Message above.")


# upload_data(TENANT_ID)
# start_trainer(TENANT_ID)
# res: CreatePredictionResponseSuccess = create_prediction(TENANT_ID)
get_results(TENANT_ID, job_id="55148db5b3fc412fa7ac7c6a61a3cf72")
