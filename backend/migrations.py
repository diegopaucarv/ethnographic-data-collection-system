"""Database schema initialization for Ayni collection system."""
import asyncio
from database import get_pool, close_pool


async def create_schema():
    """Create all required database tables."""
    
    queries = [
        # Users table
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'collector',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
        """,
        
        # Form submissions - main table
        """
        CREATE TABLE IF NOT EXISTS form_submissions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            form_type VARCHAR(10) NOT NULL,
            form_code VARCHAR(50) UNIQUE NOT NULL,
            data JSONB NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            synced_at TIMESTAMP
        )
        """,
        
        # Ethnographic scene records
        """
        CREATE TABLE IF NOT EXISTS ethnographic_scenes (
            id TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL REFERENCES form_submissions(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            time_start TIME,
            place VARCHAR(500),
            people TEXT,
            context TEXT,
            researcher_position TEXT,
            reflexivity TEXT,
            initial_impressions TEXT,
            key_moments TEXT,
            participant_reactions TEXT,
            personal_notes TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Observation day records
        """
        CREATE TABLE IF NOT EXISTS observation_days (
            id TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL REFERENCES form_submissions(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            time_start TIME,
            time_end TIME,
            place VARCHAR(500),
            position VARCHAR(500),
            main_activity TEXT,
            participants TEXT,
            interruptions TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Scene records
        """
        CREATE TABLE IF NOT EXISTS scene_records (
            id TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL REFERENCES form_submissions(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            dense_description TEXT NOT NULL,
            exact_phrases TEXT,
            interpretations TEXT,
            preliminary_codes TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Analytic memos
        """
        CREATE TABLE IF NOT EXISTS analytic_memos (
            id TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL REFERENCES form_submissions(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            main_findings TEXT NOT NULL,
            emergent_questions TEXT NOT NULL,
            connections TEXT,
            next_steps TEXT,
            conceptual_insights TEXT,
            methodological_notes TEXT,
            reflexivity TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Audit log for admin actions
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            admin_id TEXT NOT NULL REFERENCES users(id),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100),
            resource_id TEXT,
            old_values JSONB,
            new_values JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Create indices for performance
        "CREATE INDEX IF NOT EXISTS idx_submissions_user_id ON form_submissions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_submissions_form_type ON form_submissions(form_type)",
        "CREATE INDEX IF NOT EXISTS idx_submissions_status ON form_submissions(status)",
        "CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON form_submissions(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ethnographic_user_id ON ethnographic_scenes(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_ethnographic_date ON ethnographic_scenes(date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_observation_user_id ON observation_days(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_observation_date ON observation_days(date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_scene_records_user_id ON scene_records(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_scene_records_date ON scene_records(date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_memos_user_id ON analytic_memos(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_memos_date ON analytic_memos(date DESC)",
    ]
    
    p = await get_pool()
    
    for query in queries:
        try:
            await p.execute(query)
            print(f"✓ Executed: {query.split()[0:3]}")
        except Exception as e:
            print(f"⚠ Error: {e}")


async def main():
    """Run migrations."""
    try:
        print("Starting database schema creation...")
        await create_schema()
        print("Schema creation completed successfully!")
    except Exception as e:
        print(f"Error during schema creation: {e}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
