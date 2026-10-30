"""Activity service for normalizing, persisting, and querying developer activities."""

from datetime import datetime, timezone
import json
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.activity import ActivityItem
from backend.app.models.credential import AdoCredential
from backend.app.services.azure_client.client_service import AzureClientService


class ActivityService:
    def __init__(self, db: Session, user_id: int, user_tz: str = "Asia/Kolkata"):
        self.db = db
        self.user_id = user_id
        self.tz = ZoneInfo(user_tz)

    async def sync_client_activities(
        self,
        start_date: str,  # YYYY-MM-DD
        end_date: str,    # YYYY-MM-DD
    ) -> Dict[str, Any]:
        """Synchronizes commits, PRs, and related work from Client Azure DevOps."""
        cred = self.db.scalars(
            select(AdoCredential).where(
                AdoCredential.user_id == self.user_id,
                AdoCredential.provider == "client",
                AdoCredential.is_valid.is_(True),
            )
        ).first()

        if not cred:
            raise ValueError("No valid Client Azure DevOps credential found for user.")

        client_service = AzureClientService(cred.org_url, cred.encrypted_pat)

        # Parse start and end date in user timezone and convert to UTC
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=self.tz)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=self.tz)

        # Fetch repositories
        repos = await client_service.get_repositories()
        total_commits = 0
        total_prs = 0
        new_items = 0

        for repo in repos:
            repo_id = repo.get("id")
            repo_name = repo.get("name")
            project_name = repo.get("project", {}).get("name")

            # Commits
            commits = await client_service.get_commits(
                repository_id=repo_id,
                from_date=start_dt.astimezone(timezone.utc),
                to_date=end_dt.astimezone(timezone.utc),
                author=cred.resolved_identity_name or cred.resolved_identity_email,
            )

            for c in commits:
                total_commits += 1
                c_id = c.get("commitId")
                c_date_raw = c.get("author", {}).get("date")
                if not c_date_raw:
                    continue
                c_dt = datetime.fromisoformat(c_date_raw.replace("Z", "+00:00"))
                # Local date string
                local_dt = c_dt.astimezone(self.tz)
                local_date_str = local_dt.strftime("%Y-%m-%d")

                # Check existing
                existing = self.db.scalars(
                    select(ActivityItem).where(
                        ActivityItem.user_id == self.user_id,
                        ActivityItem.source_type == "commit",
                        ActivityItem.external_id == c_id,
                    )
                ).first()

                if not existing:
                    item = ActivityItem(
                        user_id=self.user_id,
                        source_type="commit",
                        external_id=c_id,
                        repository=repo_name,
                        project=project_name,
                        author_id=c.get("author", {}).get("email"),
                        author_name=c.get("author", {}).get("name"),
                        occurred_at=c_dt,
                        date_str=local_date_str,
                        title=c.get("comment", "").split("\n")[0],
                        description=c.get("comment", ""),
                        url=c.get("remoteUrl") or c.get("url"),
                    )
                    self.db.add(item)
                    new_items += 1

            # Pull Requests
            prs = await client_service.get_pull_requests(
                repository_id=repo_id,
                from_date=start_dt.astimezone(timezone.utc),
                to_date=end_dt.astimezone(timezone.utc),
                creator_id=cred.resolved_identity_id,
            )
            for pr in prs:
                total_prs += 1
                pr_id = str(pr.get("pullRequestId"))
                pr_date_raw = pr.get("creationDate")
                pr_dt = datetime.fromisoformat(pr_date_raw.replace("Z", "+00:00")) if pr_date_raw else datetime.now(timezone.utc)
                local_date_str = pr_dt.astimezone(self.tz).strftime("%Y-%m-%d")

                existing = self.db.scalars(
                    select(ActivityItem).where(
                        ActivityItem.user_id == self.user_id,
                        ActivityItem.source_type == "pull_request",
                        ActivityItem.external_id == pr_id,
                    )
                ).first()

                if not existing:
                    item = ActivityItem(
                        user_id=self.user_id,
                        source_type="pull_request",
                        external_id=pr_id,
                        repository=repo_name,
                        project=project_name,
                        author_id=pr.get("createdBy", {}).get("id"),
                        author_name=pr.get("createdBy", {}).get("displayName"),
                        occurred_at=pr_dt,
                        date_str=local_date_str,
                        title=pr.get("title", ""),
                        description=pr.get("description", ""),
                        url=pr.get("url"),
                    )
                    self.db.add(item)
                    new_items += 1

        self.db.commit()
        return {
            "total_found": total_commits + total_prs,
            "new_added": new_items,
            "commits": total_commits,
            "pull_requests": total_prs,
            "work_items": 0,
            "reviews": 0,
            "branches": 0,
            "date_range": f"{start_date} to {end_date}",
            "last_synced_at": datetime.now(timezone.utc),
        }

    def get_activities_for_date(self, date_str: str, include_excluded: bool = False) -> List[ActivityItem]:
        """Retrieves normalized activities for a given day."""
        stmt = select(ActivityItem).where(
            ActivityItem.user_id == self.user_id,
            ActivityItem.date_str == date_str,
        )
        if not include_excluded:
            stmt = stmt.where(ActivityItem.is_excluded.is_(False))
        return list(self.db.scalars(stmt).all())
