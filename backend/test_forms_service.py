"""Integration and concurrency tests for form submission service."""
import pytest
import pytest_asyncio
import asyncio
import json
from uuid import uuid4
from forms_service import (
    create_form_submission,
    get_form_submission,
    update_form_submission,
    get_user_submissions,
    delete_form_submission,
    sync_form,
)
from auth import create_user
from database import execute, get_pool, fetchval
import os

# Test user fixtures
TEST_USER_EMAIL = "test.collector@example.com"
TEST_USER_PASSWORD = "TestPassword123!"
TEST_ADMIN_EMAIL = "test.admin@example.com"
TEST_ADMIN_PASSWORD = "AdminPassword123!"


@pytest_asyncio.fixture
async def test_user():
    """Create an isolated test collector user."""
    await execute("DELETE FROM users WHERE email = $1", TEST_USER_EMAIL)
    user = await create_user(
        email=TEST_USER_EMAIL,
        name="Test Collector",
        password=TEST_USER_PASSWORD,
        role="collector"
    )
    yield user
    # Cleanup: delete user after test
    await execute("DELETE FROM users WHERE id = $1", user["id"])


@pytest_asyncio.fixture
async def test_admin():
    """Create a test admin user."""
    admin = await create_user(
        email=TEST_ADMIN_EMAIL,
        name="Test Admin",
        password=TEST_ADMIN_PASSWORD,
        role="admin"
    )
    yield admin
    # Cleanup
    await execute("DELETE FROM users WHERE id = $1", admin["id"])


@pytest_asyncio.fixture
async def cleanup_submissions():
    """Cleanup submissions after each test."""
    yield
    await execute("DELETE FROM form_submissions")


@pytest.mark.asyncio
async def test_create_form_submission_basic(test_user, cleanup_submissions):
    """Test basic form submission creation."""
    data = {
        "date": "2024-09-22",
        "place": "Test Location",
        "context": "Test context",
    }
    
    result = await create_form_submission(
        user_id=test_user["id"],
        form_type="ENT",
        data=data,
        status="draft",
        client_id="client-1"
    )
    
    assert result["id"] is not None
    assert result["user_id"] == test_user["id"]
    assert result["form_type"] == "ENT"
    assert result["form_code"].startswith("ENT-")
    assert result["data"] == data
    assert result["status"] == "draft"
    assert result["client_id"] == "client-1"


@pytest.mark.asyncio
async def test_idempotency_same_client_id(test_user, cleanup_submissions):
    """Test that same client_id returns the same submission."""
    data1 = {"date": "2024-09-22", "place": "Location A"}
    data2 = {"date": "2024-09-23", "place": "Location B"}
    client_id = "client-idempotent-1"
    
    result1 = await create_form_submission(
        user_id=test_user["id"],
        form_type="OBS",
        data=data1,
        client_id=client_id
    )
    
    result2 = await create_form_submission(
        user_id=test_user["id"],
        form_type="OBS",
        data=data2,
        client_id=client_id
    )
    
    assert result1["id"] == result2["id"]
    assert result1["form_code"] == result2["form_code"]
    assert result1["data"] == data1


@pytest.mark.asyncio
async def test_concurrent_form_code_generation(test_user, cleanup_submissions):
    """Test concurrent form code generation produces unique codes."""
    async def create_submission(index):
        return await create_form_submission(
            user_id=test_user["id"],
            form_type="REC",
            data={"index": index},
            client_id=f"concurrent-{index}"
        )
    
    tasks = [create_submission(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    form_codes = [r["form_code"] for r in results]
    assert len(form_codes) == len(set(form_codes)), "Form codes must be unique"
    
    for i, code in enumerate(sorted(form_codes)):
        expected = f"REC-{i+1:03d}"
        assert code == expected, f"Expected {expected}, got {code}"


@pytest.mark.asyncio
async def test_get_form_submission(test_user, cleanup_submissions):
    """Test retrieving a form submission."""
    data = {"test": "data"}
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="MEM",
        data=data,
        client_id="get-test"
    )
    
    retrieved = await get_form_submission(created["id"])
    assert retrieved is not None
    assert retrieved["id"] == created["id"]
    assert retrieved["data"] == data


@pytest.mark.asyncio
async def test_update_form_submission_draft_status(test_user, cleanup_submissions):
    """Test updating a draft submission status."""
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="ENT",
        data={"test": "data"},
        status="draft",
        client_id="update-test"
    )
    
    updated = await update_form_submission(
        submission_id=created["id"],
        user_id=test_user["id"],
        status="submitted"
    )
    
    assert updated is not None
    assert updated["status"] == "submitted"
    assert updated["submitted_at"] is not None


