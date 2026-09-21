# Ayni Collection System - Backend API

FastAPI backend for the Ayni qualitative data collection system. Provides async PostgreSQL database access, form management, user authentication, and role-based access control.

## Architecture Overview

```
backend/
├── main.py              # FastAPI application & routes
├── database.py          # Async PostgreSQL connection pool
├── auth.py              # JWT auth & password hashing
├── schema.py            # Pydantic models
├── forms_service.py     # Form business logic
├── migrations.py        # Database schema initialization
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Key Components

### Database (`database.py`)
- **Connection Pooling**: asyncpg connection pool for efficient concurrent access
- **Helper Functions**: `fetch()`, `fetchrow()`, `fetchval()`, `execute()` for safe parameterized queries

### Authentication (`auth.py`)
- **Password Hashing**: PBKDF2-SHA256 with salt
- **JWT Tokens**: Token generation and validation
- **User Management**: Create, authenticate, and retrieve users
- **Role Checking**: Admin verification

### Forms Service (`forms_service.py`)
- **CRUD Operations**: Create, read, update, delete form submissions
- **User Scoping**: All queries scoped to current user ID
- **Team Access**: Non-admins see only other users' submitted forms
- **Statistics**: Aggregated submission counts and status breakdowns

### Schema (`schema.py`)
- **Pydantic Models**: Type-safe data validation for all forms
- **Form Types**: ETN (Ethnographic), OBS (Observation), REC (Records), MEM (Memos)

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your DATABASE_URL and SECRET_KEY
```

### 3. Initialize Database Schema
```bash
python migrations.py
```

### 4. Run the Server
```bash
python main.py
```

Server runs on `http://localhost:8000` by default.

## Database Schema

### Users Table
- `id` (TEXT PRIMARY KEY)
- `email` (VARCHAR UNIQUE)
- `name` (VARCHAR)
- `password_hash` (VARCHAR)
- `role` (VARCHAR): 'admin' or 'collector'
- `is_active` (BOOLEAN)
- Timestamps

### Form Submissions Table
- `id` (TEXT PRIMARY KEY)
- `user_id` (FK to users)
- `form_type` (VARCHAR): ETN, OBS, REC, MEM
- `form_code` (VARCHAR UNIQUE): Auto-generated (ETN-001, etc.)
- `data` (JSONB): Form data
- `status` (VARCHAR): 'draft', 'submitted', 'synced'
- Timestamps

### Type-Specific Tables
- `ethnographic_scenes`: Denormalized data for ETN forms
- `observation_days`: Denormalized data for OBS forms
- `scene_records`: Denormalized data for REC forms
- `analytic_memos`: Denormalized data for MEM forms
- `audit_log`: Admin action tracking

## API Routes

### Authentication
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - Login and get JWT token

### Form Submissions
- `POST /api/forms` - Create form
- `GET /api/forms` - List user's forms
- `GET /api/forms/{id}` - Get specific form
- `PUT /api/forms/{id}` - Update form
- `DELETE /api/forms/{id}` - Delete form
- `POST /api/forms/{id}/submit` - Submit draft
- `POST /api/forms/{id}/sync` - Mark as synced

### Team & Admin
- `GET /api/team/forms` - Get team's submitted forms (read-only)
- `GET /api/statistics` - Get submission statistics

### System
- `GET /api/health` - Health check
- `GET /` - API info

## Security Features

### User Data Protection
- ✅ **Per-user scoping**: Every query filtered by `user_id`
- ✅ **Draft privacy**: Drafts visible only to owner or admin
- ✅ **Read-only team access**: Non-admins see only other users' submitted forms
- ✅ **Password hashing**: PBKDF2-SHA256 with salt

### Query Safety
- ✅ **Parameterized queries**: All SQL uses `$1, $2` syntax (never f-strings)
- ✅ **No SQL injection**: asyncpg handles escaping
- ✅ **JSONB validation**: Pydantic models validate form data

### Access Control
- ✅ **JWT authentication**: All routes require valid token
- ✅ **Role-based**: Admin-only operations protected
- ✅ **Ownership checks**: Users can only modify own resources

## Performance Optimization

- **Connection Pooling**: Reusable connections (min=5, max=20)
- **Async/await**: Non-blocking database calls
- **Database Indices**: Optimized queries on `user_id`, `form_type`, `status`, dates
- **JSONB Indexing**: Fast querying of form data
- **Pagination**: Team forms support limit/offset

## Development

### Reset Database
```bash
# Drop all tables (careful in production!)
psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
python migrations.py
```

### Test API
```bash
# Run with Uvicorn auto-reload
uvicorn backend.main:app --reload
```

Interactive API docs: `http://localhost:8000/docs`

## Deployment

### Environment Variables
Ensure these are set in production:
- `DATABASE_URL`: PostgreSQL connection string (Neon)
- `SECRET_KEY`: Strong random string (≥32 characters)
- `PORT`: Server port (default: 8000)
- `NODE_ENV`: "production" for deployment

### CORS Configuration
Update `allow_origins` in `main.py` for production domains.

### Database Backups
Set up automated backups through your Neon dashboard.

## Troubleshooting

### Connection Pool Exhausted
- Increase `max_size` in `database.py`
- Check for unclosed connections in application code

### Token Expired
- Tokens expire after 24 hours by default
- Client must re-authenticate and request new token

### Form Not Found
- Verify user owns the form or is admin
- Check `user_id` matches in request

## Future Enhancements

- [ ] Offline mode with sync queue
- [ ] Real-time collaboration (WebSocket)
- [ ] Image upload to cloud storage
- [ ] Advanced filtering/search
- [ ] Batch export (CSV/JSON)
- [ ] Webhook integrations
- [ ] Rate limiting per user
- [ ] Form versioning
