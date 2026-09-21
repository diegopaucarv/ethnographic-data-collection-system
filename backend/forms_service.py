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
    status: str = "draft"
) -> dict:
    """Create a new form submission."""
    submission_id = str(uuid.uuid4())
    
    # Generate form code (ETN-001, OBS-002, etc.)
    last_code_num = await fetchval(
        """
        SELECT COALESCE(MAX(CAST(SUBSTRING(form_code FROM LENGTH($1) + 2) AS INTEGER)), 0)
        FROM form_submissions
        WHERE form_type = $1
        """,
        form_type
    )
    form_code = f"{form_type}-{str(last_code_num + 1).zfill(3)}"
    
    query = """
    INSERT INTO form_submissions 
    (id, user_id, form_type, form_code, data, status, created_at, updated_at)
    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    RETURNING id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
    """
    
    result = await fetchrow(
        query,
        submission_id,
        user_id,
        form_type,
        form_code,
        json.dumps(data),
        status
    )
    
    result["data"] = json.loads(result["data"])
    return result


async def get_form_submission(submission_id: str) -> Optional[dict]:
    """Get a form submission by ID."""
    result = await fetchrow(
        """
        SELECT id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
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
    
    if submission["user_id"] != user_id:
        # Only admins can update other users' submissions
        if not await is_admin(user_id):
            return None
    
    updates = []
    params = [submission_id]
    param_index = 2
    
    if data is not None:
        updates.append(f"data = ${param_index}")
        params.append(json.dumps(data))
        param_index += 1
    
    if status is not None:
        updates.append(f"status = ${param_index}")
        params.append(status)
        param_index += 1
        
        # If submitting, set submitted_at
        if status == "submitted":
            updates.append(f"submitted_at = CURRENT_TIMESTAMP")
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    query = f"""
    UPDATE form_submissions
    SET {', '.join(updates)}
    WHERE id = $1
    RETURNING id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
    """
    
    result = await fetchrow(query, *params)
    if result:
        result["data"] = json.loads(result["data"])
    return result


async def get_user_submissions(user_id: str, form_type: Optional[str] = None) -> list[dict]:
    """Get all submissions for a user."""
    if form_type:
        query = """
        SELECT id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
        FROM form_submissions
        WHERE user_id = $1 AND form_type = $2
        ORDER BY created_at DESC
        """
        results = await fetch(query, user_id, form_type)
    else:
        query = """
        SELECT id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
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
        SELECT id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
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
        SELECT id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
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
    
    # Only allow syncing own submissions or as admin
    if submission["user_id"] != user_id and not await is_admin(user_id):
        return None
    
    query = """
    UPDATE form_submissions
    SET status = 'synced', synced_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
    WHERE id = $1
    RETURNING id, user_id, form_type, form_code, data, status, created_at, updated_at, submitted_at
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
