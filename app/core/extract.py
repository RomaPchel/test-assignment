import base64
import json
import re
import time
from pathlib import Path
from typing import Tuple
import anthropic
from PIL import Image

from app.models.schemas import ExtractedDocument, PipelineTrace
from app.utils.business_rules import EXTRACTION_TIMEOUT_SECONDS
from app.utils.config import MODEL_NAME, ANTHROPIC_API_KEY
from app.utils.errors import ExtractionFailure, MalformedModelOutput
from app.utils import business_rules as rules

MEDIA_TYPE_MAP = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif"
}

def _read_prompt(prompt_name: str) -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.txt"
    return prompt_path.read_text(encoding="utf-8")

def _load_image_as_base64(image_path: str) -> Tuple[str, str]:
    with Image.open(image_path) as img:
        fmt = img.format.lower() if img.format else "jpeg"
        media_type = MEDIA_TYPE_MAP.get(fmt, "image/jpeg")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    return image_data, media_type

def _parse_json_response(response_text: str) -> dict:
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if not json_match:
        raise MalformedModelOutput("No JSON object found in response")

    json_str = json_match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        cleaned_json = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return json.loads(cleaned_json)

async def extract_document(file_path: str) -> Tuple[ExtractedDocument, PipelineTrace]:
    start_time = time.time()
    file_ext = Path(file_path).suffix.lower()
    is_image = file_ext in rules.IMAGE_EXTENSIONS

    system_prompt = _read_prompt("extract_document")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        if is_image:
            image_data, media_type = _load_image_as_base64(file_path)
            message = client.messages.create(
                model=MODEL_NAME,
                max_tokens=2000,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                        {"type": "text", "text": "Extract structured information from this document image."}
                    ]
                }],
                timeout=EXTRACTION_TIMEOUT_SECONDS
            )
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
            message = client.messages.create(
                model=MODEL_NAME,
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": f"<user_input>\n{text_content}\n</user_input>\n\nExtract structured information from this document."}],
                timeout=EXTRACTION_TIMEOUT_SECONDS
            )
    except Exception as e:
        raise ExtractionFailure(f"API error: {str(e)}")

    try:
        data = _parse_json_response(message.content[0].text)
        extracted_doc = ExtractedDocument(**data)
    except json.JSONDecodeError as e:
        raise MalformedModelOutput(f"JSON parse error at position {e.pos}: {e.msg}")
    except Exception as e:
        raise MalformedModelOutput(f"Parse error: {str(e)}")

    latency_ms = (time.time() - start_time) * 1000
    trace = PipelineTrace(
        step="extract_document",
        model=MODEL_NAME,
        model_version=MODEL_NAME,
        latency_ms=latency_ms
    )

    return extracted_doc, trace
