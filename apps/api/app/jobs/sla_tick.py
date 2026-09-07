from app.database.session import SessionLocal
from app.modules.sla.service import SlaEngine


def run_once() -> dict[str, int]:
    with SessionLocal() as db:
        result = SlaEngine(db).tick()
        db.commit()
        return result


if __name__ == "__main__":
    print(run_once())
