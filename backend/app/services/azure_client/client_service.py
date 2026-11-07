"""Azure DevOps Client connector for retrieving engineering activity with verbose file & console logging."""

import base64
from datetime import datetime, timezone
import json
import os
from typing import Dict, Any, List, Optional
import httpx
from backend.app.security.crypto import decrypt_pat


FETCH_LOG_FILE = os.path.abspath("fetchClientLogs.txt")


def log_client_fetch(entry_type: str, url: str, status_code: int, payload: Any):
    """Appends raw API communication details directly to fetchClientLogs.txt."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(FETCH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"[{timestamp}] [{entry_type}] HTTP {status_code}\n")
            f.write(f"URL: {url}\n")
            f.write(f"{'-' * 80}\n")
            if isinstance(payload, (dict, list)):
                f.write(json.dumps(payload, indent=2, default=str))
            else:
                f.write(str(payload))
            f.write(f"\n{'=' * 80}\n")
    except Exception as e:
        print(f"[Log Error] Failed to write to fetchClientLogs.txt: {e}")


def log_sync_header(org_url: str, start_date: str, end_date: str, user_info: str):
    """Writes session header for a client sync run in fetchClientLogs.txt."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(FETCH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n\n{'#' * 80}\n")
            f.write(f"# AZURE DEVOPS CLIENT SYNC SESSION - {timestamp}\n")
            f.write(f"# Target Org: {org_url}\n")
            f.write(f"# Date Range: {start_date} to {end_date}\n")
            f.write(f"# User Profile: {user_info}\n")
            f.write(f"# Scope: Client Repository & PR linked Work Items\n")
            f.write(f"{'#' * 80}\n\n")
    except Exception as e:
        print(f"[Log Error] Failed to write session header to fetchClientLogs.txt: {e}")


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
            log_client_fetch("VALIDATE_CONNECTION", url, resp.status_code, resp.text[:500])
            if resp.status_code == 401:
                print(f"[Client ADO] Validation 401: Invalid or expired PAT for {self.org_url}")
                raise ValueError("Authentication failed. Invalid or expired Client PAT.")
            if resp.status_code != 200:
                print(f"[Client ADO] Validation failed: HTTP {resp.status_code} - {resp.text[:200]}")
                raise ValueError(f"Azure DevOps connection error: HTTP {resp.status_code} - {resp.text}")

            data = resp.json()
            authenticated_user = data.get("authenticatedUser", {})
            identity_info = {
                "id": authenticated_user.get("id"),
                "name": authenticated_user.get("providerDisplayName") or authenticated_user.get("customDisplayName"),
                "email": authenticated_user.get("mailAddress") or authenticated_user.get("preferredEmailAddress"),
            }
            print(f"[Client ADO] Validated identity successfully: {identity_info['name']} ({identity_info['email']})")
            return identity_info

    async def get_projects(self) -> List[Dict[str, Any]]:
        """Retrieves list of accessible projects in the client organization."""
        url = f"{self.org_url}/_apis/projects?api-version=7.1"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            log_client_fetch("GET_PROJECTS", url, resp.status_code, resp.json() if resp.status_code == 200 else resp.text[:300])
            if resp.status_code != 200:
                print(f"[Client ADO Error] GET {url} failed: HTTP {resp.status_code} - {resp.text[:200]}")
                return []
            projects = resp.json().get("value", [])
            print(f"[Client ADO] Fetched {len(projects)} accessible projects from {self.org_url}")
            return projects

    async def get_repositories(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves Git repositories."""
        if project_id:
            url = f"{self.org_url}/{project_id}/_apis/git/repositories?api-version=7.1"
        else:
            url = f"{self.org_url}/_apis/git/repositories?api-version=7.1"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            log_client_fetch("GET_REPOSITORIES", url, resp.status_code, resp.json() if resp.status_code == 200 else resp.text[:300])
            if resp.status_code != 200:
                print(f"[Client ADO Error] GET repositories failed: HTTP {resp.status_code} - {resp.text[:200]}")
                return []
            repos = resp.json().get("value", [])
            print(f"[Client ADO] Discovered {len(repos)} repositories in {self.org_url}")
            return repos

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
            log_client_fetch(f"GET_COMMITS (repo={repository_id}, author={author})", str(resp.url), resp.status_code, resp.json() if resp.status_code == 200 else resp.text[:300])
            if resp.status_code != 200:
                print(f"[Client ADO Error] GET commits for repo {repository_id} failed: HTTP {resp.status_code} - {resp.text[:200]}")
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
            log_client_fetch(f"GET_PULL_REQUESTS (repo={repository_id}, creator={creator_id})", str(resp.url), resp.status_code, resp.json() if resp.status_code == 200 else resp.text[:300])
            if resp.status_code != 200:
                print(f"[Client ADO Error] GET pull requests for repo {repository_id} failed: HTTP {resp.status_code} - {resp.text[:200]}")
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

    async def get_pull_request_work_items(
        self,
        repository_id: str,
        pull_request_id: str,
    ) -> List[Dict[str, Any]]:
        """Retrieves work items linked to a specific pull request."""
        url = f"{self.org_url}/_apis/git/repositories/{repository_id}/pullRequests/{pull_request_id}/workitems?api-version=7.1"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            log_client_fetch(f"GET_PR_WORK_ITEMS (PR #{pull_request_id})", url, resp.status_code, resp.json() if resp.status_code == 200 else resp.text[:300])
            if resp.status_code != 200:
                print(f"[Client ADO Error] GET work items for PR #{pull_request_id} failed: HTTP {resp.status_code}")
                return []
            return resp.json().get("value", [])

    async def get_work_item(self, work_item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a work item by ID."""
        url = f"{self.org_url}/_apis/wit/workitems/{work_item_id}?api-version=7.1"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            log_client_fetch(f"GET_WORK_ITEM #{work_item_id}", url, resp.status_code, resp.json() if resp.status_code == 200 else resp.text[:300])
            if resp.status_code != 200:
                return None
            return resp.json()
