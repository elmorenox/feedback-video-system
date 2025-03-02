from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sshtunnel import SSHTunnelForwarder
from urllib.parse import urlparse
from src.settings import Settings

# Load settings
settings = Settings()

# Base for models (shared between SQLite and MySQL)
Base = declarative_base()

# SQLite setup (local database)
sqlite_engine = create_engine(settings.DB_URL)
SessionLocalSQLite = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)


# Function to modify MySQL connection string for SSH tunnel
def build_mysql_connection_string_with_ssh(
    mysql_url: str, ssh_tunnel: SSHTunnelForwarder
) -> str:
    """
    Modifies the MySQL connection string to use the SSH tunnel's local bind address.
    """
    parsed_url = urlparse(mysql_url)
    new_netloc = f"127.0.0.1:{ssh_tunnel.local_bind_port}"
    modified_url = f"{parsed_url.scheme}://{parsed_url.username}:{parsed_url.password}@{new_netloc}{parsed_url.path}"

    return modified_url


# Parse the MYSQL_URL to extract the remote MySQL host and port
parsed_mysql_url = urlparse(settings.MYSQL_URL)
mysql_host = parsed_mysql_url.hostname
mysql_port = parsed_mysql_url.port or 3306

# SSH Tunnel setup for MySQL
ssh_tunnel = SSHTunnelForwarder(
    (settings.SSH_HOST, settings.SSH_PORT),
    ssh_username=settings.SSH_USERNAME,
    ssh_pkey=settings.SSH_KEY_PATH,
    remote_bind_address=(
        mysql_host,
        mysql_port,
    ),
)

# Start the SSH tunnel
ssh_tunnel.start()

# Build MySQL connection string with SSH tunnel
mysql_url_with_ssh = build_mysql_connection_string_with_ssh(
    settings.MYSQL_URL, ssh_tunnel
)

# Create SQLAlchemy engine for MySQL
mysql_engine = create_engine(
    mysql_url_with_ssh,
    execution_options={"readonly": True}
)
SessionLocalMySQL = sessionmaker(
    autocommit=False, autoflush=False, bind=mysql_engine
)


# Dependency to get SQLite DB session
def get_sqlite_db():
    db = SessionLocalSQLite()
    try:
        yield db
    finally:
        db.close()


# Dependency to get MySQL DB session
def get_mysql_db():
    db = SessionLocalMySQL()
    try:
        yield db
    finally:
        db.close()


# Close the SSH tunnel when the application shuts down
def close_ssh_tunnel():
    ssh_tunnel.stop()
