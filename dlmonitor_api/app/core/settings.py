"""
Core settings for the DLMonitor API application.
Uses Pydantic Settings for environment variable management.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "DLMonitor API"
    app_version: str = "2.0.0"
    debug: bool = False
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://dlmonitor:password@localhost/dlmonitor",
        description="Async PostgreSQL connection string"
    )
    database_echo: bool = False  # Log SQL queries
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching and sessions"
    )
    
    # Supabase Auth
    supabase_url: str = Field(
        default="",
        description="Supabase project URL for authentication"
    )
    supabase_anon_key: str = Field(
        default="",
        description="Supabase anonymous/public API key"
    )
    supabase_service_key: Optional[str] = Field(
        default=None,
        description="Supabase service role key for admin operations"
    )
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    allowed_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: list[str] = ["*"]
    
    # External APIs
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    github_token: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Sentry (Error tracking)
    sentry_dsn: Optional[str] = None
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings() 