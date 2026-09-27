"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration loaded from environment variables."""

    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    
    # LLM Provider: "groq" or "google"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    
    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Google AI Studio (Gemini)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash-lite")

    HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")
    HINDSIGHT_BASE_URL: str = os.getenv(
        "HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"
    )
    HINDSIGHT_BANK_ID: str = os.getenv("HINDSIGHT_BANK_ID", "code-review-demo")

    @property
    def has_github(self) -> bool:
        return bool(self.GITHUB_TOKEN)

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def has_google(self) -> bool:
        return bool(self.GOOGLE_API_KEY)

    @property
    def has_llm(self) -> bool:
        return self.has_groq or self.has_google

    @property
    def has_hindsight(self) -> bool:
        return bool(self.HINDSIGHT_API_KEY)


settings = Settings()
