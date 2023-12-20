import os


class TokenManager:
    def __init__(self):
        self.token = os.getenv("ACCESS_TOKEN")

    def update_token(self, new_token: str):
        self.token = new_token

    def generate_headers(
        self,
        include_token: bool = True,
        include_content_type: bool = False,
        tenant_id: str = "",
        job_id: str = "",
    ) -> dict:
        headers = {}
        if include_token:
            headers["Authorization"] = f"Bearer {self.token}"
        if include_content_type:
            headers["Content-Type"] = "application/json"
        if tenant_id:
            headers["tenantId"] = tenant_id
        if job_id:
            headers["jobId"] = job_id
        return headers