@pytest.mark.asyncio
async def test_cannot_update_submitted_without_admin(test_user, cleanup_submissions):
    """Test that non-admin cannot move submitted->draft."""
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="OBS",
        data={"test": "data"},
        status="draft",
        client_id="immutable-test"
    )
    
    submitted = await update_form_submission(
        submission_id=created["id"],
        user_id=test_user["id"],
        status="submitted"
    )
    assert submitted is not None
    
    result = await update_form_submission(
        submission_id=created["id"],
        user_id=test_user["id"],
        status="draft"
    )
    assert result is None


@pytest.mark.asyncio
async def test_admin_can_update_submitted(test_admin, test_user, cleanup_submissions):
    """Test that admin can move submitted->draft."""
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="REC",
        data={"test": "data"},
        status="draft",
        client_id="admin-update"
    )
    
    submitted = await update_form_submission(
        submission_id=created["id"],
        user_id=test_user["id"],
        status="submitted"
    )
    assert submitted is not None
    
    result = await update_form_submission(
        submission_id=created["id"],
        user_id=test_admin["id"],
        status="draft"
    )
    assert result is not None
    assert result["status"] == "draft"


@pytest.mark.asyncio
async def test_sync_form_transition(test_user, cleanup_submissions):
    """Test syncing a submitted form."""
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="MEM",
        data={"test": "data"},
        status="draft",
        client_id="sync-test"
    )
    
    submitted = await update_form_submission(
        submission_id=created["id"],
        user_id=test_user["id"],
        status="submitted"
    )
    
    synced = await sync_form(created["id"], test_user["id"])
    assert synced is not None
    assert synced["status"] == "synced"


@pytest.mark.asyncio
async def test_get_user_submissions(test_user, cleanup_submissions):
    """Test retrieving all submissions for a user."""
    client_ids = [f"user-list-{i}" for i in range(3)]
    for i, client_id in enumerate(client_ids):
        await create_form_submission(
            user_id=test_user["id"],
            form_type="ENT" if i % 2 == 0 else "OBS",
            data={"index": i},
            client_id=client_id
        )
    
    submissions = await get_user_submissions(test_user["id"])
    assert len(submissions) == 3
    
    ent_submissions = await get_user_submissions(test_user["id"], form_type="ENT")
    assert len(ent_submissions) == 2


@pytest.mark.asyncio
async def test_delete_form_submission_only_draft(test_user, cleanup_submissions):
    """Test that only draft submissions can be deleted by non-admin."""
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="REC",
        data={"test": "data"},
        status="draft",
        client_id="delete-test"
    )
    
    deleted = await delete_form_submission(created["id"], test_user["id"])
    assert deleted is True
    
    retrieved = await get_form_submission(created["id"])
    assert retrieved is None


@pytest.mark.asyncio
async def test_cannot_delete_submitted_without_admin(test_user, cleanup_submissions):
    """Test that non-admin cannot delete submitted submissions."""
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="MEM",
        data={"test": "data"},
        status="draft",
        client_id="delete-protect"
    )
    
    submitted = await update_form_submission(
        submission_id=created["id"],
        user_id=test_user["id"],
        status="submitted"
    )
    
    deleted = await delete_form_submission(created["id"], test_user["id"])
    assert deleted is False


@pytest.mark.asyncio
async def test_form_code_counter_persistence(test_user, cleanup_submissions):
    """Test that form code counters persist across requests."""
    ids1 = []
    for i in range(5):
        result = await create_form_submission(
            user_id=test_user["id"],
            form_type="ENT",
            data={"batch": 1, "index": i},
            client_id=f"persist-1-{i}"
        )
        ids1.append(result["form_code"])
    
    ids2 = []
    for i in range(5):
        result = await create_form_submission(
            user_id=test_user["id"],
            form_type="ENT",
            data={"batch": 2, "index": i},
            client_id=f"persist-2-{i}"
        )
        ids2.append(result["form_code"])
    
    all_codes = ids1 + ids2
    assert all_codes == [f"ENT-{i+1:03d}" for i in range(10)]


@pytest.mark.asyncio
async def test_status_state_machine(test_user, cleanup_submissions):
    """Test valid state transitions in the form status machine."""
    created = await create_form_submission(
        user_id=test_user["id"],
        form_type="OBS",
        data={"test": "data"},
        status="draft",
        client_id="state-test"
    )
    
    allowed_transitions = {
        "draft": ["draft", "submitted"],
        "submitted": ["submitted", "synced"],
        "synced": ["synced"],
    }
    
    current_status = "draft"
    for next_status in allowed_transitions[current_status]:
        result = await update_form_submission(
            submission_id=created["id"],
            user_id=test_user["id"],
            status=next_status
        )
        assert result is not None
        assert result["status"] == next_status
        current_status = next_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
