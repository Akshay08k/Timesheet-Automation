"""Activity service for normalizing, persisting, and querying developer activities with MongoDB."""

import asyncio
from datetime import datetime, timezone
import json
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo
from pymongo.database import Database
from backend.app.models.database import get_next_sequence_value
from backend.app.models.activity import ActivityItem
from backend.app.models.credential import AdoCredential
from backend.app.services.azure_client.client_service import (
    AzureClientService,
    log_client_fetch,
    log_sync_header,
)


class ActivityService:
    def __init__(self, db: Database, user_id: int, user_tz: str = "Asia/Kolkata"):
        self.db = db
        self.user_id = user_id
        self.tz = ZoneInfo(user_tz)

    async def get_vcqms_context(
        self,
        start_date: str,  # YYYY-MM-DD
        end_date: str,    # YYYY-MM-DD
        sync_to_db: bool = True,
    ) -> Dict[str, Any]:
        """Fetches complete context from Client Azure DevOps strictly scoped to VCQMS repository and PR-linked Work Items."""
        cred_doc = self.db.ado_credentials.find_one(
            {
                "user_id": self.user_id,
                "provider": "client",
                "is_valid": True,
            }
        )

        if not cred_doc:
            raise ValueError("No valid Client Azure DevOps credential found for user.")

        cred = AdoCredential.from_doc(cred_doc)
        client_service = AzureClientService(cred.org_url, cred.encrypted_pat)

        # Retrieve user profile for author matching
        user_doc = self.db.users.find_one({"id": self.user_id}) or {}
        user_fullname = (user_doc.get("full_name") or "").lower()
        user_username = (user_doc.get("username") or "").lower()
        user_email = (user_doc.get("email") or "").lower()
        id_name = (cred.resolved_identity_name or "").lower()
        id_email = (cred.resolved_identity_email or "").lower()

        print("\n==================================================================")
        print(f"[Azure DevOps Sync] Initiated for User: {user_doc.get('username')} ({user_doc.get('full_name')})")
        print(f"[Azure DevOps Sync] Organization: {cred.org_url}")
        print(f"[Azure DevOps Sync] Date Range: {start_date} to {end_date}")
        print(f"[Azure DevOps Sync] Identity Profile: Name='{cred.resolved_identity_name}', Email='{cred.resolved_identity_email}'")
        print("[Azure DevOps Sync] Scope Enforced: STRICTLY VCQMS REPO ONLY")
        print("==================================================================")

        def matches_user(author_name: str, author_email: str) -> bool:
            """Determines if a Git author matches the authenticated user."""
            an = (author_name or "").lower()
            ae = (author_email or "").lower()

            if user_email and user_email == ae:
                return True
            if id_email and id_email == ae:
                return True

            ae_prefix = ae.split("@")[0] if "@" in ae else ""
            if user_username and (user_username in ae_prefix or ae_prefix in user_username):
                return True

            keywords = set(filter(None, [w for w in (user_fullname + " " + id_name).split() if len(w) > 2]))
            keywords.update(["akshay", "komale", "komle"])
            match_count = sum(1 for kw in keywords if kw in an or kw in ae)
            if match_count >= 1 and ("akshay" in an or "akshay" in ae):
                return True

            return False

        # Write session start in fetchClientLogs.txt
        log_sync_header(
            org_url=cred.org_url,
            start_date=start_date,
            end_date=end_date,
            user_info=f"User={user_doc.get('username')} ({user_doc.get('full_name')}) | ADO Identity={cred.resolved_identity_name} <{cred.resolved_identity_email}>",
        )

        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=self.tz)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=self.tz)

        # Fetch repositories
        all_repos = await client_service.get_repositories()
        print(f"[Azure DevOps Sync] Discovered {len(all_repos)} total repositories in client organization.")

        # USER SCOPE: Search in VCQMS and RMAFEModernization repositories
        vcqms_repos = [
            r for r in all_repos
            if "vcqms" in (r.get("name") or "").lower()
            or "vcqms" in (r.get("project", {}).get("name") or "").lower()
            or "rmafemodernization" in (r.get("name") or "").lower()
        ]

        log_client_fetch(
            "REPOSITORY_FILTER_SCOPE",
            f"{cred.org_url}/_apis/git/repositories",
            200,
            {
                "scope_enforced": "VCQMS and RMAFEModernization",
                "total_org_repos": len(all_repos),
                "matched_repos": [r.get("name") for r in vcqms_repos],
                "all_repo_names": [r.get("name") for r in all_repos],
            },
        )

        if not vcqms_repos:
            msg = (
                f"[Azure DevOps Sync Warning] No repository containing 'VCQMS' or 'RMAFEModernization' was found among {len(all_repos)} repos. "
                f"Available repos: {[r.get('name') for r in all_repos[:10]]}"
            )
            print(msg)
            repos_to_scan = []
        else:
            repos_to_scan = vcqms_repos
            print(f"[Azure DevOps Sync] Scope narrowed to {len(repos_to_scan)} repository(ies): {[r.get('name') for r in repos_to_scan]}\n")

        total_commits = 0
        total_prs = 0
        total_work_items = 0
        new_items = 0

        # Optimization: Pre-fetch all existing external IDs for this user in 1 fast query
        existing_external_ids = set(
            self.db.activity_items.distinct("external_id", {"user_id": self.user_id})
        )

        commit_details: List[Dict[str, Any]] = []
        pr_details: List[Dict[str, Any]] = []
        work_item_details: List[Dict[str, Any]] = []

        for idx, repo in enumerate(repos_to_scan, 1):
            repo_id = repo.get("id")
            repo_name = repo.get("name")
            project_name = repo.get("project", {}).get("name")

            # 1. Fetch commits in VCQMS
            author_query = cred.resolved_identity_email or cred.resolved_identity_name
            commits = await client_service.get_commits(
                repository_id=repo_id,
                from_date=start_dt.astimezone(timezone.utc),
                to_date=end_dt.astimezone(timezone.utc),
                author=author_query,
            )

            if not commits:
                all_repo_commits = await client_service.get_commits(
                    repository_id=repo_id,
                    from_date=start_dt.astimezone(timezone.utc),
                    to_date=end_dt.astimezone(timezone.utc),
                )
                commits = [
                    c for c in all_repo_commits
                    if matches_user(
                        c.get("author", {}).get("name", ""),
                        c.get("author", {}).get("email", ""),
                    )
                ]

            for c in commits:
                c_id = c.get("commitId")
                c_date_raw = c.get("author", {}).get("date")
                if not c_date_raw:
                    continue
                c_dt = datetime.fromisoformat(c_date_raw.replace("Z", "+00:00"))
                local_dt = c_dt.astimezone(self.tz)
                local_date_str = local_dt.strftime("%Y-%m-%d")

                author_name = c.get("author", {}).get("name", "")
                author_email = c.get("author", {}).get("email", "")
                title = c.get("comment", "").split("\n")[0].strip()

                print(f"  [Incoming Commit] [{repo_name}] {c_id[:8]} | {local_date_str} | {author_name} <{author_email}> | {title}")

                commit_entry = {
                    "id": c_id,
                    "short_sha": c_id[:8],
                    "title": title,
                    "author_name": author_name,
                    "author_email": author_email,
                    "date": local_date_str,
                    "occurred_at": c_dt.isoformat(),
                    "repository": repo_name,
                    "project": project_name,
                    "url": c.get("remoteUrl") or c.get("url"),
                }
                commit_details.append(commit_entry)

                if sync_to_db and c_id not in existing_external_ids:
                    new_id = get_next_sequence_value(self.db, "activity_items")
                    item = ActivityItem(
                        id=new_id,
                        user_id=self.user_id,
                        source_type="commit",
                        external_id=c_id,
                        repository=repo_name,
                        project=project_name,
                        author_id=author_email,
                        author_name=author_name,
                        occurred_at=c_dt,
                        date_str=local_date_str,
                        title=title,
                        description=c.get("comment", ""),
                        url=c.get("remoteUrl") or c.get("url"),
                    )
                    self.db.activity_items.insert_one(item.to_dict())
                    existing_external_ids.add(c_id)
                    new_items += 1

                total_commits += 1

            # 2. Fetch Pull Requests in VCQMS
            prs = await client_service.get_pull_requests(
                repository_id=repo_id,
                from_date=start_dt.astimezone(timezone.utc),
                to_date=end_dt.astimezone(timezone.utc),
                creator_id=cred.resolved_identity_id,
            )

            if not prs:
                all_prs = await client_service.get_pull_requests(
                    repository_id=repo_id,
                    from_date=start_dt.astimezone(timezone.utc),
                    to_date=end_dt.astimezone(timezone.utc),
                )
                prs = [
                    p for p in all_prs
                    if matches_user(
                        p.get("createdBy", {}).get("displayName", ""),
                        p.get("createdBy", {}).get("uniqueName", ""),
                    )
                ]

            for pr in prs:
                pr_id = str(pr.get("pullRequestId"))
                pr_date_raw = pr.get("creationDate")
                pr_dt = datetime.fromisoformat(pr_date_raw.replace("Z", "+00:00")) if pr_date_raw else datetime.now(timezone.utc)
                local_date_str = pr_dt.astimezone(self.tz).strftime("%Y-%m-%d")
                pr_title = pr.get("title", "").strip()
                pr_status = pr.get("status", "")
                creator_name = pr.get("createdBy", {}).get("displayName", "")

                print(f"  [Incoming PR]     [{repo_name}] #{pr_id} ({pr_status}) | {local_date_str} | Creator: {creator_name} | {pr_title}")

                pr_entry = {
                    "id": pr_id,
                    "title": pr_title,
                    "status": pr_status,
                    "creator": creator_name,
                    "date": local_date_str,
                    "occurred_at": pr_dt.isoformat(),
                    "repository": repo_name,
                    "project": project_name,
                    "url": pr.get("url"),
                    "linked_work_items": [],
                }

                if sync_to_db and pr_id not in existing_external_ids:
                    new_id = get_next_sequence_value(self.db, "activity_items")
                    item = ActivityItem(
                        id=new_id,
                        user_id=self.user_id,
                        source_type="pull_request",
                        external_id=pr_id,
                        repository=repo_name,
                        project=project_name,
                        author_id=pr.get("createdBy", {}).get("id"),
                        author_name=creator_name,
                        occurred_at=pr_dt,
                        date_str=local_date_str,
                        title=pr_title,
                        description=pr.get("description", ""),
                        url=pr.get("url"),
                    )
                    self.db.activity_items.insert_one(item.to_dict())
                    existing_external_ids.add(pr_id)
                    new_items += 1

                total_prs += 1

                # 3. Find WorkItems linked to this PR concurrently
                linked_wis = await client_service.get_pull_request_work_items(repo_id, pr_id)
                valid_refs = [w for w in linked_wis if w.get("id")]
                if valid_refs:
                    raw_details = await asyncio.gather(
                        *[client_service.get_work_item(str(w.get("id"))) for w in valid_refs],
                        return_exceptions=True,
                    )
                else:
                    raw_details = []

                for wi_ref, wi_details in zip(valid_refs, raw_details):
                    if isinstance(wi_details, Exception) or not wi_details:
                        continue
                    wi_id = str(wi_ref.get("id"))
                    fields = (wi_details or {}).get("fields", {})
                    wi_title = fields.get("System.Title") or f"WorkItem #{wi_id}"
                    wi_type = fields.get("System.WorkItemType") or "Task"
                    wi_state = fields.get("System.State") or ""
                    wi_url = (wi_details or {}).get("_links", {}).get("html", {}).get("href") or wi_ref.get("url")

                    print(f"  [Incoming WorkItem] [{repo_name}] {wi_type} #{wi_id} ({wi_state}) | Linked from PR #{pr_id} | {wi_title}")

                    wi_entry = {
                        "id": wi_id,
                        "title": wi_title,
                        "type": wi_type,
                        "state": wi_state,
                        "linked_pr_id": pr_id,
                        "repository": repo_name,
                        "project": project_name,
                        "date": local_date_str,
                        "url": wi_url,
                    }
                    pr_entry["linked_work_items"].append(wi_entry)
                    work_item_details.append(wi_entry)

                    if sync_to_db and wi_id not in existing_external_ids:
                        new_wi_id = get_next_sequence_value(self.db, "activity_items")
                        wi_item = ActivityItem(
                            id=new_wi_id,
                            user_id=self.user_id,
                            source_type="work_item",
                            external_id=wi_id,
                            repository=repo_name,
                            project=project_name,
                            occurred_at=pr_dt,
                            date_str=local_date_str,
                            title=f"[{wi_type}] {wi_title}",
                            description=f"Status: {wi_state}. Linked from Pull Request #{pr_id}: {pr_title}",
                            url=wi_url,
                            related_ids=f"pr:{pr_id}",
                        )
                        self.db.activity_items.insert_one(wi_item.to_dict())
                        existing_external_ids.add(wi_id)
                        new_items += 1

                    total_work_items += 1

                pr_details.append(pr_entry)

        summary_data = {
            "scanned_repositories": [r.get("name") for r in repos_to_scan],
            "total_commits": total_commits,
            "total_prs": total_prs,
            "total_work_items": total_work_items,
            "new_stored_in_db": new_items,
        }
        log_client_fetch("SYNC_SESSION_SUMMARY", f"{cred.org_url}/sync_summary", 200, summary_data)

        print("\n==================================================================")
        print(f"[Azure DevOps Sync Summary] Scanned {len(repos_to_scan)} VCQMS repository(ies).")
        print(f"  -> Total Matching Commits: {total_commits}")
        print(f"  -> Total Matching Pull Requests: {total_prs}")
        print(f"  -> Total Linked Work Items: {total_work_items}")
        print(f"  -> Newly Stored in MongoDB: {new_items}")
        print("  -> Full Raw Logs written to fetchClientLogs.txt")
        print("==================================================================\n")

        return {
            "status": "success",
            "scope": "VCQMS only",
            "target_organization": cred.org_url,
            "authenticated_user": f"{user_doc.get('username')} ({user_doc.get('full_name')})",
            "date_range": f"{start_date} to {end_date}",
            "repositories": [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "project": r.get("project", {}).get("name"),
                }
                for r in repos_to_scan
            ],
            "commits": commit_details,
            "pull_requests": pr_details,
            "work_items": work_item_details,
            "stats": {
                "repositories_count": len(repos_to_scan),
                "commits_count": total_commits,
                "pull_requests_count": total_prs,
                "work_items_count": total_work_items,
                "newly_saved_in_db": new_items,
            },
            "total_found": total_commits + total_prs + total_work_items,
            "new_added": new_items,
            "commits_count": total_commits,
            "pull_requests_count": total_prs,
            "work_items_count": total_work_items,
            "reviews": 0,
            "branches": 0,
            "raw_logs_file": "fetchClientLogs.txt",
            "last_synced_at": datetime.now(timezone.utc),
        }

    async def sync_client_activities(
        self,
        start_date: str,  # YYYY-MM-DD
        end_date: str,    # YYYY-MM-DD
    ) -> Dict[str, Any]:
        """Backward-compatible wrapper for sync activities."""
        res = await self.get_vcqms_context(start_date, end_date, sync_to_db=True)
        return {
            "total_found": res["total_found"],
            "new_added": res["new_added"],
            "commits": res["stats"]["commits_count"],
            "pull_requests": res["stats"]["pull_requests_count"],
            "work_items": res["stats"]["work_items_count"],
            "reviews": 0,
            "branches": 0,
            "date_range": res["date_range"],
            "last_synced_at": res["last_synced_at"],
        }

    def get_activities_for_date(self, date_str: str, include_excluded: bool = False) -> List[ActivityItem]:
        """Retrieves normalized activities for a given day from MongoDB."""
        query: Dict[str, Any] = {
            "user_id": self.user_id,
            "date_str": date_str,
        }
        if not include_excluded:
            query["is_excluded"] = False
        docs = self.db.activity_items.find(query)
        return [ActivityItem.from_doc(d) for d in docs]

    # Alias for client context
    get_client_context = get_vcqms_context
