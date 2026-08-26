"""initial schema

Creates the full Frontline Prep schema: catalog spine, users, question bank,
assessments, ISSB simulation suite and the content/agent tables.

Enum-valued columns are VARCHAR + CHECK rather than native PG ENUM types, so
adding a value later is a constraint swap instead of an ALTER TYPE that cannot
run inside a transaction on a managed provider.

Revision ID: 0001_initial
Revises:
Created: 2026-08-25
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('announcements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('level', sa.String(length=16), nullable=False),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='announcement_service', native_enum=False, length=32), nullable=True),
    sa.Column('link_url', sa.String(length=400), nullable=True),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_announcements'))
    )
    op.create_table('contact_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=160), nullable=False),
    sa.Column('phone', sa.String(length=24), nullable=True),
    sa.Column('subject', sa.String(length=200), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('handled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contact_messages'))
    )
    op.create_table('gto_tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_type', sa.Enum('group_discussion', 'group_planning', 'progressive_group_task', 'half_group_task', 'individual_obstacles', 'command_task', 'snake_race', 'final_group_task', 'lecturette', name='gto_task_type', native_enum=False, length=32), nullable=False),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='gto_service', native_enum=False, length=32), nullable=True),
    sa.Column('title', sa.String(length=180), nullable=False),
    sa.Column('brief', sa.Text(), nullable=False),
    sa.Column('constraints', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('resources', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('map_url', sa.String(length=400), nullable=True),
    sa.Column('planning_seconds', sa.Integer(), nullable=False),
    sa.Column('execution_seconds', sa.Integer(), nullable=False),
    sa.Column('group_size', sa.SmallInteger(), nullable=False),
    sa.Column('model_solution', sa.Text(), nullable=True),
    sa.Column('rubric', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('target_olqs', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='gto_difficulty', native_enum=False, length=32), nullable=False),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='gto_status', native_enum=False, length=32), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_gto_tasks'))
    )
    op.create_table('services',
    sa.Column('id', sa.SmallInteger(), nullable=False),
    sa.Column('code', sa.Enum('army', 'air_force', 'navy', 'common', name='service_code', native_enum=False, length=32), nullable=False),
    sa.Column('name', sa.String(length=60), nullable=False),
    sa.Column('short_name', sa.String(length=16), nullable=False),
    sa.Column('tagline', sa.String(length=160), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('accent', sa.String(length=16), nullable=False),
    sa.Column('emblem_url', sa.String(length=400), nullable=True),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_services')),
    sa.UniqueConstraint('code', name=op.f('uq_services_code'))
    )
    op.create_table('stages',
    sa.Column('id', sa.SmallInteger(), nullable=False),
    sa.Column('code', sa.Enum('registration', 'initial_test', 'physical', 'medical', 'prelim_interview', 'issb_screening', 'issb_psychological', 'issb_gto', 'issb_interview', 'issb_conference', 'final_medical', 'merit', name='stage_code', native_enum=False, length=32), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('icon', sa.String(length=40), nullable=True),
    sa.Column('day_hint', sa.String(length=40), nullable=True),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stages')),
    sa.UniqueConstraint('code', name=op.f('uq_stages_code'))
    )
    op.create_table('modules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('service_id', sa.SmallInteger(), nullable=False),
    sa.Column('stage_id', sa.SmallInteger(), nullable=False),
    sa.Column('slug', sa.String(length=90), nullable=False),
    sa.Column('title', sa.String(length=140), nullable=False),
    sa.Column('subtitle', sa.String(length=200), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('icon', sa.String(length=40), nullable=True),
    sa.Column('default_question_count', sa.SmallInteger(), nullable=False),
    sa.Column('default_duration_min', sa.SmallInteger(), nullable=False),
    sa.Column('approved_question_count', sa.Integer(), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_modules_service_id_services'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stage_id'], ['stages.id'], name=op.f('fk_modules_stage_id_stages'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_modules')),
    sa.UniqueConstraint('service_id', 'slug', name='uq_modules_service_id')
    )
    op.create_table('programs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('service_id', sa.SmallInteger(), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('short_name', sa.String(length=32), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('eligibility', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('physical_standards', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('test_blueprint', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('intake_note', sa.String(length=200), nullable=True),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_programs_service_id_services'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_programs')),
    sa.UniqueConstraint('slug', name=op.f('uq_programs_slug'))
    )
    op.create_table('test_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=90), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('service_id', sa.SmallInteger(), nullable=True),
    sa.Column('stage_id', sa.SmallInteger(), nullable=True),
    sa.Column('program_id', sa.Integer(), nullable=True),
    sa.Column('sections', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('duration_min', sa.SmallInteger(), nullable=False),
    sa.Column('total_questions', sa.SmallInteger(), nullable=False),
    sa.Column('pass_percentage', sa.Float(), nullable=False),
    sa.Column('negative_marking', sa.Float(), nullable=False),
    sa.Column('shuffle_questions', sa.Boolean(), nullable=False),
    sa.Column('shuffle_options', sa.Boolean(), nullable=False),
    sa.Column('show_answers_after', sa.Boolean(), nullable=False),
    sa.Column('is_mock', sa.Boolean(), nullable=False),
    sa.Column('is_free', sa.Boolean(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='template_status', native_enum=False, length=32), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_test_templates_program_id_programs'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_test_templates_service_id_services'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['stage_id'], ['stages.id'], name=op.f('fk_test_templates_stage_id_stages'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_test_templates')),
    sa.UniqueConstraint('slug', name=op.f('uq_test_templates_slug'))
    )
    op.create_table('topics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=90), nullable=False),
    sa.Column('name', sa.String(length=140), nullable=False),
    sa.Column('blurb', sa.String(length=280), nullable=True),
    sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('approved_question_count', sa.Integer(), nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['module_id'], ['modules.id'], name=op.f('fk_topics_module_id_modules'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_topics')),
    sa.UniqueConstraint('module_id', 'slug', name='uq_topics_module_id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=160), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('phone', sa.String(length=24), nullable=True),
    sa.Column('role', sa.Enum('student', 'instructor', 'admin', 'super_admin', name='user_role', native_enum=False, length=32), nullable=False),
    sa.Column('status', sa.Enum('pending', 'active', 'suspended', name='user_status', native_enum=False, length=32), nullable=False),
    sa.Column('target_service', sa.Enum('army', 'air_force', 'navy', 'common', name='user_service', native_enum=False, length=32), nullable=True),
    sa.Column('target_program_id', sa.Integer(), nullable=True),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('gender', sa.String(length=12), nullable=True),
    sa.Column('city', sa.String(length=80), nullable=True),
    sa.Column('avatar_url', sa.String(length=400), nullable=True),
    sa.Column('height_cm', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('weight_kg', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('email_verified', sa.Boolean(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('google_sub', sa.String(length=64), nullable=True),
    sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['target_program_id'], ['programs.id'], name=op.f('fk_users_target_program_id_programs'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('google_sub', name=op.f('uq_users_google_sub'))
    )
    op.create_table('articles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=240), nullable=False),
    sa.Column('slug', sa.String(length=260), nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='article_service', native_enum=False, length=32), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('key_points', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('source_name', sa.String(length=120), nullable=True),
    sa.Column('source_url', sa.String(length=500), nullable=True),
    sa.Column('cover_url', sa.String(length=400), nullable=True),
    sa.Column('published_on', sa.Date(), nullable=True),
    sa.Column('body_chars', sa.Integer(), nullable=False),
    sa.Column('body_hash', sa.String(length=40), nullable=True),
    sa.Column('body_pruned', sa.Boolean(), nullable=False),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('entities', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='article_status', native_enum=False, length=32), nullable=False),
    sa.Column('is_featured', sa.Boolean(), nullable=False),
    sa.Column('generated', sa.Boolean(), nullable=False),
    sa.Column('generated_count', sa.SmallInteger(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_articles_author_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_articles')),
    sa.UniqueConstraint('slug', name=op.f('uq_articles_slug'))
    )
    op.create_table('attempts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=True),
    sa.Column('module_id', sa.Integer(), nullable=True),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='attempt_service', native_enum=False, length=32), nullable=True),
    sa.Column('mode', sa.String(length=16), nullable=False),
    sa.Column('status', sa.Enum('in_progress', 'submitted', 'expired', 'abandoned', name='attempt_status', native_enum=False, length=32), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duration_sec', sa.Integer(), nullable=False),
    sa.Column('blueprint', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('total_questions', sa.SmallInteger(), nullable=False),
    sa.Column('attempted', sa.SmallInteger(), nullable=False),
    sa.Column('correct', sa.SmallInteger(), nullable=False),
    sa.Column('wrong', sa.SmallInteger(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('max_score', sa.Float(), nullable=False),
    sa.Column('percentage', sa.Float(), nullable=False),
    sa.Column('passed', sa.Boolean(), nullable=True),
    sa.Column('topic_breakdown', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('detail_pruned', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['module_id'], ['modules.id'], name=op.f('fk_attempts_module_id_modules'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['template_id'], ['test_templates.id'], name=op.f('fk_attempts_template_id_test_templates'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_attempts_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attempts'))
    )
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('entity', sa.String(length=48), nullable=False),
    sa.Column('entity_id', sa.String(length=48), nullable=True),
    sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_logs_actor_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_table('gto_submissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('duration_sec', sa.Integer(), nullable=False),
    sa.Column('olq_scores', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('signals', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('overall_score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['gto_tasks.id'], name=op.f('fk_gto_submissions_task_id_gto_tasks'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_gto_submissions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_gto_submissions'))
    )
    op.create_table('interview_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='interview_session_service', native_enum=False, length=32), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duration_sec', sa.Integer(), nullable=False),
    sa.Column('exchanges', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('signals', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('olq_scores', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('overall_score', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_interview_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_interview_sessions'))
    )
    op.create_table('notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=True),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='note_service', native_enum=False, length=32), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=220), nullable=False),
    sa.Column('summary', sa.String(length=400), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('reading_minutes', sa.SmallInteger(), nullable=False),
    sa.Column('attachment_url', sa.String(length=400), nullable=True),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='note_status', native_enum=False, length=32), nullable=False),
    sa.Column('view_count', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_notes_author_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['module_id'], ['modules.id'], name=op.f('fk_notes_module_id_modules'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_notes_topic_id_topics'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notes')),
    sa.UniqueConstraint('slug', name=op.f('uq_notes_slug'))
    )
    op.create_table('physical_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('logged_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('note', sa.String(length=280), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_physical_logs_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_physical_logs'))
    )
    op.create_table('psych_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('test_type', sa.Enum('wat', 'sct', 'srt', 'tat', 'psw', 'self_description', 'piq', name='psych_session_type', native_enum=False, length=32), nullable=False),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='psych_session_service', native_enum=False, length=32), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duration_sec', sa.Integer(), nullable=False),
    sa.Column('item_count', sa.SmallInteger(), nullable=False),
    sa.Column('answered_count', sa.SmallInteger(), nullable=False),
    sa.Column('word_count', sa.Integer(), nullable=False),
    sa.Column('responses', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('signals', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('olq_scores', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('overall_score', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_psych_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_psych_sessions'))
    )
    op.create_table('refresh_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('user_agent', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_refresh_tokens_token_hash'))
    )
    op.create_table('testimonials',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('author_name', sa.String(length=120), nullable=False),
    sa.Column('headline', sa.String(length=160), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='testimonial_service', native_enum=False, length=32), nullable=True),
    sa.Column('program_name', sa.String(length=120), nullable=True),
    sa.Column('outcome', sa.String(length=60), nullable=True),
    sa.Column('rating', sa.SmallInteger(), nullable=False),
    sa.Column('avatar_url', sa.String(length=400), nullable=True),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='testimonial_status', native_enum=False, length=32), nullable=False),
    sa.Column('is_featured', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_testimonials_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_testimonials'))
    )
    op.create_table('user_stats',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('attempts_total', sa.Integer(), nullable=False),
    sa.Column('questions_answered', sa.Integer(), nullable=False),
    sa.Column('questions_correct', sa.Integer(), nullable=False),
    sa.Column('study_seconds', sa.Integer(), nullable=False),
    sa.Column('current_streak', sa.SmallInteger(), nullable=False),
    sa.Column('longest_streak', sa.SmallInteger(), nullable=False),
    sa.Column('last_active_on', sa.Date(), nullable=True),
    sa.Column('readiness', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('topic_mastery', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('olq_profile', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_stats_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_user_stats'))
    )
    op.create_table('agent_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=True),
    sa.Column('triggered_by_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('queued', 'running', 'succeeded', 'partial', 'failed', name='agent_run_status', native_enum=False, length=32), nullable=False),
    sa.Column('engine', sa.String(length=32), nullable=False),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('facts_found', sa.SmallInteger(), nullable=False),
    sa.Column('candidates', sa.SmallInteger(), nullable=False),
    sa.Column('accepted', sa.SmallInteger(), nullable=False),
    sa.Column('rejected', sa.SmallInteger(), nullable=False),
    sa.Column('duplicates', sa.SmallInteger(), nullable=False),
    sa.Column('avg_quality', sa.Float(), nullable=True),
    sa.Column('trace', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('rejections', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], name=op.f('fk_agent_runs_article_id_articles'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['triggered_by_id'], ['users.id'], name=op.f('fk_agent_runs_triggered_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_runs'))
    )
    op.create_table('interview_questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('service', sa.Enum('army', 'air_force', 'navy', 'common', name='interview_service', native_enum=False, length=32), nullable=True),
    sa.Column('category', sa.String(length=48), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('guidance', sa.Text(), nullable=True),
    sa.Column('follow_ups', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('target_olqs', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='interview_difficulty', native_enum=False, length=32), nullable=False),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='interview_status', native_enum=False, length=32), nullable=False),
    sa.Column('origin', sa.Enum('human', 'agent', 'import', name='interview_origin', native_enum=False, length=32), nullable=False),
    sa.Column('source_article_id', sa.Integer(), nullable=True),
    sa.Column('fingerprint', sa.String(length=40), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_article_id'], ['articles.id'], name=op.f('fk_interview_questions_source_article_id_articles'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_interview_questions')),
    sa.UniqueConstraint('fingerprint', name=op.f('uq_interview_questions_fingerprint'))
    )
    op.create_table('psych_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('test_type', sa.Enum('wat', 'sct', 'srt', 'tat', 'psw', 'self_description', 'piq', name='psych_test_type', native_enum=False, length=32), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('image_url', sa.String(length=400), nullable=True),
    sa.Column('perception_hint', sa.Text(), nullable=True),
    sa.Column('seconds', sa.SmallInteger(), nullable=False),
    sa.Column('target_olqs', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('model_answer', sa.Text(), nullable=True),
    sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='psych_difficulty', native_enum=False, length=32), nullable=False),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='psych_status', native_enum=False, length=32), nullable=False),
    sa.Column('origin', sa.Enum('human', 'agent', 'import', name='psych_origin', native_enum=False, length=32), nullable=False),
    sa.Column('source_article_id', sa.Integer(), nullable=True),
    sa.Column('fingerprint', sa.String(length=40), nullable=True),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_article_id'], ['articles.id'], name=op.f('fk_psych_items_source_article_id_articles'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_psych_items')),
    sa.UniqueConstraint('fingerprint', name=op.f('uq_psych_items_fingerprint'))
    )
    op.create_table('questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('service_id', sa.SmallInteger(), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.Column('qtype', sa.Enum('mcq', 'multi_select', 'true_false', 'fill_blank', 'matching', 'ordering', 'short_answer', 'non_verbal', name='question_type', native_enum=False, length=32), nullable=False),
    sa.Column('stem', sa.Text(), nullable=False),
    sa.Column('options', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('answer_keys', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('hint', sa.String(length=280), nullable=True),
    sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='question_difficulty', native_enum=False, length=32), nullable=False),
    sa.Column('marks', sa.Float(), nullable=False),
    sa.Column('negative_marks', sa.Float(), nullable=False),
    sa.Column('time_hint_sec', sa.SmallInteger(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'rejected', 'archived', name='question_status', native_enum=False, length=32), nullable=False),
    sa.Column('origin', sa.Enum('human', 'agent', 'import', name='question_origin', native_enum=False, length=32), nullable=False),
    sa.Column('media', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('source_article_id', sa.Integer(), nullable=True),
    sa.Column('agent_run_id', sa.Integer(), nullable=True),
    sa.Column('quality_score', sa.Float(), nullable=True),
    sa.Column('generation_meta', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('fingerprint', sa.String(length=40), nullable=True),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_note', sa.String(length=400), nullable=True),
    sa.Column('times_served', sa.Integer(), nullable=False),
    sa.Column('times_correct', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], name=op.f('fk_questions_agent_run_id_agent_runs'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['module_id'], ['modules.id'], name=op.f('fk_questions_module_id_modules'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], name=op.f('fk_questions_reviewed_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('fk_questions_service_id_services'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_article_id'], ['articles.id'], name=op.f('fk_questions_source_article_id_articles'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_questions_topic_id_topics'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_questions')),
    sa.UniqueConstraint('fingerprint', name=op.f('uq_questions_fingerprint'))
    )
    op.create_table('practice_cards',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('ease', sa.Float(), nullable=False),
    sa.Column('interval_days', sa.SmallInteger(), nullable=False),
    sa.Column('repetitions', sa.SmallInteger(), nullable=False),
    sa.Column('lapses', sa.SmallInteger(), nullable=False),
    sa.Column('due_on', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name=op.f('fk_practice_cards_question_id_questions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_practice_cards_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'question_id', name=op.f('pk_practice_cards'))
    )
    op.create_table('question_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('reason', sa.String(length=40), nullable=False),
    sa.Column('note', sa.String(length=400), nullable=True),
    sa.Column('resolved', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], name=op.f('fk_question_reports_question_id_questions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_question_reports_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_question_reports'))
    )
    op.create_index('ix_announcements_live', 'announcements', ['is_active', 'starts_at'], unique=False)
    op.create_index('ix_contact_messages_open', 'contact_messages', ['handled', 'created_at'], unique=False)
    op.create_index('ix_gto_tasks_live', 'gto_tasks', ['task_type', 'status'], unique=False)
    op.create_index('ix_modules_service_stage', 'modules', ['service_id', 'stage_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_programs_service_id'), 'programs', ['service_id'], unique=False)
    op.create_index('ix_test_templates_live', 'test_templates', ['service_id', 'status', 'is_mock'], unique=False)
    op.create_index(op.f('ix_topics_module_id'), 'topics', ['module_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index('ix_users_role_status', 'users', ['role', 'status'], unique=False)
    op.create_index(op.f('ix_articles_body_hash'), 'articles', ['body_hash'], unique=False)
    op.create_index('ix_articles_category', 'articles', ['category', 'status'], unique=False)
    op.create_index('ix_articles_feed', 'articles', ['status', 'published_on'], unique=False)
    op.create_index('ix_attempts_template', 'attempts', ['template_id', 'percentage'], unique=False)
    op.create_index('ix_attempts_user_recent', 'attempts', ['user_id', 'started_at'], unique=False)
    op.create_index('ix_attempts_user_status', 'attempts', ['user_id', 'status'], unique=False)
    op.create_index('ix_audit_logs_created', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity', 'entity_id'], unique=False)
    op.create_index('ix_gto_submissions_user', 'gto_submissions', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_interview_sessions_user', 'interview_sessions', ['user_id', 'started_at'], unique=False)
    op.create_index('ix_notes_module', 'notes', ['module_id', 'status', 'sort_order'], unique=False)
    op.create_index('ix_physical_logs_user', 'physical_logs', ['user_id', 'logged_on'], unique=False)
    op.create_index('ix_psych_sessions_user', 'psych_sessions', ['user_id', 'test_type', 'started_at'], unique=False)
    op.create_index('ix_refresh_tokens_expiry', 'refresh_tokens', ['expires_at'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_testimonials_live', 'testimonials', ['status', 'is_featured'], unique=False)
    op.create_index(op.f('ix_agent_runs_article_id'), 'agent_runs', ['article_id'], unique=False)
    op.create_index('ix_agent_runs_recent', 'agent_runs', ['started_at'], unique=False)
    op.create_index('ix_interview_live', 'interview_questions', ['category', 'status'], unique=False)
    op.create_index('ix_psych_items_live', 'psych_items', ['test_type', 'status', 'sort_order'], unique=False)
    op.create_index('ix_questions_live', 'questions', ['module_id', 'difficulty'], unique=False, postgresql_where=sa.text("status = 'approved'"))
    op.create_index('ix_questions_review_queue', 'questions', ['status', 'created_at'], unique=False)
    op.create_index('ix_questions_service', 'questions', ['service_id', 'status'], unique=False)
    op.create_index('ix_questions_topic_status', 'questions', ['topic_id', 'status'], unique=False)
    op.create_index('ix_practice_cards_due', 'practice_cards', ['user_id', 'due_on'], unique=False)
    op.create_index(op.f('ix_question_reports_question_id'), 'question_reports', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_question_reports_question_id'), table_name='question_reports')
    op.drop_index('ix_practice_cards_due', table_name='practice_cards')
    op.drop_index('ix_questions_topic_status', table_name='questions')
    op.drop_index('ix_questions_service', table_name='questions')
    op.drop_index('ix_questions_review_queue', table_name='questions')
    op.drop_index('ix_questions_live', table_name='questions', postgresql_where=sa.text("status = 'approved'"))
    op.drop_index('ix_psych_items_live', table_name='psych_items')
    op.drop_index('ix_interview_live', table_name='interview_questions')
    op.drop_index('ix_agent_runs_recent', table_name='agent_runs')
    op.drop_index(op.f('ix_agent_runs_article_id'), table_name='agent_runs')
    op.drop_index('ix_testimonials_live', table_name='testimonials')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_expiry', table_name='refresh_tokens')
    op.drop_index('ix_psych_sessions_user', table_name='psych_sessions')
    op.drop_index('ix_physical_logs_user', table_name='physical_logs')
    op.drop_index('ix_notes_module', table_name='notes')
    op.drop_index('ix_interview_sessions_user', table_name='interview_sessions')
    op.drop_index('ix_gto_submissions_user', table_name='gto_submissions')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created', table_name='audit_logs')
    op.drop_index('ix_attempts_user_status', table_name='attempts')
    op.drop_index('ix_attempts_user_recent', table_name='attempts')
    op.drop_index('ix_attempts_template', table_name='attempts')
    op.drop_index('ix_articles_feed', table_name='articles')
    op.drop_index('ix_articles_category', table_name='articles')
    op.drop_index(op.f('ix_articles_body_hash'), table_name='articles')
    op.drop_index('ix_users_role_status', table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_topics_module_id'), table_name='topics')
    op.drop_index('ix_test_templates_live', table_name='test_templates')
    op.drop_index(op.f('ix_programs_service_id'), table_name='programs')
    op.drop_index('ix_modules_service_stage', table_name='modules')
    op.drop_index('ix_gto_tasks_live', table_name='gto_tasks')
    op.drop_index('ix_contact_messages_open', table_name='contact_messages')
    op.drop_index('ix_announcements_live', table_name='announcements')
    op.drop_table('question_reports')
    op.drop_table('practice_cards')
    op.drop_table('questions')
    op.drop_table('psych_items')
    op.drop_table('interview_questions')
    op.drop_table('agent_runs')
    op.drop_table('user_stats')
    op.drop_table('testimonials')
    op.drop_table('refresh_tokens')
    op.drop_table('psych_sessions')
    op.drop_table('physical_logs')
    op.drop_table('notes')
    op.drop_table('interview_sessions')
    op.drop_table('gto_submissions')
    op.drop_table('audit_logs')
    op.drop_table('attempts')
    op.drop_table('articles')
    op.drop_table('users')
    op.drop_table('topics')
    op.drop_table('test_templates')
    op.drop_table('programs')
    op.drop_table('modules')
    op.drop_table('stages')
    op.drop_table('services')
    op.drop_table('gto_tasks')
    op.drop_table('contact_messages')
    op.drop_table('announcements')
