"""Solve a stored quiz question with Gemini."""

import json
import logging

from google import genai
from google.genai import errors

from bot.config import GEMINI_API_KEY
from db.database import get_question

logger = logging.getLogger(__name__)

_MODEL = "gemini-3.5-flash-lite"

# The client is created once, at import time.
#
# Why not per request? The client holds the API key and a reusable HTTP
# connection pool. Building one for every question would redo that setup and
# open fresh connections each time - slower and pointless.
client = genai.Client(api_key=GEMINI_API_KEY)


def _build_prompt(question_text: str, options: list[str]) -> str:
    """Build the text prompt from the row's fields only (never the image)."""
    if options:
        options_block = "\n".join(
            f"{chr(ord('A') + index)}) {option}" for index, option in enumerate(options)
        )
    else:
        options_block = "(no options were read from the photo)"

    # We only send text because the transcriber already did the vision work:
    # the question and its options are in the DB, so re-uploading the photo
    # would cost more tokens and add nothing.
    return f"""You are solving a multiple-choice quiz question.

Question:
{question_text}

Options:
{options_block}

Return ONLY a JSON object, in strict JSON. No markdown code fences, no explanation outside the JSON, no extra text.

The JSON object must have exactly these two keys:
{{
  "correct_answer": "<the correct option, copied exactly as written in the options>",
  "explanation": "<a short explanation of why that answer is correct>"
}}

Output valid JSON only."""


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
    """Check the parsed JSON has the shape we need, else return None.

    Why validate instead of trusting the model? A generative model can return
    "null", a list or the wrong types at any time. Without these checks the bad
    value would reach the DB and break the reply, far from the real cause.
    """
    if not isinstance(data, dict):
        return None

    correct_answer = data.get("correct_answer")
    if not isinstance(correct_answer, str) or not correct_answer.strip():
        return None

    explanation = data.get("explanation")
    if not isinstance(explanation, str):
        return None

    return {
        "correct_answer": correct_answer.strip(),
        "explanation": explanation.strip(),
    }


def _ask_gemini(prompt: str) -> str:
    """Send the prompt to Gemini and return the raw text answer.

    The SDK call is one method: `models.generate_content` posts the prompt to
    the model named in `model` and returns a response object whose `.text`
    holds the generated answer.

    For free-tier accounts an unavailable model raises a
    `google.genai.errors.ClientError` (e.g. 404). We log it and re-raise so the
    caller's retry loop treats it as a failure and returns ``None``.
    """
    try:
        response = client.models.generate_content(model=_MODEL, contents=prompt)
        return response.text or ""
    except errors.ClientError as e:
        logger.exception("Gemini request failed - model may be unavailable: %s", e)
        raise


def solve_and_grade(question_id: int) -> dict | None:
    """Solve the stored question with Gemini.

    **Side-effect free** - this function reads the DB row and calls Gemini.
    It does *not* write anything back, so callers must persist the result.

    There is no grading here any more: the bot no longer reads a student
    answer from the photo, so there is nothing to compare against.

    Returns {"correct_answer": str, "explanation": str}
    or ``None`` if the question could not be solved.
    """
    row = get_question(question_id)
    if row is None or not row["question_text"]:
        return None

    # `options` is stored as JSON text in the DB, so parse it back to a list.
    try:
        options = json.loads(row["options"]) if row["options"] else []
    except (TypeError, json.JSONDecodeError):
        options = []
    if not isinstance(options, list):
        options = []

    prompt = _build_prompt(row["question_text"], options)

    # One attempt, and one retry if the answer is unusable. `except Exception`
    # covers google.genai errors (bad key, quota, network) as well.
    solution = None
    for attempt in (1, 2):
        try:
            raw = _ask_gemini(prompt)
            data = _parse_json(raw)
            validated = _validate(data) if data is not None else None
            if validated is not None:
                solution = validated
                break
            logger.warning("Attempt %d: unusable model output: %.300s", attempt, raw)
        except Exception:
            logger.exception("Attempt %d: Gemini request failed", attempt)

    if solution is None:
        return None

    return {
        "correct_answer": solution["correct_answer"],
        "explanation": solution["explanation"],
    }