from typing import Any


class DescriptionProvider:
    """
    説明文生成Providerの抽象的な親クラス。
    後で OpenAIProvider / GeminiProvider に差し替える。
    """

    def generate_sector_description(
        self,
        node_id: str,
        node_name: str,
        sector: str,
        sector_label_ja: str,
        sector_label_en: str,
        sector_image_url: str | None,
        ocr_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raise NotImplementedError


class DummyDescriptionProvider(DescriptionProvider):
    """
    ダミー説明生成Provider。
    実際には画像を読まないが、sector画像URLとOCR結果を説明文に反映する。
    """

    def generate_sector_description(
        self,
        node_id: str,
        node_name: str,
        sector: str,
        sector_label_ja: str,
        sector_label_en: str,
        sector_image_url: str | None,
        ocr_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ocr_texts = [
            str(result.get("text", ""))
            for result in ocr_results
            if result.get("text")
        ]

        if ocr_texts:
            ocr_summary_ja = "、".join(ocr_texts)
            ocr_summary_en = ", ".join(ocr_texts)
        else:
            ocr_summary_ja = "なし"
            ocr_summary_en = "none"

        if sector_image_url:
            image_reference_ja = f"対応するsector画像は {sector_image_url} です。"
            image_reference_en = f"The corresponding sector image is {sector_image_url}."
        else:
            image_reference_ja = "対応するsector画像は未生成です。"
            image_reference_en = "The corresponding sector image has not been generated."

        return {
            "ja": {
                "brief": (
                    f"{node_name}の{sector_label_ja}方向の仮説明です。"
                    f"OCR候補: {ocr_summary_ja}。"
                ),
                "detailed": (
                    f"{node_name}の{sector_label_ja}方向を確認しています。"
                    f"OCR候補として {ocr_summary_ja} が検出されています。"
                    f"{image_reference_ja}"
                ),
                "very_detailed": (
                    f"{node_name}の{sector_label_ja}方向に関する詳細な仮説明です。"
                    f"この説明は、後でVLMによる画像理解に置き換える予定です。"
                    f"現在はsector画像とOCR候補を入力として保持しており、"
                    f"OCR候補は {ocr_summary_ja} です。{image_reference_ja}"
                ),
            },
            "en": {
                "brief": (
                    f"Temporary description for the {sector_label_en} direction at {node_name}. "
                    f"OCR candidates: {ocr_summary_en}."
                ),
                "detailed": (
                    f"This is a temporary description for the {sector_label_en} direction at {node_name}. "
                    f"OCR candidates detected in this sector: {ocr_summary_en}. "
                    f"{image_reference_en}"
                ),
                "very_detailed": (
                    f"This is a detailed temporary description for the {sector_label_en} direction at {node_name}. "
                    f"It will later be replaced by VLM-generated visual descriptions. "
                    f"The current placeholder uses sector image references and OCR candidates. "
                    f"OCR candidates: {ocr_summary_en}. {image_reference_en}"
                ),
            },
            "confidence": 0.45 if ocr_texts else 0.3,
            "review_required": True,
        }

class OpenAIDescriptionProvider(DescriptionProvider):
    """
    OpenAI Vision API用のProviderスタブ。
    今回はまだ実APIを呼ばず、未実装エラーを出す。
    次のステップで実装する。
    """

    def __init__(self, api_key: str | None, prompt_text: str):
        self.api_key = api_key
        self.prompt_text = prompt_text

    def generate_sector_description(
        self,
        node_id: str,
        node_name: str,
        sector: str,
        sector_label_ja: str,
        sector_label_en: str,
        sector_image_url: str | None,
        ocr_results: list[dict],
    ) -> dict:
        raise NotImplementedError(
            "OpenAIDescriptionProvider is not implemented yet. "
            "Use DESCRIPTION_PROVIDER=dummy for now."
        )

from settings import (
    get_description_provider_name,
    get_openai_api_key,
    get_sector_description_prompt_path,
)


def load_prompt_text() -> str:
    prompt_path = get_sector_description_prompt_path()

    if not prompt_path.exists():
        return ""

    return prompt_path.read_text(encoding="utf-8")


def create_description_provider() -> DescriptionProvider:
    provider_name = get_description_provider_name()

    if provider_name == "dummy":
        return DummyDescriptionProvider()

    if provider_name == "openai":
        return OpenAIDescriptionProvider(
            api_key=get_openai_api_key(),
            prompt_text=load_prompt_text(),
        )

    raise ValueError(f"Unknown DESCRIPTION_PROVIDER: {provider_name}")