from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    BOT_TOKEN: str

    WEBAPP_URL: str = "https://d4rkli.ru/webapp/"
    SQLITE_PATH: str = "sqlite+aiosqlite:////var/lib/dndsheet/dnd_v2.sqlite3"
    DM_USER_IDS: str = ""
    DEV_USER_IDS: str = ""

    SESSION_SECRET: str
    COOKIE_SECURE: bool = True
    SESSION_MAX_AGE_DAYS: int = 30

    VK_APP_ID: str = ""
    VK_APP_SECRET: str = ""
    VK_REDIRECT_URI: str = "https://d4rkli.ru/api/auth/vk/callback"

    def dm_ids(self) -> set[int]:
        if not self.DM_USER_IDS:
            return set()
        return {int(x.strip()) for x in self.DM_USER_IDS.split(",")}

    def dev_ids(self) -> set[int]:
        if not self.DEV_USER_IDS:
            return set()
        return {int(x.strip()) for x in self.DEV_USER_IDS.split(",")}


settings = Settings()