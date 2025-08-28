"""
Configuration settings for the Email Transaction Parser.
"""
import os
from typing import Optional

# Try to import pydantic-based settings; if unavailable, fall back to a simple env-backed Settings
try:
    from pydantic_settings import BaseSettings
    from pydantic import validator
    PydanticBacked = True
except Exception:
    PydanticBacked = False


if PydanticBacked:
    class Settings(BaseSettings):
        """Application settings using pydantic-settings when present."""
        # Email Configuration
        email_host: str = "gmail"  # gmail, outlook, yahoo, custom
        email_server: Optional[str] = None  # Auto-detected if not specified
        email_port: int = 993
        email_username: str = "your_email@gmail.com"
        email_password: str = "your_app_password"
        email_use_ssl: bool = True

        # Database Configuration
        database_url: str = "sqlite:///transactions.db"

        # Application Configuration
        app_host: str = "0.0.0.0"
        app_port: int = 8000
        log_level: str = "INFO"
        app_name: str = "Email Transaction Parser"

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

        @validator('email_port')
        def validate_email_port(cls, v):
            if v not in [143, 993, 587, 465]:
                raise ValueError('Email port must be one of: 143, 993, 587, 465')
            return v

        @property
        def email_server_config(self) -> dict:
            """Get email server configuration based on host."""
            if self.email_server:
                # Use custom server if specified
                return {
                    "server": self.email_server,
                    "port": self.email_port,
                    "use_ssl": self.email_use_ssl
                }

            # Auto-detect based on email_host
            configs = {
                "gmail": {
                    "server": "imap.gmail.com",
                    "port": 993,
                    "use_ssl": True
                },
                "outlook": {
                    "server": "outlook.office365.com",
                    "port": 993,
                    "use_ssl": True
                },
                "yahoo": {
                    "server": "imap.mail.yahoo.com",
                    "port": 993,
                    "use_ssl": True
                },
                "custom": {
                    "server": "mail.bchainre.com",
                    "port": 993,
                    "use_ssl": True
                }
            }

            config = configs.get(self.email_host.lower(), configs["gmail"])
            # Override with custom port if specified
            config["port"] = self.email_port
            config["use_ssl"] = self.email_use_ssl

            return config


    # Create settings instance
    settings = Settings()

else:
    # Lightweight fallback Settings that reads from environment variables (used when pydantic-settings is missing).
    class Settings:
        def __init__(self):
            # Email Configuration
            self.email_host = os.environ.get('EMAIL_HOST', 'gmail')
            self.email_server = os.environ.get('EMAIL_SERVER')
            self.email_port = int(os.environ.get('EMAIL_PORT', 993))
            self.email_username = os.environ.get('EMAIL_USERNAME', 'your_email@gmail.com')
            self.email_password = os.environ.get('EMAIL_PASSWORD', 'your_app_password')
            self.email_use_ssl = os.environ.get('EMAIL_USE_SSL', 'true').lower() in ('1', 'true', 'yes')

            # Database Configuration
            self.database_url = os.environ.get('DATABASE_URL', 'sqlite:///transactions.db')

            # Application Configuration
            self.app_host = os.environ.get('APP_HOST', '0.0.0.0')
            self.app_port = int(os.environ.get('APP_PORT', 8000))
            self.log_level = os.environ.get('LOG_LEVEL', 'INFO')
            self.app_name = os.environ.get('APP_NAME', 'Email Transaction Parser')

        def email_server_config(self) -> dict:
            """Get email server configuration based on host."""
            if self.email_server:
                return {
                    "server": self.email_server,
                    "port": self.email_port,
                    "use_ssl": self.email_use_ssl
                }

            configs = {
                "gmail": {
                    "server": "imap.gmail.com",
                    "port": 993,
                    "use_ssl": True
                },
                "outlook": {
                    "server": "outlook.office365.com",
                    "port": 993,
                    "use_ssl": True
                },
                "yahoo": {
                    "server": "imap.mail.yahoo.com",
                    "port": 993,
                    "use_ssl": True
                },
                "custom": {
                    "server": "mail.bchainre.com",
                    "port": 993,
                    "use_ssl": True
                }
            }

            config = configs.get(self.email_host.lower(), configs["gmail"])
            config["port"] = self.email_port
            config["use_ssl"] = self.email_use_ssl
            return config


    settings = Settings()
