"""Add the implementer configuration permission domain.

Revision ID: 0029
Revises: 0028
"""
import sqlalchemy as sa

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("""
        INSERT INTO permissions (code, description, name_he, description_he, category, scope, is_active)
        SELECT 'implementer.configuration.read', 'View business configuration', 'צפייה בתצורת מערכת',
               'צפייה בתצורה עסקית מבוקרת', 'יישום מערכת', 'global', 1
        WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='implementer.configuration.read')
    """))
    connection.execute(sa.text("""
        INSERT INTO permissions (code, description, name_he, description_he, category, scope, is_active)
        SELECT 'implementer.configuration.manage', 'Manage business configuration', 'עריכת תצורת מערכת',
               'עריכת תצורה עסקית מבוקרת', 'יישום מערכת', 'global', 1
        WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='implementer.configuration.manage')
    """))
    connection.execute(sa.text("""
        INSERT INTO permission_domains
          (code, name_he, description_he, category, scope, view_permissions, edit_permissions, sort_order, is_active)
        SELECT 'implementer_studio', 'סטודיו להגדרת מערכת', 'צפייה ועריכת תצורה עסקית מבוקרת',
               'יישום מערכת', 'global', 'implementer.configuration.read', 'implementer.configuration.manage', 0, 1
        WHERE NOT EXISTS (SELECT 1 FROM permission_domains WHERE code='implementer_studio')
    """))


def downgrade() -> None:
    op.execute("DELETE FROM permission_domains WHERE code='implementer_studio'")
    op.execute("DELETE FROM permissions WHERE code IN ('implementer.configuration.read','implementer.configuration.manage')")
