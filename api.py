import json
import os
from time import sleep
from typing import Tuple

import requests
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
from generate_data import generate_data

VISMA_CONNECT_CLIENT_ID = os.getenv("VISMA_CONNECT_CLIENT_ID")
VISMA_CONNECT_CLIENT_SECRET = os.getenv("VISMA_CONNECT_CLIENT_SECRET")
VISMA_CONNECT_GRANT_TYPE = os.getenv("VISMA_CONNECT_GRANT_TYPE")
VISMA_CONNECT_SCOPE = os.getenv("VISMA_CONNECT_SCOPE")
VISMA_CONNECT_URL = os.getenv("VISMA_CONNECT_URL")
IO_BASE_URL = os.getenv("IO_BASE_URL")


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


def get_presigned_url() -> Tuple[str, str]:
    url = f"{IO_BASE_URL}/presigned_url"
    headers = {
        "Authorization": f'Bearer {os.getenv("ACCESS_TOKEN")}',
        "tenantId": os.getenv("TENANT_ID"),
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json().get("url"), res.json().get("jobId")
    else:
        print(f"Error getting presigned url. Response:\n{res.json()}")
        return None


def upload_data():
    url, job_id = get_presigned_url()
    if url is not None:
        headers = {"tenantId": os.getenv("TENANT_ID")}
        data = generate_data()
        res = requests.put(
            url,
            data=json.dumps(data),  # NB! Need to use json.dumps() on the dict here
            headers=headers,
        )
        sleep(3)
        res = get_job_status(os.getenv("TENANT_ID"), job_id)
        print(res)


def get_job_status(tenant_id, job_id, max_retries=5) -> str:
    url = f"{IO_BASE_URL}/status"
    headers = {
        "Authorization": f'Bearer {os.getenv("ACCESS_TOKEN")}',
        "tenantId": tenant_id,
        "jobId": job_id,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        tries = 0
        for _ in range(max_retries):
            tries += 1
            sleep(3)
            response = requests.get(url, headers=headers)
            if response.status_code != 404:
                break
    if response.status_code == 200:
        return response.json()
    else:
        return None


# update_access_token()
# get_presigned_url()
upload_data()
