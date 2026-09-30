from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def build_database(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        # ponytail: Azure Files rejects SQLite's POSIX locks, so this uses nolock.
        # Ceiling is one writer. A second replica corrupts the file; move to Postgres.
        path = database_url.removeprefix("sqlite:///")
        if path.startswith("./"):
            path = path[2:]
        database_url = f"sqlite:///file:{path}?mode=rwc&nolock=1&uri=true"
        connect_args = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(database_url, connect_args=connect_args)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
