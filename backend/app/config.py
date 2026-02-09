from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    BOT_TOKEN: str

    BASE_URL: str = "https://d4rkli.ru"
    WEBAPP_URL: str = "//d4rkli.ru/webapp/?"
    SQLITE_PATH: str = "sqlite+aiosqlite:///./dnd_v2.sqlite3"
    DM_USER_IDS: str = ""

    def dm_ids(self) -> set[int]:
        if not self.DM_USER_IDS:
            return set()
        return {int(x.strip()) for x in self.DM_USER_IDS.split(",")}


settings = Settings()