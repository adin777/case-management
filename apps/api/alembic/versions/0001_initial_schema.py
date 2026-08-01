"""initial case-management schema"""
from alembic import op
from app.database.base import Base
from app.modules import models  # noqa: F401
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
