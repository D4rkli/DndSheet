from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    BOT_TOKEN: str

    BASE_URL: str = "http://127.0.0.1:8000"
    WEBAPP_URL: str = "http://127.0.0.1:8000/webapp/?v=5"
    SQLITE_PATH: str = "sqlite+aiosqlite:///./dnd._v2.sqlite3"
    DM_USER_IDS: str = ""

    def dm_ids(self) -> set[int]:
        if not self.DM_USER_IDS:
            return set()
        return {int(x.strip()) for x in self.DM_USER_IDS.split(",")}


settings = Settings()