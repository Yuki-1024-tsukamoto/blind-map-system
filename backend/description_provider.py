import base64
import json
from pathlib import Path
from typing import Any

from openai import OpenAI
from google import genai
from google.genai import types

from settings import (
    get_description_provider_name,
    get_gemini_api_key,
    get_gemini_description_model,
    get_openai_api_key,
    get_openai_description_model,
    get_sector_description_prompt_path,
)


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
        sector_image_path: str | None = None,
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
        sector_image_path: str | None = None,
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
            "landmarks": [],
            "confidence": 0.45 if ocr_texts else 0.3,
            "review_required": True,
        }


def image_file_to_data_url(image_path: Path) -> str:
    """
    ローカル画像をOpenAI APIへ渡すため、Base64 data URLに変換する。
    """
    suffix = image_path.suffix.lower()
    if suffix in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif suffix == ".png":
        mime_type = "image/png"
    elif suffix == ".webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"

    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


class OpenAIDescriptionProvider(DescriptionProvider):
    """
    OpenAI Vision API用のProvider。
    初期段階では1sectorテスト用に使う。
    """

    def __init__(self, api_key: str | None, prompt_text: str, model: str):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        self.client = OpenAI(api_key=api_key)
        self.prompt_text = prompt_text
        self.model = model

    def generate_sector_description(
        self,
        node_id: str,
        node_name: str,
        sector: str,
        sector_label_ja: str,
        sector_label_en: str,
        sector_image_url: str | None,
        ocr_results: list[dict[str, Any]],
        sector_image_path: str | None = None,
    ) -> dict[str, Any]:
        if not sector_image_path:
            raise ValueError("sector_image_path is required for OpenAIProvider.")

        image_path = Path(sector_image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Sector image not found: {image_path}")

        image_data_url = image_file_to_data_url(image_path)

        ocr_texts = [
            str(result.get("text", ""))
            for result in ocr_results
            if result.get("text")
        ]

        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "ja": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "brief": {"type": "string"},
                        "detailed": {"type": "string"},
                        "very_detailed": {"type": "string"},
                    },
                    "required": ["brief", "detailed", "very_detailed"],
                },
                "en": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "brief": {"type": "string"},
                        "detailed": {"type": "string"},
                        "very_detailed": {"type": "string"},
                    },
                    "required": ["brief", "detailed", "very_detailed"],
                },
                "landmarks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": [
                                    "toilet",
                                    "exit",
                                    "reception",
                                    "stairs",
                                    "elevator",
                                    "escalator",
                                    "exhibit",
                                    "room",
                                    "sign",
                                    "other",
                                ],
                            },
                            "canonical_ja": {"type": "string"},
                            "canonical_en": {"type": "string"},
                            "aliases": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "navigational_value": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                            },
                        },
                        "required": [
                            "category",
                            "canonical_ja",
                            "canonical_en",
                            "aliases",
                            "navigational_value",
                        ],
                    },
                },
                "confidence": {"type": "number"},
                "review_required": {"type": "boolean"},
            },
            "required": [
                "ja",
                "en",
                "landmarks",
                "confidence",
                "review_required",
            ],
        }

        user_text = (
            f"{self.prompt_text}\n\n"
            f"node_id: {node_id}\n"
            f"node_name: {node_name}\n"
            f"sector: {sector}\n"
            f"sector_label_ja: {sector_label_ja}\n"
            f"sector_label_en: {sector_label_en}\n"
            f"OCR candidates: {ocr_texts}\n"
            "Generate the required JSON only."
        )

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_text},
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": "low",
                        },
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "sector_description",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        return json.loads(response.output_text)
    
class GeminiDescriptionProvider(DescriptionProvider):
    """
    Gemini Vision API用のProvider。
    まずは1sectorテスト用に使う。
    """

    def __init__(self, api_key: str | None, prompt_text: str, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.prompt_text = prompt_text
        self.model = model

    def generate_sector_description(
        self,
        node_id: str,
        node_name: str,
        sector: str,
        sector_label_ja: str,
        sector_label_en: str,
        sector_image_url: str | None,
        ocr_results: list[dict],
        sector_image_path: str | None = None,
    ) -> dict:
        if not sector_image_path:
            raise ValueError("sector_image_path is required for GeminiProvider.")

        image_path = Path(sector_image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Sector image not found: {image_path}")

        suffix = image_path.suffix.lower()
        if suffix in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif suffix == ".png":
            mime_type = "image/png"
        elif suffix == ".webp":
            mime_type = "image/webp"
        else:
            mime_type = "image/jpeg"

        image_bytes = image_path.read_bytes()

        ocr_texts = [
            str(result.get("text", ""))
            for result in ocr_results
            if result.get("text")
        ]

        schema = {
            "type": "object",
            "properties": {
                "ja": {
                    "type": "object",
                    "properties": {
                        "brief": {"type": "string"},
                        "detailed": {"type": "string"},
                        "very_detailed": {"type": "string"},
                    },
                    "required": ["brief", "detailed", "very_detailed"],
                },
                "en": {
                    "type": "object",
                    "properties": {
                        "brief": {"type": "string"},
                        "detailed": {"type": "string"},
                        "very_detailed": {"type": "string"},
                    },
                    "required": ["brief", "detailed", "very_detailed"],
                },
                "landmarks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "canonical_ja": {"type": "string"},
                            "canonical_en": {"type": "string"},
                            "aliases": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "navigational_value": {"type": "string"},
                        },
                        "required": [
                            "category",
                            "canonical_ja",
                            "canonical_en",
                            "aliases",
                            "navigational_value",
                        ],
                    },
                },
                "confidence": {"type": "number"},
                "review_required": {"type": "boolean"},
            },
            "required": [
                "ja",
                "en",
                "landmarks",
                "confidence",
                "review_required",
            ],
        }

        user_text = (
            f"{self.prompt_text}\n\n"
            f"node_id: {node_id}\n"
            f"node_name: {node_name}\n"
            f"sector: {sector}\n"
            f"sector_label_ja: {sector_label_ja}\n"
            f"sector_label_en: {sector_label_en}\n"
            f"OCR candidates: {ocr_texts}\n"
            "Return only JSON that follows the schema."
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                user_text,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=schema,
            ),
        )

        return json.loads(response.text)


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
            model=get_openai_description_model(),
        )

    if provider_name == "gemini":
        return GeminiDescriptionProvider(
            api_key=get_gemini_api_key(),
            prompt_text=load_prompt_text(),
            model=get_gemini_description_model(),
        )

    raise ValueError(f"Unknown DESCRIPTION_PROVIDER: {provider_name}")