"""Synchronize semantic Global Fields with indexed Case columns.

Revision ID: 0026
Revises: 0025
"""
import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.drop_constraint("fk_cases_priority_id",type_="foreignkey")
        batch.drop_constraint("fk_cases_sub_priority_id",type_="foreignkey")
        batch.create_foreign_key("fk_cases_global_priority_id","global_priority_definitions",
            ["priority_id"],["id"])
        batch.create_foreign_key("fk_cases_global_sub_priority_id","global_sub_priority_definitions",
            ["sub_priority_id"],["id"])
    op.create_table(
        "case_semantic_sync_conflicts",
        sa.Column("id",sa.Uuid(),primary_key=True),
        sa.Column("case_id",sa.Uuid(),sa.ForeignKey("cases.id",ondelete="CASCADE"),nullable=False),
        sa.Column("semantic_binding",sa.String(80),nullable=False),
        sa.Column("global_value_json",sa.JSON()),
        sa.Column("optimized_value_id",sa.Uuid()),
        sa.Column("reason",sa.String(120),nullable=False),
        sa.Column("resolved_at",sa.DateTime(timezone=True)),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
    )
    op.create_index("ix_case_semantic_conflict_case","case_semantic_sync_conflicts",["case_id"])
    op.create_index("ix_case_semantic_conflict_binding","case_semantic_sync_conflicts",["semantic_binding"])
    from sqlalchemy.orm import Session

    from app.modules.case_semantics.service import CaseSemanticFieldService
    from app.modules.models import Case
    session=Session(bind=op.get_bind())
    for item in session.scalars(sa.select(Case)):
        CaseSemanticFieldService(session).sync_case(item)
    session.flush()


def downgrade() -> None:
    op.drop_index("ix_case_semantic_conflict_binding",table_name="case_semantic_sync_conflicts")
    op.drop_index("ix_case_semantic_conflict_case",table_name="case_semantic_sync_conflicts")
    op.drop_table("case_semantic_sync_conflicts")
    with op.batch_alter_table("cases") as batch:
        batch.drop_constraint("fk_cases_global_priority_id",type_="foreignkey")
        batch.drop_constraint("fk_cases_global_sub_priority_id",type_="foreignkey")
        batch.create_foreign_key("fk_cases_priority_id","priority_definitions",["priority_id"],["id"])
        batch.create_foreign_key("fk_cases_sub_priority_id","sub_priority_definitions",["sub_priority_id"],["id"])
