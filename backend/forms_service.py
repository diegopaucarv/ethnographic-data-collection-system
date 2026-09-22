"""Service layer for form submissions."""
import uuid
import json
from datetime import datetime
from typing import Optional
from database import execute, fetch, fetchrow, fetchval
from auth import is_admin


async def create_form_submission(
    user_id: str,
    form_type: str,
    data: dict,
    status: str = "draft",
    client_id: Optional[str] = None,
) -> dict:
    """Create a submission once per client-generated identity."""
    submission_id = str(uuid.uuid4())

    # The counter update is atomic. The client-id unique index below makes the
    # final insert the idempotency authority when two retries race.
    sequence_number = await fetchval(
        """
        INSERT INTO form_code_counters (form_type, next_number)
        VALUES ($1, 2)
        ON CONFLICT (form_type)
        DO UPDATE SET next_number = form_code_counters.next_number + 1
        RETURNING next_number - 1
        """,
        form_type,
    )
    form_code = f"{form_type}-{int(sequence_number):03d}"

    result = await fetchrow(
        """
        INSERT INTO form_submissions
          (id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, client_id) WHERE client_id IS NOT NULL DO NOTHING
        RETURNING id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
        """,
        submission_id,
        user_id,
        form_type,
        form_code,
        json.dumps(data),
        status,
        client_id,
    )

    if result is None:
        result = await fetchrow(
            """
            SELECT id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
            FROM form_submissions
            WHERE user_id = $1 AND client_id = $2
            """,
            user_id,
            client_id,
        )

    if result is None:
        raise RuntimeError("Submission insert lost its idempotency result")
    result["data"] = json.loads(result["data"])
    return result


async def get_form_submission(submission_id: str) -> Optional[dict]:
    """Get a form submission by ID."""
    result = await fetchrow(
        """
        SELECT id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
        FROM form_submissions
        WHERE id = $1
        """,
        submission_id
    )
    
    if result:
        result["data"] = json.loads(result["data"])
    return result


async def update_form_submission(
    submission_id: str,
    user_id: str,
    data: Optional[dict] = None,
    status: Optional[str] = None
) -> Optional[dict]:
    """Update a form submission (user can only update own drafts)."""
    
    # Check ownership
    submission = await get_form_submission(submission_id)
    if not submission:
        return None
    
    admin = await is_admin(user_id)
    if submission["user_id"] != user_id:
        # Only admins can update another collector's record.
        if not admin:
            return None
    elif submission["status"] != "draft" and not admin:
        # Collectors may edit only their own drafts; submitted records are immutable.
        return None
    
    updates = []
    params = [submission_id]
    param_index = 2
    
    if data is not None:
        updates.append(f"data = ${param_index}")
        params.append(json.dumps(data))
        param_index += 1
    
    if status is not None:
        allowed_transitions = {
            "draft": {"draft", "submitted"},
            "submitted": {"submitted", "synced"},
            "synced": {"synced"},
        }
        if status not in allowed_transitions.get(submission["status"], set()):
            return None
        if submission["status"] == "submitted" and status == "synced" and not admin:
            return None
        if submission["status"] == "submitted" and status == "draft" and not admin:
            return None
        updates.append(f"status = ${param_index}")
        params.append(status)
        param_index += 1

        if status == "submitted":
            updates.append("submitted_at = CURRENT_TIMESTAMP")
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    query = f"""
    UPDATE form_submissions
    SET {', '.join(updates)}
    WHERE id = $1
    RETURNING id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
    """
    
    result = await fetchrow(query, *params)
    if result:
        result["data"] = json.loads(result["data"])
    return result


async def get_user_submissions(user_id: str, form_type: Optional[str] = None) -> list[dict]:
    """Get all submissions for a user."""
    if form_type:
        query = """
        SELECT id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
        FROM form_submissions
        WHERE user_id = $1 AND form_type = $2
        ORDER BY created_at DESC
        """
        results = await fetch(query, user_id, form_type)
    else:
        query = """
        SELECT id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
        FROM form_submissions
        WHERE user_id = $1
        ORDER BY created_at DESC
        """
        results = await fetch(query, user_id)
    
    for result in results:
        result["data"] = json.loads(result["data"])
    return results


