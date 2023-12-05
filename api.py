import json
import os
from time import sleep
from typing import Tuple

import requests
from dotenv import find_dotenv, load_dotenv

from generate_data import generate_data

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


def upload_data(tenant_id: str):
    url, job_id = get_presigned_url(tenant_id)
    if not url:
        raise Exception("Error getting presigned url")
    headers = _get_headers(include_token=False, tenant_id=tenant_id)
    data = generate_data()
    res = requests.put(
        url,
        data=json.dumps(data),  # NB! Need to use json.dumps() on the dict here
        headers=headers,
    )
    _update_access_token(res.status_code)
    sleep(SLEEP_DURATION_SHORT)
    res = get_job_status(tenant_id, job_id)
    if res and res.get("status") == "success":
        print("Data uploaded successfully")
    else:
        print(f"Error uploading data. Response from the status endpoint:\n{res}")


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


def get_job_status(tenant_id: str, job_id: str) -> str:
    print("Getting job status...")

    url = f"{IO_BASE_URL}/status"
    headers = _get_headers(tenant_id=tenant_id, job_id=job_id)
    response = requests.get(url, headers=headers)

    tries = 0
    while response.status_code == 404 and tries < MAX_RETRIES:
        tries += 1
        sleep(SLEEP_DURATION_SHORT)
        response = requests.get(url, headers=headers)

    if response.status_code == 200:
        while response.json().get("status") == "inProgress":
            print(f'\tResponse status: {response.json().get("status")}')
            sleep(SLEEP_DURATION_LONG)
            response = requests.get(url, headers=headers)
        return response.json()
    else:
        return None


def _get_headers(include_token: bool = True, tenant_id: str = "", job_id: str = ""):
    headers = {}
    if include_token:
        headers["Authorization"] = f'Bearer {os.getenv("ACCESS_TOKEN")}'
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
    _update_env_file("ACCESS_TOKEN", access_token)
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
