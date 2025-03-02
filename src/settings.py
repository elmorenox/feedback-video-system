from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # FastAPI
    SECRET_KEY: str
    API_VERSION: str
    DEBUG: bool = False

    # Databases
    DB_URL: str
    MYSQL_URL: str

    # SSH Tunnel
    SSH_HOST: str
    SSH_PORT: int = 22
    SSH_USERNAME: str
    SSH_KEY_PATH: str

    # OpenAI
    OPENAI_API_KEY: str

    # HeyGen
    HEYGEN_API_KEY: str
    HEYGEN_TEMPLATE_ID: str

    # Descript
    DESCRIPT_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