async def get_team_submissions(requester_id: str, limit: int = 100, offset: int = 0) -> dict:
    """Get all submitted forms from the team (read-only access for non-admins)."""
    # Check if requester is admin
    admin = await is_admin(requester_id)
    
    if admin:
        # Admins see all forms
        query = """
        SELECT id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
        FROM form_submissions
        WHERE status IN ('submitted', 'synced')
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """
        results = await fetch(query, limit, offset)
        
        total_query = """
        SELECT COUNT(*) FROM form_submissions
        WHERE status IN ('submitted', 'synced')
        """
        total = await fetchval(total_query)
    else:
        # Non-admins see only other users' submitted forms (not their own)
        query = """
        SELECT id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
        FROM form_submissions
        WHERE status IN ('submitted', 'synced') AND user_id != $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """
        results = await fetch(query, requester_id, limit, offset)
        
        total_query = """
        SELECT COUNT(*) FROM form_submissions
        WHERE status IN ('submitted', 'synced') AND user_id != $1
        """
        total = await fetchval(total_query, requester_id)
    
    for result in results:
        result["data"] = json.loads(result["data"])
    
    return {
        "forms": results,
        "total": total,
        "limit": limit,
        "offset": offset
    }


async def delete_form_submission(submission_id: str, user_id: str) -> bool:
    """Delete a form submission (admin only or owner of draft)."""
    submission = await get_form_submission(submission_id)
    
    if not submission:
        return False
    
    # Check if admin or owner of draft
    if not await is_admin(user_id) and (submission["user_id"] != user_id or submission["status"] != "draft"):
        return False
    
    await execute("DELETE FROM form_submissions WHERE id = $1", submission_id)
    return True


async def sync_form(submission_id: str, user_id: str) -> Optional[dict]:
    """Mark a form as synced (submitted -> synced transition)."""
    submission = await get_form_submission(submission_id)
    
    if not submission:
        return None
    
    # Only submitted records can be synced, and only by their owner or an admin.
    if submission["user_id"] != user_id and not await is_admin(user_id):
        return None
    if submission["status"] != "submitted":
        return None

    query = """
    UPDATE form_submissions
    SET status = 'synced', synced_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
    WHERE id = $1
    RETURNING id, user_id, form_type, form_code, data, status, client_id, created_at, updated_at, submitted_at
    """
    
    result = await fetchrow(query, submission_id)
    if result:
        result["data"] = json.loads(result["data"])
    return result


async def get_statistics(user_id: str) -> dict:
    """Get form submission statistics."""
    admin = await is_admin(user_id)
    
    if admin:
        # Admin sees all statistics
        user_count = await fetchval("SELECT COUNT(*) FROM users WHERE role = 'collector'")
        total_submissions = await fetchval("SELECT COUNT(*) FROM form_submissions")
        submitted_count = await fetchval(
            "SELECT COUNT(*) FROM form_submissions WHERE status IN ('submitted', 'synced')"
        )
        draft_count = await fetchval(
            "SELECT COUNT(*) FROM form_submissions WHERE status = 'draft'"
        )
        
        by_form_type = await fetch("""
            SELECT form_type, COUNT(*) as count, status
            FROM form_submissions
            GROUP BY form_type, status
            ORDER BY form_type
        """)
    else:
        # User sees only their own statistics
        user_count = None
        total_submissions = await fetchval(
            "SELECT COUNT(*) FROM form_submissions WHERE user_id = $1",
            user_id
        )
        submitted_count = await fetchval(
            "SELECT COUNT(*) FROM form_submissions WHERE user_id = $1 AND status IN ('submitted', 'synced')",
            user_id
        )
        draft_count = await fetchval(
            "SELECT COUNT(*) FROM form_submissions WHERE user_id = $1 AND status = 'draft'",
            user_id
        )
        by_form_type = await fetch("""
            SELECT form_type, COUNT(*) as count, status
            FROM form_submissions
            WHERE user_id = $1
            GROUP BY form_type, status
            ORDER BY form_type
        """, user_id)
    
    return {
        "user_count": user_count,
        "total_submissions": total_submissions,
        "submitted_count": submitted_count,
        "draft_count": draft_count,
        "by_form_type": by_form_type
    }
