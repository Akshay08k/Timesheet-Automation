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

    def _matches_target_user(
        self,
        fields: Dict[str, Any],
        date_str: str,
        user_identity: Optional[str] = None,
        user_email: Optional[str] = None,
    ) -> bool:
        """Validates that a candidate Resource Timesheet work item strictly matches the date and target user."""
        title = (fields.get("System.Title") or "").lower()
        if date_str.lower() not in title:
            custom_date = (fields.get("Custom.Date") or "").lower()
            if date_str.lower() not in custom_date:
                return False

        assigned_obj = fields.get("System.AssignedTo") or {}
        assigned_name = (assigned_obj.get("displayName") or "").lower() if isinstance(assigned_obj, dict) else str(assigned_obj).lower()
        assigned_email = (assigned_obj.get("uniqueName") or "").lower() if isinstance(assigned_obj, dict) else ""

        created_obj = fields.get("System.CreatedBy") or {}
        created_name = (created_obj.get("displayName") or "").lower() if isinstance(created_obj, dict) else str(created_obj).lower()
        created_email = (created_obj.get("uniqueName") or "").lower() if isinstance(created_obj, dict) else ""

        # Collect user matching keywords/tokens
        tokens = set()
        if user_identity:
            ident_clean = user_identity.lower().strip()
            tokens.add(ident_clean)
            for part in ident_clean.split():
                if len(part) >= 3:
                    tokens.add(part)
        if user_email:
            email_clean = user_email.lower().strip()
            tokens.add(email_clean)
            prefix = email_clean.split("@")[0]
            if len(prefix) >= 3:
                tokens.add(prefix)

        if not tokens:
            return True

        for tok in tokens:
            if tok in title:
                return True
            if tok in assigned_name or (assigned_email and tok in assigned_email):
                return True
            if tok in created_name or (created_email and tok in created_email):
                return True

        return False

    async def search_existing_timesheet(
        self,
        date_str: str,
        user_identity: Optional[str] = None,
        user_email: Optional[str] = None,
        project: str = "Rysun Project Management",
    ) -> Optional[Dict[str, Any]]:
        """Queries Rysun using WIQL to find if a Resource Timesheet work item already exists for this date and user."""
        clean_date = date_str.replace("'", "''").strip()
        clauses = [
            "[System.WorkItemType] = 'Resource Timesheet'",
            f"[System.Title] CONTAINS '{clean_date}'",
        ]

        user_clauses = ["[System.AssignedTo] = @Me"]
        if user_identity and user_identity.strip():
            clean_user = user_identity.replace("'", "''").strip()
            user_clauses.append(f"[System.Title] CONTAINS '{clean_user}'")
            first_name = clean_user.split()[0]
            if len(first_name) >= 3 and first_name != clean_user:
                user_clauses.append(f"[System.Title] CONTAINS '{first_name}'")
        if user_email and user_email.strip():
            clean_email = user_email.replace("'", "''").strip()
            user_clauses.append(f"[System.Title] CONTAINS '{clean_email}'")

        clauses.append(f"({' OR '.join(user_clauses)})")
        where_stmt = " AND ".join(clauses)

        url = f"{self.org_url}/{project}/_apis/wit/wiql?api-version=7.1"
        query = {
            "query": f"""
                SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
                FROM WorkItems
                WHERE {where_stmt}
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

            # Verify found work items to strictly ensure they belong to this user
            for item in work_items[:5]:
                first_id = item.get("id")
                if not first_id:
                    continue
                item_resp = await client.get(
                    f"{self.org_url}/_apis/wit/workitems/{first_id}?api-version=7.1",
                    headers=self.auth_header,
                )
                if item_resp.status_code == 200:
                    item_data = item_resp.json()
                    fields = item_data.get("fields", {})
                    if self._matches_target_user(fields, date_str, user_identity, user_email):
                        return item_data

            return None

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
