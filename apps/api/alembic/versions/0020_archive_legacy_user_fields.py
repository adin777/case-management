"""Archive legacy employee user fields without deleting historical values.

Revision ID: 0020
Revises: 0019
"""
import sqlalchemy as sa

from alembic import op

revision="0020";down_revision="0019";branch_labels=None;depends_on=None

def upgrade()->None:
    connection=op.get_bind(); inspector=sa.inspect(connection)
    if "user_field_definitions" in inspector.get_table_names():
        connection.execute(sa.text("UPDATE user_field_definitions SET is_active = 0 WHERE is_active = 1"))

def downgrade()->None:
    pass
