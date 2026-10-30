"""Azure DevOps Client connector for retrieving engineering activity."""

import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from backend.app.security.crypto import decrypt_pat


class AzureClientService:
    def __init__(self, org_url: str, encrypted_pat: str):
        self.org_url = org_url.rstrip("/")
        self.pat = decrypt_pat(encrypted_pat)
        self.auth_header = {
            "Authorization": f"Basic {base64.b64encode(f':{self.pat}'.encode()).decode()}",
            "Content-Type": "application/json",
        }

    async def validate_connection(self) -> Dict[str, Any]:
        """Validates connection and resolves user identity."""
        url = f"{self.org_url}/_apis/connectionData?api-version=7.1-preview.1"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            if resp.status_code == 401:
                raise ValueError("Authentication failed. Invalid or expired Client PAT.")
            if resp.status_code != 200:
                raise ValueError(f"Azure DevOps connection error: HTTP {resp.status_code} - {resp.text}")

            data = resp.json()
            authenticated_user = data.get("authenticatedUser", {})
            return {
                "id": authenticated_user.get("id"),
                "name": authenticated_user.get("providerDisplayName") or authenticated_user.get("customDisplayName"),
                "email": authenticated_user.get("mailAddress") or authenticated_user.get("preferredEmailAddress"),
            }

    async def get_projects(self) -> List[Dict[str, Any]]:
        """Retrieves list of accessible projects in the client organization."""
        url = f"{self.org_url}/_apis/projects?api-version=7.1"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            if resp.status_code != 200:
                return []
            return resp.json().get("value", [])

    async def get_repositories(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves Git repositories."""
        if project_id:
            url = f"{self.org_url}/{project_id}/_apis/git/repositories?api-version=7.1"
        else:
            url = f"{self.org_url}/_apis/git/repositories?api-version=7.1"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            if resp.status_code != 200:
                return []
            return resp.json().get("value", [])

    async def get_commits(
        self,
        repository_id: str,
        from_date: datetime,
        to_date: datetime,
        author: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves commits within date range."""
        params = {
            "searchCriteria.fromDate": from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "searchCriteria.toDate": to_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "api-version": "7.1",
            "$top": "200",
        }
        if author:
            params["searchCriteria.author"] = author

        url = f"{self.org_url}/_apis/git/repositories/{repository_id}/commits"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.auth_header, params=params)
            if resp.status_code != 200:
                return []
            return resp.json().get("value", [])

    async def get_pull_requests(
        self,
        repository_id: str,
        from_date: datetime,
        to_date: datetime,
        creator_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves pull requests updated or created in date range."""
        params = {
            "searchCriteria.status": "all",
            "api-version": "7.1",
            "$top": "100",
        }
        if creator_id:
            params["searchCriteria.creatorId"] = creator_id

        url = f"{self.org_url}/_apis/git/repositories/{repository_id}/pullrequests"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.auth_header, params=params)
            if resp.status_code != 200:
                return []
            items = resp.json().get("value", [])
            # Filter in-range
            filtered = []
            for item in items:
                creation_date_str = item.get("creationDate")
                if creation_date_str:
                    c_date = datetime.fromisoformat(creation_date_str.replace("Z", "+00:00"))
                    if from_date <= c_date <= to_date:
                        filtered.append(item)
            return filtered
