from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    gauth_file: str = "./.gauth.json"
    accounts_file: str = "./.accounts.json"
    credentials_dir: str = "."

    @property
    def absolute_credentials_dir(self) -> str:
        return os.path.abspath(self.credentials_dir)

    @property
    def absolute_gauth_file(self) -> str:
        return os.path.abspath(self.gauth_file)

    @property
    def absolute_accounts_file(self) -> str:
        return os.path.abspath(self.accounts_file)

try:
    settings = Settings()
    logger.info(f"Loaded settings: gauth_file='{settings.gauth_file}', accounts_file='{settings.accounts_file}', credentials_dir='{settings.credentials_dir}'")
    logger.info(f"Absolute paths: gauth='{settings.absolute_gauth_file}', accounts='{settings.absolute_accounts_file}', creds='{settings.absolute_credentials_dir}'")
except Exception as e:
    logger.error(f"Error loading settings: {e}")
    settings = Settings() # Use defaults
    logger.warning("Using default settings due to loading error.")
