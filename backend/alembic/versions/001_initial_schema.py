"""Initial schema for Ayni collection system

Revision ID: 001
Revises: 
Create Date: 2026-09-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('email', sa.VARCHAR(255), unique=True, nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('password_hash', sa.VARCHAR(255), nullable=False),
        sa.Column('role', sa.VARCHAR(50), nullable=False, server_default='collector'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('is_active', sa.BOOLEAN, server_default=sa.true()),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Form submissions table
    op.create_table(
        'form_submissions',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('user_id', sa.TEXT, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('form_type', sa.VARCHAR(10), nullable=False),
        sa.Column('form_code', sa.VARCHAR(50), unique=True, nullable=False),
        sa.Column('data', sa.JSON, nullable=False),
        sa.Column('status', sa.VARCHAR(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('submitted_at', sa.TIMESTAMP),
        sa.Column('synced_at', sa.TIMESTAMP),
    )
    op.create_index('ix_submissions_user_id', 'form_submissions', ['user_id'])
    op.create_index('ix_submissions_form_type', 'form_submissions', ['form_type'])
    op.create_index('ix_submissions_status', 'form_submissions', ['status'])
    op.create_index('ix_submissions_created_at', 'form_submissions', ['created_at'])
    
    # Ethnographic scenes table
    op.create_table(
        'ethnographic_scenes',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('submission_id', sa.TEXT, sa.ForeignKey('form_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.TEXT, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.DATE, nullable=False),
        sa.Column('time_start', sa.TIME),
        sa.Column('place', sa.VARCHAR(500)),
        sa.Column('people', sa.TEXT),
        sa.Column('context', sa.TEXT),
        sa.Column('researcher_position', sa.TEXT),
        sa.Column('reflexivity', sa.TEXT),
        sa.Column('initial_impressions', sa.TEXT),
        sa.Column('key_moments', sa.TEXT),
        sa.Column('participant_reactions', sa.TEXT),
        sa.Column('personal_notes', sa.TEXT),
        sa.Column('image_url', sa.TEXT),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )
    op.create_index('ix_ethnographic_user_id', 'ethnographic_scenes', ['user_id'])
    op.create_index('ix_ethnographic_date', 'ethnographic_scenes', ['date'])
    
    # Observation days table
    op.create_table(
        'observation_days',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('submission_id', sa.TEXT, sa.ForeignKey('form_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.TEXT, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.DATE, nullable=False),
        sa.Column('time_start', sa.TIME),
        sa.Column('time_end', sa.TIME),
        sa.Column('place', sa.VARCHAR(500)),
        sa.Column('position', sa.VARCHAR(500)),
        sa.Column('main_activity', sa.TEXT),
        sa.Column('participants', sa.TEXT),
        sa.Column('interruptions', sa.TEXT),
        sa.Column('image_url', sa.TEXT),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )
    op.create_index('ix_observation_user_id', 'observation_days', ['user_id'])
    op.create_index('ix_observation_date', 'observation_days', ['date'])
    
    # Scene records table
    op.create_table(
        'scene_records',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('submission_id', sa.TEXT, sa.ForeignKey('form_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.TEXT, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.DATE, nullable=False),
        sa.Column('dense_description', sa.TEXT, nullable=False),
        sa.Column('exact_phrases', sa.TEXT),
        sa.Column('interpretations', sa.TEXT),
        sa.Column('preliminary_codes', sa.TEXT),
        sa.Column('image_url', sa.TEXT),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )
    op.create_index('ix_scene_records_user_id', 'scene_records', ['user_id'])
    op.create_index('ix_scene_records_date', 'scene_records', ['date'])
    
    # Analytic memos table
    op.create_table(
        'analytic_memos',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('submission_id', sa.TEXT, sa.ForeignKey('form_submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.TEXT, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.DATE, nullable=False),
        sa.Column('main_findings', sa.TEXT, nullable=False),
        sa.Column('emergent_questions', sa.TEXT, nullable=False),
        sa.Column('connections', sa.TEXT),
        sa.Column('next_steps', sa.TEXT),
        sa.Column('conceptual_insights', sa.TEXT),
        sa.Column('methodological_notes', sa.TEXT),
        sa.Column('reflexivity', sa.TEXT),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )
    op.create_index('ix_memos_user_id', 'analytic_memos', ['user_id'])
    op.create_index('ix_memos_date', 'analytic_memos', ['date'])
    
    # Audit log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.TEXT, primary_key=True),
        sa.Column('admin_id', sa.TEXT, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.VARCHAR(100), nullable=False),
        sa.Column('resource_type', sa.VARCHAR(100)),
        sa.Column('resource_id', sa.TEXT),
        sa.Column('old_values', sa.JSON),
        sa.Column('new_values', sa.JSON),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
    )
    op.create_index('ix_audit_log_admin_id', 'audit_log', ['admin_id'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('audit_log')
    op.drop_table('analytic_memos')
    op.drop_table('scene_records')
    op.drop_table('observation_days')
    op.drop_table('ethnographic_scenes')
    op.drop_table('form_submissions')
    op.drop_table('users')
