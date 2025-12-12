"""Initial migration - Create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 users 表
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_created_at', 'users', ['created_at'])
    
    # 创建 knowledge_bases 表
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('embedding_model', sa.String(length=100), nullable=False, server_default='text-embedding-ada-002'),
        sa.Column('embedding_dimension', sa.Integer(), nullable=False, server_default='1536'),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_chunks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_bases_owner_id', 'knowledge_bases', ['owner_id'])
    op.create_index('ix_knowledge_bases_is_public', 'knowledge_bases', ['is_public'])
    op.create_index('ix_knowledge_bases_created_at', 'knowledge_bases', ['created_at'])
    
    # 创建 kb_tags 表
    op.create_table(
        'kb_tags',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('kb_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['kb_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_tags_kb_id', 'kb_tags', ['kb_id'])
    op.create_index('ix_kb_tags_name', 'kb_tags', ['name'])
    
    # 创建 documents 表
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('kb_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['kb_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_kb_id', 'documents', ['kb_id'])
    op.create_index('ix_documents_status', 'documents', ['status'])
    op.create_index('ix_documents_file_type', 'documents', ['file_type'])
    op.create_index('ix_documents_created_at', 'documents', ['created_at'])
    op.create_index('ix_documents_content_hash', 'documents', ['content_hash'])
    
    # 创建 chunks 表
    op.create_table(
        'chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('kb_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('vector_id', sa.String(length=100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kb_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chunks_document_id', 'chunks', ['document_id'])
    op.create_index('ix_chunks_kb_id', 'chunks', ['kb_id'])
    op.create_index('ix_chunks_chunk_index', 'chunks', ['chunk_index'])
    op.create_index('ix_chunks_vector_id', 'chunks', ['vector_id'])
    
    # 创建 api_keys 表
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])
    
    # 创建 user_kb_permissions 表
    op.create_table(
        'user_kb_permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('kb_id', sa.UUID(), nullable=False),
        sa.Column('permission', sa.String(length=20), nullable=False, server_default='read'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['kb_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'kb_id', name='uq_user_kb_permission')
    )
    op.create_index('ix_user_kb_permissions_user_id', 'user_kb_permissions', ['user_id'])
    op.create_index('ix_user_kb_permissions_kb_id', 'user_kb_permissions', ['kb_id'])
    
    # 创建 model_configs 表
    op.create_table(
        'model_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('model_type', sa.String(length=20), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('api_base', sa.String(length=500), nullable=True),
        sa.Column('encrypted_api_key', sa.Text(), nullable=True),
        sa.Column('extra_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_model_configs_model_type', 'model_configs', ['model_type'])
    op.create_index('ix_model_configs_provider', 'model_configs', ['provider'])
    op.create_index('ix_model_configs_is_default', 'model_configs', ['is_default'])
    op.create_index('ix_model_configs_is_active', 'model_configs', ['is_active'])


def downgrade() -> None:
    # 按依赖顺序删除表
    op.drop_table('model_configs')
    op.drop_table('user_kb_permissions')
    op.drop_table('api_keys')
    op.drop_table('chunks')
    op.drop_table('documents')
    op.drop_table('kb_tags')
    op.drop_table('knowledge_bases')
    op.drop_table('users')
