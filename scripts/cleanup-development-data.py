"""Safely remove local development identities after a verified SQLite backup."""

import argparse
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "case_management.db"
BACKUP = ROOT / "data" / "backups" / "case_management_before_user_cleanup.db"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not BACKUP.is_file() or BACKUP.stat().st_size == 0:
        raise SystemExit("A verified pre-cleanup backup is required")
    backup_engine = create_engine(f"sqlite:///{BACKUP.as_posix()}")
    with backup_engine.connect() as backup_connection:
        if backup_connection.exec_driver_sql("pragma quick_check").scalar_one() != "ok":
            raise SystemExit("The pre-cleanup backup failed SQLite integrity validation")
    engine = create_engine(f"sqlite:///{DATABASE.as_posix()}")
    with engine.begin() as connection:
        admin_id = connection.execute(text("select id from users where email='admin@example.com'")) .scalar_one()
        removed = connection.execute(text("select id,email from users where id != :admin"), {"admin": admin_id}).mappings().all()
        print("Will remove:", [row["email"] for row in removed])
        if not args.apply:
            return
        ids = [row["id"] for row in removed]
        if ids:
            bind = {f"u{i}": value for i, value in enumerate(ids)}
            values = ",".join(f":u{i}" for i in range(len(ids)))
            connection.execute(text(f"update audit_events set actor_name_snapshot=(select display_name from users where users.id=audit_events.actor_id), actor_email_snapshot=(select email from users where users.id=audit_events.actor_id), actor_id=null where actor_id in ({values})"), bind)
            case_ids = connection.execute(text(f"select distinct id from cases where requester_id in ({values}) or reporter_id in ({values}) or assignee_id in ({values}) union select case_id from case_participants where user_id in ({values}) union select case_id from comments where author_id in ({values})"), bind).scalars().all()
            if case_ids:
                case_bind = {f"c{i}": value for i, value in enumerate(case_ids)}
                case_values = ",".join(f":c{i}" for i in range(len(case_ids)))
                connection.execute(text(f"delete from cases where id in ({case_values})"), case_bind)
            flow_ids = connection.execute(text(f"select distinct approval_flow_id from approval_step_definitions where approver_user_id in ({values})"), bind).scalars().all()
            if flow_ids:
                flow_bind = {f"f{i}": value for i, value in enumerate(flow_ids)}
                flow_values = ",".join(f":f{i}" for i in range(len(flow_ids)))
                connection.execute(text(f"delete from approval_flow_definitions where id in ({flow_values})"), flow_bind)
            connection.execute(text("delete from groups"))
            connection.execute(text(f"delete from users where id in ({values})"), bind)
        connection.execute(text("update users set is_active=1,is_system_admin=1 where id=:admin"), {"admin": admin_id})
        remaining = connection.execute(text("select email from users")).scalars().all()
        if remaining != ["admin@example.com"]:
            raise RuntimeError(f"Unexpected remaining users: {remaining}")
        print("Cleanup committed; audit history preserved with actor snapshots")


if __name__ == "__main__":
    main()
