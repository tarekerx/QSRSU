"""Turn a photo of a quiz question into structured data.

Uses Groq's hosted vision model, so there is no local model to download or
load - the image is sent to the API and the answer comes back as text.
"""

import base64
import json
import logging
import time

from groq import Groq

from bot.config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# The vision model that reads the photo. Must be one Groq supports for images.
_MODEL = "qwen/qwen3.8-27b"

# The Groq client is created once, at import time.
#
# Why not per request? The client holds the API key, a reusable HTTP connection
# pool and timeout/retry settings. Building one for every photo would redo all
# that setup and open fresh connections each time - slower and pointless.
client = Groq(api_key=GROQ_API_KEY)

# The instruction we send together with the image. It must be unambiguous: we
# want JSON and nothing else, because we parse the answer with json.loads().
_PROMPT = """You are an exam-question reader. Look at the photo of a multiple-choice quiz question.

Return ONLY a JSON object, in strict JSON. No markdown code fences, no explanation, no extra text.

The JSON object must have exactly these two keys:
{
  "question_text": "<the question text exactly as written>",
  "options": ["<first option>", "<second option>", "..."]
}

Rules:
- "options" is a plain list of strings, in the order they appear in the photo.
- Do not try to answer the question or mention what the student marked.
- Output valid JSON only."""


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that chat models add out of habit."""
    text = text.strip()
    if text.startswith("```"):
        # Drop the opening line ("```" or "```json"), then the closing fence.
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        text = text.rstrip()
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _parse_json(raw: str):
    """Turn the model's text answer into a Python object, or None."""
    cleaned = _strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: keep only the outermost {...} in case the model wrapped the
    # JSON in a sentence ("Here is the JSON: {...}").
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _validate(data) -> dict | None:
    """Check the parsed JSON has exactly the shape we need, else return None.

    Why validate instead of trusting the model? A generative model can return
    "null", a string, a list, or wrong types at any time - especially on a
    blurry photo. Without these checks the bad value would travel into the DB
    and crash json.dumps()/the UI later, far from the real cause.
    """
    if not isinstance(data, dict):
        return None

    question_text = data.get("question_text")
    if not isinstance(question_text, str) or not question_text.strip():
        return None

    options = data.get("options")
    if not isinstance(options, list):
        return None
    if not all(isinstance(option, str) for option in options):
        return None

    return {
        "question_text": question_text.strip(),
        "options": options,
    }


def _call_model(image_b64: str) -> str:
    """Send the image to Groq and return the model's raw text answer.

    The SDK call is a normal chat completion: the `content` list mixes a text
    block (our prompt) with an image block. Groq accepts the photo inline as a
    "data:image/jpeg;base64,..." URL, so no file upload step is needed.
    """
    response = client.chat.completions.create(
        model=_MODEL,
        # temperature=0 makes the answer as repeatable as possible, which
        # matters when we expect strict JSON.
        temperature=0,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content or ""


def transcribe_question(image_path: str) -> dict | None:
    """Read the quiz in `image_path`.

    Returns {"question_text": str, "options": list[str]}
    or None if the photo could not be read into valid JSON.
    """
    try:
        # The API wants the raw bytes, so read the file and base64-encode it.
        with open(image_path, "rb") as image_file:
            image_b64 = base64.b64encode(image_file.read()).decode("ascii")
    except OSError:
        logger.exception("Could not read image %s", image_path)
        return None

    # One attempt, and if anything goes wrong one retry after a short pause.
    # Network hiccups and HTTP 429 rate limits are usually gone a moment later;
    # `except Exception` covers groq.APIError, RateLimitError and friends.
    for attempt in (1, 2):
        try:
            raw = _call_model(image_b64)
            data = _parse_json(raw)
            validated = _validate(data) if data is not None else None
            if validated is not None:
                return validated
            logger.warning("Attempt %d: unusable model output: %.300s", attempt, raw)
        except Exception:
            logger.exception("Attempt %d: Groq request failed", attempt)

        if attempt == 1:
            time.sleep(2)

    return None