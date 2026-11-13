"""Rysun Azure DevOps connector for Resource Timesheet discovery and submission."""

import base64
from typing import Dict, Any, List, Optional
import httpx
from backend.app.security.crypto import decrypt_pat


class AzureRysunService:
    def __init__(self, org_url: str, encrypted_pat: str):
        self.org_url = org_url.rstrip("/")
        self.pat = decrypt_pat(encrypted_pat)
        self.auth_header = {
            "Authorization": f"Basic {base64.b64encode(f':{self.pat}'.encode()).decode()}",
            "Content-Type": "application/json",
        }
        self.patch_header = {
            "Authorization": f"Basic {base64.b64encode(f':{self.pat}'.encode()).decode()}",
            "Content-Type": "application/json-patch+json",
        }

    async def validate_connection(self) -> Dict[str, Any]:
        """Validates connection and resolves user identity in Rysun ADO."""
        url = f"{self.org_url}/_apis/connectionData?api-version=7.1-preview.1"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            if resp.status_code == 401:
                raise ValueError("Authentication failed. Invalid or expired Rysun PAT.")
            if resp.status_code != 200:
                raise ValueError(f"Rysun Azure DevOps connection error: HTTP {resp.status_code} - {resp.text}")

            data = resp.json()
            authenticated_user = data.get("authenticatedUser", {})
            return {
                "id": authenticated_user.get("id"),
                "name": authenticated_user.get("providerDisplayName") or authenticated_user.get("customDisplayName"),
                "email": authenticated_user.get("mailAddress") or authenticated_user.get("preferredEmailAddress"),
            }

    async def discover_timesheet_fields(self, project: str = "Rysun Project Management") -> Dict[str, Any]:
        """Discovers the schema and custom field definitions of the Resource Timesheet work item type."""
        url = f"{self.org_url}/{project}/_apis/wit/workitemtypes/Resource%20Timesheet?api-version=7.1"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=self.auth_header)
            if resp.status_code == 200:
                data = resp.json()
                fields = data.get("fields", [])
                field_map = {f.get("referenceName"): f.get("name") for f in fields}
                return {
                    "success": True,
                    "work_item_type": "Resource Timesheet",
                    "fields": field_map,
                }
            return {
                "success": False,
                "error": f"Failed to retrieve Resource Timesheet fields: HTTP {resp.status_code}",
            }

    async def search_existing_timesheet(
        self,
        date_str: str,
        user_identity: str,
        project: str = "Rysun Project Management",
    ) -> Optional[Dict[str, Any]]:
        """Queries Rysun using WIQL to find if a Resource Timesheet work item already exists for this date and user."""
        url = f"{self.org_url}/{project}/_apis/wit/wiql?api-version=7.1"
        query = {
            "query": f"""
                SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
                FROM WorkItems
                WHERE [System.WorkItemType] = 'Resource Timesheet'
                AND [System.Title] CONTAINS '{date_str}'
                ORDER BY [System.CreatedDate] DESC
            """
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=self.auth_header, json=query)
            if resp.status_code != 200:
                return None

            data = resp.json()
            work_items = data.get("workItems", [])
            if not work_items:
                return None

            first_id = work_items[0].get("id")
            # Fetch details for the found item
            item_resp = await client.get(
                f"{self.org_url}/_apis/wit/workitems/{first_id}?api-version=7.1",
                headers=self.auth_header,
            )
            if item_resp.status_code == 200:
                return item_resp.json()
            return {"id": first_id}

    async def create_resource_timesheet(
        self,
        title: str,
        fields_patch: List[Dict[str, Any]],
        project: str = "Rysun Project Management",
    ) -> Dict[str, Any]:
        """Creates a Resource Timesheet work item in Rysun."""
        url = f"{self.org_url}/{project}/_apis/wit/workitems/$Resource%20Timesheet?api-version=7.1"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self.patch_header, json=fields_patch)
            if resp.status_code in (200, 201):
                return resp.json()
            raise ValueError(f"Failed to create Resource Timesheet work item: HTTP {resp.status_code} - {resp.text}")

    async def update_resource_timesheet(
        self,
        workitem_id: int,
        fields_patch: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Updates an existing Resource Timesheet work item in Rysun."""
        url = f"{self.org_url}/_apis/wit/workitems/{workitem_id}?api-version=7.1"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(url, headers=self.patch_header, json=fields_patch)
            if resp.status_code == 200:
                return resp.json()
            raise ValueError(f"Failed to update Resource Timesheet work item {workitem_id}: HTTP {resp.status_code} - {resp.text}")


# Compatibility alias
AzureMyCompanyService = AzureRysunService
