import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# プロジェクト直下の .env を読み込む
load_dotenv(PROJECT_ROOT / ".env")


def get_description_provider_name() -> str:
    """
    説明文生成Providerを切り替えるための設定。
    初期値は dummy。
    """
    return os.getenv("DESCRIPTION_PROVIDER", "dummy")


def get_openai_api_key() -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key is None:
        return None

    api_key = api_key.strip()

    if api_key == "" or "ここに" in api_key:
        return None

    return api_key

def get_gemini_api_key() -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key is None:
        return None

    api_key = api_key.strip()

    if api_key == "" or "ここに" in api_key:
        return None

    return api_key


def get_gemini_description_model() -> str:
    return os.getenv("GEMINI_DESCRIPTION_MODEL", "gemini-2.5-flash")


def get_openai_description_model() -> str:
    """
    sector説明生成に使うOpenAIモデル名。
    """
    return os.getenv("OPENAI_DESCRIPTION_MODEL", "gpt-4.1-mini")


def get_sector_description_prompt_path() -> Path:
    return PROJECT_ROOT / "prompts" / "sector_description_prompt.md"