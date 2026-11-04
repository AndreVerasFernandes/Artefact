"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv(
	"OPENROUTER_MODEL",
	"nvidia/nemotron-3.5-lightning:free",
)
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL")
OPENROUTER_SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "Emporio da Musica")
