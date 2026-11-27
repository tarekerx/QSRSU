"""Read a photo of a multiple-choice question into structured data.

Uses the local INT4-quantized Qwen/Qwen3.5-4B model exported to OpenVINO and
run on the CPU, so nothing leaves the machine and no API key is needed.
"""

import json
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from bot.config import VLM_DEVICE, VLM_MODEL_PATH

logger = logging.getLogger(__name__)

# The instruction we give the model. It must be unambiguous: we want JSON and
# nothing else, because we parse the answer with json.loads() afterwards.
_PROMPT = """You are an exam-question reader. Look at the photo of a multiple-choice question and extract its content.

Return ONLY a JSON object, in strict JSON. No markdown code fences, no explanation, no extra text.

The JSON object must have exactly these three keys:
{
  "question_text": "<the question text exactly as written, including any geometry labels and numbers>",
  "options": {"A": "<option A text>", "B": "<option B text>"},
  "user_answer": "<the letter of the option the user marked, or null if nothing is marked>"
}

Rules:
- "options" maps each option letter that appears in the image to its text.
- "user_answer" is a single uppercase letter, or null.
- Output valid JSON only."""

# Module-level singleton for the loaded pipeline.
#
# Why load it only once? Building a VLMPipeline reads the whole model from disk
# and builds the inference graph, which takes minutes on a CPU. Doing that per
# photo would make every upload unusable, so we build it once and reuse the
# same in-memory model for every request.
_pipeline = None


def _get_pipeline():
    """Return the shared VLMPipeline, creating it on first use (lazy import)."""
    global _pipeline
    if _pipeline is None:
        # Imported here (not at module top) so that `import ai.transcriber`
        # works even before openvino-genai is installed, e.g. for unit tests.
        import openvino_genai as ov_genai

        logger.info("Loading VLM from %s on %s (once)", VLM_MODEL_PATH, VLM_DEVICE)
        _pipeline = ov_genai.VLMPipeline(VLM_MODEL_PATH, VLM_DEVICE)
    return _pipeline


def check_vlm() -> bool:
    """Verify the model folder exists and that the pipeline can be built.

    Called once at bot startup. Building the pipeline here also warms the model
    up, so the first photo does not pay the multi-minute load cost.
    """
    if not Path(VLM_MODEL_PATH).is_dir():
        logger.warning(
            "VLM model directory not found: %s (photo transcription disabled)",
            VLM_MODEL_PATH,
        )
        return False

    try:
        _get_pipeline()

    except Exception:
        logger.exception(
            "Could not build the VLMPipeline from %s (photo transcription disabled)",
            VLM_MODEL_PATH,
        )
        return False

    return True


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
    if not isinstance(options, dict) or not options:
        return None
    for letter, text in options.items():
        if not isinstance(letter, str) or not isinstance(text, str):
            return None

    user_answer = data.get("user_answer")
    if user_answer is not None and not isinstance(user_answer, str):
        return None
    # Normalize: "" / "  " mean "nothing marked", and letters are uppercase.
    if isinstance(user_answer, str):
        user_answer = user_answer.strip().upper() or None

    return {
        "question_text": question_text.strip(),
        "options": options,
        "user_answer": user_answer,
    }


def _result_text(result) -> str:
    """Extract plain text from whatever openvino_genai's generate() returned."""
    texts = getattr(result, "texts", None)  # DecodedResults.texts
    if texts:
        return texts[0]
    return str(result)


def transcribe_question(image_path: str) -> dict | None:
    """Read the question in `image_path`.

    Returns {"question_text": str, "options": dict, "user_answer": str | None}
    or None if the image could not be read into valid JSON.
    """
    try:
        import openvino as ov
        import openvino_genai as ov_genai

        # OpenVINO works on tensors, so the PIL image becomes a numpy array
        # (H, W, 3) and then an ov.Tensor. Newer openvino_genai re-exports
        # Tensor; older versions only have it in the openvino package.
        tensor_cls = getattr(ov_genai, "Tensor", None) or ov.Tensor
        image = Image.open(image_path).convert("RGB")
        image_tensor = tensor_cls(np.array(image))

        pipe = _get_pipeline()
        # max_new_tokens caps the answer length; do_sample=False keeps the
        # output deterministic, which matters when we expect strict JSON.
        config = ov_genai.GenerationConfig(max_new_tokens=512, do_sample=False)
        try:
            result = pipe.generate(
                _PROMPT, images=[image_tensor], generation_config=config
            )
        except TypeError:
            # Older openvino_genai versions take the image and options directly.
            result = pipe.generate(
                _PROMPT, image=image_tensor, max_new_tokens=512, do_sample=False
            )
    except Exception:
        # Model missing, out of memory, corrupt image... all mean "cannot read".
        logger.exception("Transcription failed for %s", image_path)
        return None

    raw = _result_text(result)
    data = _parse_json(raw)
    if data is None:
        logger.warning("Model did not return valid JSON: %.300s", raw)
        return None

    validated = _validate(data)
    if validated is None:
        logger.warning("Model returned unexpected JSON shape: %.300s", raw)
    return validated
