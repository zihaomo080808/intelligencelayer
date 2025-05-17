"""add feedback tables

Revision ID: feedback_tables
Revises: 001_initial
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT

# revision identifiers, used by Alembic
revision = 'feedback_tables'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Create user_feedback table
    op.create_table(
        'user_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('item_id', sa.String(), nullable=False),
        sa.Column('feedback_type', sa.String(), nullable=False),  # 'like' or 'skip'
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('item_embedding', ARRAY(FLOAT), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_item_interactions table
    op.create_table(
        'user_item_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('item_id', sa.String(), nullable=False),
        sa.Column('interaction_type', sa.String(), nullable=False),  # 'view', 'click', 'apply'
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for performance
    op.create_index('ix_user_feedback_user_id', 'user_feedback', ['user_id'])
    op.create_index('ix_user_feedback_item_id', 'user_feedback', ['item_id'])
    op.create_index('ix_user_item_interactions_user_id', 'user_item_interactions', ['user_id'])
    op.create_index('ix_user_item_interactions_item_id', 'user_item_interactions', ['item_id'])

def downgrade():
    op.drop_table('user_feedback')
    op.drop_table('user_item_interactions') 