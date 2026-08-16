"""Create global case-value catalogs and preserve legacy identifiers.

Revision ID: 0021
Revises: 0020
"""
import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def _catalog(name: str, *, status: bool = False) -> None:
    columns = [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("label_he", sa.String(200), nullable=False),
        sa.Column("label_en", sa.String(200)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]
    if status:
        columns[4:4] = [
            sa.Column("semantic_category", sa.String(30), nullable=False, server_default="open"),
            sa.Column("is_initial", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false()),
        ]
    op.create_table(name, *columns)


def upgrade() -> None:
    _catalog("global_status_definitions", status=True)
    _catalog("global_priority_definitions")
    _catalog("global_sub_priority_definitions")
    connection = op.get_bind()
    statuses = connection.execute(sa.text("""
        SELECT id, code, label_he, label_en, semantic_category, is_initial, is_final,
               is_active, sort_order, color FROM workflow_statuses ORDER BY is_initial DESC, sort_order, id
    """)).mappings().all()
    initial_id = next((row["id"] for row in statuses if row["is_initial"] and row["is_active"]), None)
    used_codes: set[str] = set()
    for row in statuses:
        code = row["code"]
        if code in used_codes:
            code = f"{code}_{str(row['id']).replace('-', '')[:8]}"
        used_codes.add(code)
        connection.execute(sa.text("""
            INSERT INTO global_status_definitions
            (id, code, label_he, label_en, semantic_category, is_initial, is_final, is_active, sort_order, color)
            VALUES (:id, :code, :label_he, :label_en, :semantic_category, :is_initial, :is_final, :is_active, :sort_order, :color)
        """), {**row, "code": code, "is_initial": row["id"] == initial_id})
    for source, target in (("priority_definitions", "global_priority_definitions"),
                           ("sub_priority_definitions", "global_sub_priority_definitions")):
        rows = connection.execute(sa.text(
            f"SELECT id, code, label_he, label_en, is_active, sort_order, color FROM {source} ORDER BY sort_order, id"
        )).mappings().all()
        used_codes = set()
        for row in rows:
            code = row["code"]
            if code in used_codes:
                code = f"{code}_{str(row['id']).replace('-', '')[:8]}"
            used_codes.add(code)
            connection.execute(sa.text(f"""
                INSERT INTO {target} (id, code, label_he, label_en, is_active, sort_order, color)
                VALUES (:id, :code, :label_he, :label_en, :is_active, :sort_order, :color)
            """), {**row, "code": code})


def downgrade() -> None:
    op.drop_table("global_sub_priority_definitions")
    op.drop_table("global_priority_definitions")
    op.drop_table("global_status_definitions")
