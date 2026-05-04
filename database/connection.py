import os

from config import DB_CONFIG
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from models import Base  # triggers imports of all tables

_raw_pw = (DB_CONFIG.get("password") or "").strip()
if not _raw_pw:
    raise RuntimeError(
        "DB_PASSWORD is empty. Add it to your project root `.env` file (same value as Azure "
        'Application settings → DB_PASSWORD), e.g. DB_PASSWORD=your_password_here\n'
        "If the password contains # or spaces, wrap it in double quotes: DB_PASSWORD=\"...\""
    )

password = quote_plus(_raw_pw)

# Build the SQLAlchemy database URL for MySQL (using PyMySQL driver)
# Include SSL and connection parameters to match CRM backend configuration
# For Azure MySQL, SSL is required
db_url = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{password}"
    f"@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
    f"?charset={DB_CONFIG['charset']}"
)

# Create engine with SSL enabled for Azure MySQL
# PyMySQL requires SSL parameters to be passed via connect_args
# For Azure MySQL, we need to enable SSL but skip hostname verification
# This matches the direct PyMySQL connection that works
# pool_pre_ping: drops dead connections (fixes "MySQL server has gone away" / SSLEOFError after idle).
# pool_recycle: recycle before Azure/MySQL wait_timeout (override with DB_POOL_RECYCLE seconds).
_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "280")),
    "connect_args": {
        "ssl": {
            "check_hostname": False
        }
    },
}
engine = create_engine(db_url, **_engine_kwargs)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
