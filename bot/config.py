import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
IMAGE_DIR: str = os.getenv("IMAGE_DIR", "images")

# Local OpenVINO export of the Qwen3.5-4B vision model, e.g.
# "/home/<user>/models/Qwen3.5-4B". expanduser() lets "~/models/..." work too.
VLM_MODEL_PATH: str = os.path.expanduser(
    os.getenv("VLM_MODEL_PATH", "~/models/Qwen3.5-4B")
)
# Where the model runs. "CPU" is the safe default on a server without a GPU.
VLM_DEVICE: str = os.getenv("VLM_DEVICE", "CPU")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
