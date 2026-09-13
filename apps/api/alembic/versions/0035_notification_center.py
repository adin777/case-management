"""Complete notification center persistence.

Revision ID: 0035
Revises: 0034
"""
import sqlalchemy as sa

from alembic import op

revision="0035";down_revision="0034";branch_labels=None;depends_on=None

def upgrade()->None:
    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("case_id",sa.Uuid()))
        batch.add_column(sa.Column("environment_id",sa.Uuid()))
        batch.add_column(sa.Column("route",sa.String(500)))
        batch.add_column(sa.Column("source",sa.String(50),nullable=False,server_default="business"))
        batch.add_column(sa.Column("deduplication_key",sa.String(300)))
        batch.add_column(sa.Column("metadata_json",sa.JSON(),nullable=False,server_default="{}"))
        batch.create_unique_constraint("uq_notifications_deduplication_key",["deduplication_key"])
        batch.create_foreign_key("fk_notifications_case_id","cases",["case_id"],["id"],ondelete="CASCADE")
        batch.create_foreign_key("fk_notifications_environment_id","environments",["environment_id"],["id"])
        batch.create_index("ix_notifications_case_id",["case_id"])
        batch.create_index("ix_notifications_environment_id",["environment_id"])
    op.create_table("notification_preferences",sa.Column("user_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("notification_type",sa.String(80),primary_key=True),sa.Column("in_app_enabled",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("email_enabled",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("frequency",sa.String(20),nullable=False,server_default="immediate"))
    op.create_table("notification_delivery_logs",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("notification_id",sa.Uuid(),sa.ForeignKey("notifications.id",ondelete="CASCADE"),nullable=False),sa.Column("channel",sa.String(30),nullable=False),sa.Column("recipient",sa.String(320),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("attempted_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.Column("error",sa.Text()),sa.Column("provider_message_id",sa.String(200)))
    op.create_index("ix_notification_delivery_logs_notification_id","notification_delivery_logs",["notification_id"])

def downgrade()->None:
    op.drop_table("notification_delivery_logs");op.drop_table("notification_preferences")
    with op.batch_alter_table("notifications") as batch:
        batch.drop_index("ix_notifications_environment_id");batch.drop_index("ix_notifications_case_id");batch.drop_constraint("fk_notifications_environment_id",type_="foreignkey");batch.drop_constraint("fk_notifications_case_id",type_="foreignkey");batch.drop_constraint("uq_notifications_deduplication_key",type_="unique")
        for name in ("metadata_json","deduplication_key","source","route","environment_id","case_id"):batch.drop_column(name)
