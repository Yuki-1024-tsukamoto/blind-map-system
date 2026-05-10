import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_description_provider_name() -> str:
    """
    説明文生成Providerを切り替えるための設定。
    初期値は dummy。
    後で openai に切り替える。
    """
    return os.getenv("DESCRIPTION_PROVIDER", "dummy")


def get_openai_api_key() -> str | None:
    """
    OpenAI API key を環境変数から取得する。
    今はまだ使わない。
    """
    return os.getenv("OPENAI_API_KEY")


def get_sector_description_prompt_path() -> Path:
    return PROJECT_ROOT / "prompts" / "sector_description_prompt.md"