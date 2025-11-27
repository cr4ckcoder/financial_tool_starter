from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"

    class Config:
        env_file = ".env"

settings = Settings()
