"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create twin_objects table
    op.create_table(
        'twin_objects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object_type', sa.String(), nullable=True),
        sa.Column('lifecycle_state', sa.String(), nullable=True),
        sa.Column('health_state', sa.String(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create snapshots table
    op.create_table(
        'snapshots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object_id', sa.String(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('hash', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['object_id'], ['twin_objects.id'], )
    )

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('actor', sa.String(), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('snapshots')
    op.drop_table('twin_objects')
