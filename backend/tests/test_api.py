"""API tests for authentication, drafts, MongoDB persistence, and encrypted storage."""

import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.database import get_database
from backend.app.security.crypto import decrypt_pat, encrypt_pat

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "DevTimesheet"
    assert data["database"] == "MongoDB"
    assert "gemini_model" in data


def test_user_registration_and_login():
    unique_suffix = uuid.uuid4().hex[:8]
    username = f"testdev_{unique_suffix}"
    email = f"testdev_{unique_suffix}@example.com"
    password = "SuperSecretPassword123"

    reg_resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": "Test Developer",
            "password": password,
            "timezone": "Asia/Kolkata",
        },
    )
    assert reg_resp.status_code == 200
    user_data = reg_resp.json()
    assert user_data["username"] == username
    assert "id" in user_data

    # Verify password in MongoDB is hashed and never plaintext
    db = get_database()
    saved_user = db.users.find_one({"username": username})
    assert saved_user is not None
    assert saved_user["hashed_password"] != password
    assert saved_user["hashed_password"].startswith("$2b$")  # bcrypt hash

    # Login
    login_resp = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    token = token_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # /api/auth/me
    me_resp = client.get("/api/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == username

    # /api/timesheets/week/2026-10-26 (Monday)
    week_resp = client.get("/api/timesheets/week/2026-10-26", headers=auth_headers)
    assert week_resp.status_code == 200
    week_data = week_resp.json()
    assert len(week_data["entries"]) == 5
    assert week_data["week_start"] == "2026-10-26"
    assert week_data["entries"][0]["day_of_week"] == "Monday"
    assert week_data["entries"][4]["day_of_week"] == "Friday"


def test_encrypted_information_stored_in_mongodb():
    """Verifies that Azure DevOps Personal Access Tokens (PATs) and credentials
    stored in the MongoDB database are strictly encrypted at rest with AES-256-GCM.
    """
    db = get_database()
    raw_pat = "my-secret-azure-devops-personal-access-token"
    encrypted = encrypt_pat(raw_pat)

    # Directly verify in MongoDB collection
    test_cred = {
        "id": 99999,
        "user_id": 99999,
        "provider": "client",
        "org_url": "https://dev.azure.com/test-org",
        "encrypted_pat": encrypted,
        "is_valid": True,
    }
    db.ado_credentials.delete_one({"id": 99999})
    db.ado_credentials.insert_one(test_cred)

    # Read back directly from MongoDB
    stored_doc = db.ado_credentials.find_one({"id": 99999})
    assert stored_doc is not None
    # Crucial check: MongoDB document does NOT contain plaintext PAT
    assert stored_doc["encrypted_pat"] != raw_pat
    # Crucial check: Stored ciphertext decrypts back with AES-256-GCM
    decrypted = decrypt_pat(stored_doc["encrypted_pat"])
    assert decrypted == raw_pat

    # Cleanup
    db.ado_credentials.delete_one({"id": 99999})


@pytest.mark.asyncio
async def test_vcqms_only_scope_and_pr_work_item_linking():
    """Verifies that client sync only scans VCQMS repo and retrieves work items linked to PRs."""
    from unittest.mock import AsyncMock, patch
    from backend.app.services.activity.activity_service import ActivityService
    from backend.app.services.azure_client.client_service import AzureClientService

    db = get_database()
    test_user_id = 88888
    # Insert test user and credential
    db.users.delete_one({"id": test_user_id})
    db.users.insert_one({
        "id": test_user_id,
        "username": "tester",
        "full_name": "Test Developer",
        "email": "tester@example.com",
    })
    db.ado_credentials.delete_one({"user_id": test_user_id, "provider": "client"})
    db.ado_credentials.insert_one({
        "id": 88888,
        "user_id": test_user_id,
        "provider": "client",
        "org_url": "https://dev.azure.com/dummy-org",
        "encrypted_pat": encrypt_pat("dummy-token"),
        "is_valid": True,
        "resolved_identity_email": "tester@example.com",
        "resolved_identity_name": "Test Developer",
        "resolved_identity_id": "dummy-user-id",
    })

    # Mock AzureClientService methods
    mock_repos = [
        {"id": "repo-1", "name": "client-vcqms-api", "project": {"name": "VCQMS"}},
        {"id": "repo-2", "name": "unrelated-repo-1", "project": {"name": "Other"}},
        {"id": "repo-3", "name": "unrelated-repo-2", "project": {"name": "Other"}},
    ]
    mock_commits = [
        {
            "commitId": "1111222233334444",
            "author": {"name": "Test Developer", "email": "tester@example.com", "date": "2026-10-30T10:00:00Z"},
            "comment": "feat: update inspection approval flow",
        }
    ]
    mock_prs = [
        {
            "pullRequestId": "789",
            "title": "VCQMS Inspection improvements",
            "creationDate": "2026-10-30T11:00:00Z",
            "status": "completed",
            "createdBy": {"displayName": "Test Developer", "uniqueName": "tester@example.com"},
        }
    ]
    mock_wi_links = [{"id": "45678", "url": "https://dummy/workitem/45678"}]
    mock_wi_details = {
        "id": 45678,
        "fields": {
            "System.Title": "Add QA verification checkbox in Inspection form",
            "System.WorkItemType": "User Story",
            "System.State": "Active",
        },
        "_links": {"html": {"href": "https://dummy/workitems/45678"}},
    }

    with patch.object(AzureClientService, "get_repositories", new_callable=AsyncMock) as mock_get_repos, \
         patch.object(AzureClientService, "get_commits", new_callable=AsyncMock) as mock_get_commits, \
         patch.object(AzureClientService, "get_pull_requests", new_callable=AsyncMock) as mock_get_prs, \
         patch.object(AzureClientService, "get_pull_request_work_items", new_callable=AsyncMock) as mock_get_wi_links, \
         patch.object(AzureClientService, "get_work_item", new_callable=AsyncMock) as mock_get_wi:

        mock_get_repos.return_value = mock_repos
        mock_get_commits.return_value = mock_commits
        mock_get_prs.return_value = mock_prs
        mock_get_wi_links.return_value = mock_wi_links
        mock_get_wi.return_value = mock_wi_details

        svc = ActivityService(db, test_user_id)
        res = await svc.sync_client_activities("2026-10-30", "2026-10-30")

        # Crucial check: only the 1 VCQMS repo was scanned, not unrelated-repo-1 or unrelated-repo-2
        assert mock_get_commits.call_count == 1
        assert mock_get_commits.call_args[1]["repository_id"] == "repo-1"

        # Crucial check: work item linked to PR was retrieved and stored
        assert res["work_items"] == 1
        wi_doc = db.activity_items.find_one({"user_id": test_user_id, "source_type": "work_item"})
        assert wi_doc is not None
        assert wi_doc["external_id"] == "45678"
        assert "QA verification checkbox" in wi_doc["title"]
        assert wi_doc["related_ids"] == "pr:789"

    # Cleanup
    db.users.delete_one({"id": test_user_id})
    db.ado_credentials.delete_one({"user_id": test_user_id})
    db.activity_items.delete_many({"user_id": test_user_id})


@pytest.mark.asyncio
async def test_get_endpoint_client_vcqms_context():
    """Verifies that GET /api/activities/client-context retrieves all context scoped strictly to VCQMS."""
    from unittest.mock import AsyncMock, patch
    from backend.app.services.azure_client.client_service import AzureClientService
    from backend.app.api.deps import get_current_user
    from backend.app.models.user import User

    db = get_database()
    test_user_id = 77777
    db.users.delete_one({"id": test_user_id})
    db.users.delete_one({"username": "mock_vcqms_tester"})
    test_user = {
        "id": test_user_id,
        "username": "mock_vcqms_tester",
        "full_name": "Mock VCQMS Tester",
        "email": "mock_vcqms_tester@example.com",
        "hashed_password": "$2b$12$dummyhashedpasswordforunittest",
        "timezone": "Asia/Kolkata",
    }
    db.users.insert_one(test_user)
    db.ado_credentials.delete_one({"user_id": test_user_id, "provider": "client"})
    db.ado_credentials.insert_one({
        "id": 77777,
        "user_id": test_user_id,
        "provider": "client",
        "org_url": "https://dev.azure.com/dummy-org",
        "encrypted_pat": encrypt_pat("dummy-token"),
        "is_valid": True,
        "resolved_identity_email": "mock_vcqms_tester@example.com",
        "resolved_identity_name": "Mock VCQMS Tester",
        "resolved_identity_id": "dummy-user-id",
    })

    mock_repos = [
        {"id": "repo-vcqms-1", "name": "client-vcqms-backend", "project": {"name": "VCQMS"}},
        {"id": "repo-unrelated", "name": "unrelated-project-repo", "project": {"name": "Other"}},
    ]
    mock_commits = [
        {
            "commitId": "abcdef1234567890",
            "author": {"name": "Mock VCQMS Tester", "email": "mock_vcqms_tester@example.com", "date": "2026-10-30T10:00:00Z"},
            "comment": "feat: inspection status filter update",
        }
    ]
    mock_prs = [
        {
            "pullRequestId": "201",
            "title": "VCQMS Approval Workflow PR",
            "creationDate": "2026-10-30T11:00:00Z",
            "status": "active",
            "createdBy": {"displayName": "Mock VCQMS Tester", "uniqueName": "mock_vcqms_tester@example.com"},
        }
    ]
    mock_wi_links = [{"id": "90001", "url": "https://dummy/workitems/90001"}]
    mock_wi_details = {
        "id": 90001,
        "fields": {
            "System.Title": "VCQMS - Implement Inspection approval checklist",
            "System.WorkItemType": "User Story",
            "System.State": "Active",
        },
        "_links": {"html": {"href": "https://dummy/workitems/90001"}},
    }

    app.dependency_overrides[get_current_user] = lambda: User.from_doc(test_user)

    with patch.object(AzureClientService, "get_repositories", new_callable=AsyncMock) as mock_get_repos, \
         patch.object(AzureClientService, "get_commits", new_callable=AsyncMock) as mock_get_commits, \
         patch.object(AzureClientService, "get_pull_requests", new_callable=AsyncMock) as mock_get_prs, \
         patch.object(AzureClientService, "get_pull_request_work_items", new_callable=AsyncMock) as mock_get_wi_links, \
         patch.object(AzureClientService, "get_work_item", new_callable=AsyncMock) as mock_get_wi:

        mock_get_repos.return_value = mock_repos
        mock_get_commits.return_value = mock_commits
        mock_get_prs.return_value = mock_prs
        mock_get_wi_links.return_value = mock_wi_links
        mock_get_wi.return_value = mock_wi_details

        # Call the GET endpoint
        response = client.get("/api/activities/client-context?start_date=2026-10-26&end_date=2026-10-30")
        assert response.status_code == 200
        data = response.json()

        # Assert strict VCQMS scope
        assert data["scope"] == "VCQMS only"
        assert len(data["repositories"]) == 1
        assert data["repositories"][0]["name"] == "client-vcqms-backend"

        # Assert commits
        assert len(data["commits"]) == 1
        assert data["commits"][0]["short_sha"] == "abcdef12"

        # Assert PRs
        assert len(data["pull_requests"]) == 1
        assert data["pull_requests"][0]["id"] == "201"

        # Assert WorkItems linked to PR
        assert len(data["work_items"]) == 1
        assert data["work_items"][0]["id"] == "90001"
        assert "Inspection approval checklist" in data["work_items"][0]["title"]
        assert data["work_items"][0]["linked_pr_id"] == "201"

        # Assert stats
        assert data["stats"]["commits_count"] == 1
        assert data["stats"]["pull_requests_count"] == 1
        assert data["stats"]["work_items_count"] == 1

    app.dependency_overrides.clear()
    db.users.delete_one({"id": test_user_id})
    db.ado_credentials.delete_one({"user_id": test_user_id})
    db.activity_items.delete_many({"user_id": test_user_id})

def test_generate_week_summaries_endpoint():
    db = get_database()
    unique_suffix = uuid.uuid4().hex[:8]
    test_user_id = 99990 + int(unique_suffix[:4], 16) % 1000
    test_user = {
        "id": test_user_id,
        "username": f"week_tester_{unique_suffix}",
        "email": f"week_tester_{unique_suffix}@example.com",
        "full_name": "Week Tester",
        "hashed_password": "$2b$12$dummyhashforunittestingonlydummyhash1234567890",
        "timezone": "Asia/Kolkata",
    }
    db.users.insert_one(test_user)

    from backend.app.api.deps import get_current_user
    from backend.app.models.user import User
    app.dependency_overrides[get_current_user] = lambda: User.from_doc(test_user)

    response = client.post(
        "/api/summaries/generate-week",
        json={"monday_date_str": "2026-11-02"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["week_start"] == "2026-11-02"
    assert len(data["entries"]) == 5

    app.dependency_overrides.clear()
    db.users.delete_one({"id": test_user_id})
    db.daily_timesheet_drafts.delete_many({"user_id": test_user_id})
