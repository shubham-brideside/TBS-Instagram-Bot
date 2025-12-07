from config import DB_CONFIG
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from models import Base  # triggers imports of all tables

password = quote_plus(DB_CONFIG['password'] or '')

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
engine = create_engine(
    db_url,
    echo=False,
    connect_args={
        "ssl": {
            "check_hostname": False
        }
    }
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
