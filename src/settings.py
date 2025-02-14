from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SYNTHESIA_API_KEY: str
    DB_URL: str = "sqlite:///sqlite.db"
    MYSQL_URL: str
    SSH_HOST: str
    SSH_USERNAME: str
    SSH_KEY_PATH: str
    SSH_PORT: int = 22
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
