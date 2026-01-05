from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # GitHub Configuration
    GITHUB_TOKEN: str = Field(..., description="GitHub Personal Access Token")
    GITHUB_POLL_INTERVAL: int = Field(default=30, ge=10, le=300)

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    OPENAI_LLM_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_MAX_TOKENS: int = Field(default=1000, ge=100, le=4000)
    OPENAI_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=2.0)

    # Pathway Configuration
    PATHWAY_PERSISTENCE_DIR: str = Field(default="./data/pathway_snapshots")
    PATHWAY_LICENSE_KEY: Optional[str] = Field(default=None)

    # API Server Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000, ge=1024, le=65535)
    API_RELOAD: bool = Field(default=False)
    CORS_ORIGINS: str = Field(default="http://localhost:5173,http://localhost:3000")

    # Frontend Configuration
    VITE_API_URL: str = Field(default="http://localhost:8000")
    VITE_WS_URL: str = Field(default="ws://localhost:8000")

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")

    # Monitoring Configuration
    ENABLE_METRICS: bool = Field(default=True)
    METRICS_PORT: int = Field(default=9090, ge=1024, le=65535)

    # Demo Mode
    DEMO_MODE: bool = Field(default=False)
    DEMO_REPOS_FILE: str = Field(default="./demo/demo_repos.json")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of {allowed_levels}")
        return v_upper

    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format is either 'json' or 'pretty'."""
        allowed_formats = {"json", "pretty"}
        v_lower = v.lower()
        if v_lower not in allowed_formats:
            raise ValueError(f"LOG_FORMAT must be one of {allowed_formats}")
        return v_lower

    @field_validator("GITHUB_TOKEN")
    @classmethod
    def validate_github_token(cls, v: str) -> str:
        """Validate GitHub token format."""
        if not v.startswith(("ghp_", "github_pat_")):
            raise ValueError("GITHUB_TOKEN must start with 'ghp_' or 'github_pat_'")
        return v

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """Validate OpenAI API key format."""
        if not v.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY must start with 'sk-'")
        return v

    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# this will be imported throughout the project
settings = Settings()
