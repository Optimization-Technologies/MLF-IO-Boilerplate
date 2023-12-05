import json
import os
from time import sleep
from typing import Tuple

import requests
from dotenv import find_dotenv, load_dotenv

from generate_data import *

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
TODO
- Create pydantic models for headers, payloads, responses, etc.
- Make better exceptions for crashing the script where you want to crash it
"""


### TRAINING ###########################################################################
def start_trainer(tenant_id: str):
    print("Starting trainer...")

    # Get the headers and payload for the request to the /start_trainer endpoint
    headers = _get_headers(include_content_type=True, tenant_id=tenant_id)
    payload = generate_start_trainer_payload()

    # Make the request to the /start_trainer endpoint
    res = requests.post(
        url=f"{IO_BASE_URL}/start_trainer",
        headers=headers,
        data=json.dumps(payload),  # NB! Need to use json.dumps() to make dict -> str
    )

    # Check the status code to see if access token is outdated (re-run script if so)
    _update_access_token(res.status_code)

    # Check if the request was successful (break if not)
    is_success = _is_request_success(res)
    if not is_success:
        return False

    # If the request was successful, poll the status endpoint until the job is complete
    job_id = res.json().get("jobId")
    is_success = _poll_status_until_complete(tenant_id, job_id)
    return is_success


def _is_request_success(res: requests.Response) -> bool:
    print(res.json().get("message"))
    if res.status_code == 202:
        return True
    else:
        return False


def _poll_status_until_complete(tenant_id: str, job_id: str) -> bool:
    sleep(SLEEP_DURATION_SHORT)
    res = poll_job_status(tenant_id, job_id)
    if res.status_code == 200:
        print(res.json().get("message"))
    else:
        print(res.status_code)
    if res and res.get("status") == "success":
        return True
    else:
        return False


### DATA ###############################################################################
def upload_data(tenant_id: str):
    url, job_id = get_presigned_url(tenant_id)
    if not url:
        raise Exception("Error getting presigned url")
    headers = _get_headers(include_token=False, tenant_id=tenant_id)
    data = generate_raw_data()
    print("Uploading data...")
    res = requests.put(
        url,
        data=json.dumps(data),  # NB! Need to use json.dumps() to make dict -> str
        headers=headers,
    )
    _update_access_token(res.status_code)
    sleep(SLEEP_DURATION_SHORT)
    poll_job_status(tenant_id, job_id)


def get_presigned_url(tenant_id: str) -> Tuple[str, str]:
    print("Getting presigned url...")
    url = f"{IO_BASE_URL}/presigned_url"
    headers = _get_headers(tenant_id=tenant_id)
    res = requests.get(url, headers=headers)
    _update_access_token(res.status_code)
    if res.status_code == 200:
        return res.json().get("url"), res.json().get("jobId")
    else:
        print(f"Error getting presigned url. Response:\n{res.json()}")
        return None


### STATUS ########################################################################
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


def poll_job_status(tenant_id: str, job_id: str):
    print("Polling job status...")
    url = f"{IO_BASE_URL}/status"
    headers = _get_headers(tenant_id=tenant_id, job_id=job_id)
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
    _handle_failed_status_call(res)


def _call_status_endpoint(url: str, headers: dict) -> StatusResponseSuccess:
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return StatusResponseSuccess(**res.json())
    _handle_failed_status_call(res)


def _handle_failed_status_call(res: requests.Response):
    status_response = StatusResponseFailure(**res.json())
    print(
        f"Status call failed."
        f"\nError: {status_response.error}"
        f"\nMessage: {status_response.message}"
    )
    raise Exception("Status call failed.")


def _get_headers(
    include_token: bool = True,
    include_content_type: bool = False,
    tenant_id: str = "",
    job_id: str = "",
):
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


def _update_access_token(status_code: int):
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


upload_data(TENANT_ID)
# start_trainer(TENANT_ID)
