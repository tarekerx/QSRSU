"""Photo flow: save the image, then transcribe the question out of it."""

import asyncio
import json
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from ai.transcriber import transcribe_question
from bot.config import IMAGE_DIR
from db.database import create_question, delete_question, update_question

# Absolute images directory, built from this file's location so it always
# points at the project root regardless of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR_PATH = PROJECT_ROOT / IMAGE_DIR


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save an incoming photo and store the question read from it."""
    if not update.message or not update.message.photo:
        return

    # 1. Get the largest photo size's file_id (Telegram sends several sizes,
    #    and the last one in the list is the biggest / best quality).
    photo = update.message.photo[-1]
    file_id = photo.file_id
    user_id = update.effective_user.id

    question_id = None
    image_absolute_path = None
    try:
        # 2. Create the DB row FIRST with a placeholder image_path ("").
        # Why before saving the file? create_question() returns the new
        # auto-incrementing id, and we need that id to name the image file
        # (images/<id>.jpg). The DB row also guarantees a unique 1:1 link
        # between a question and its photo.
        question_id = create_question(telegram_user_id=user_id, image_path="")

        # 3. Ensure the images/ directory exists, then build absolute paths.
        IMAGE_DIR_PATH.mkdir(parents=True, exist_ok=True)
        image_filename = f"{question_id}.jpg"
        image_absolute_path = IMAGE_DIR_PATH / image_filename
        # The DB stores a relative path so the project stays portable.
        image_relative_path = f"{IMAGE_DIR}/{image_filename}"

        # Download the photo from Telegram's servers to that path.
        file_obj = await context.bot.get_file(file_id)
        await file_obj.download_to_drive(custom_path=image_absolute_path)

        # 4. Fill in the real image path now that the file exists on disk.
        update_question(question_id, image_path=image_relative_path)

        # 5. Ask the local model what the photo says. Model inference is
        #    CPU-bound and blocking, so run it in a worker thread to keep the
        #    bot responsive to other users while it runs.
        data = await asyncio.to_thread(transcribe_question, str(image_absolute_path))

        if data is None:
            # Nothing readable: keep the row (image + path are valid) and ask
            # for a better photo.
            await update.message.reply_text(
                "Couldn't read the question from this photo. Try a clearer image."
            )
            return

        # 6. Store the transcription. `options` is a dict, but the column is
        #    TEXT, so it is serialized to a JSON string here; reading it back
        #    is a plain json.loads().
        update_question(
            question_id,
            question_text=data["question_text"],
            options=json.dumps(data["options"], ensure_ascii=False),
            user_answer=data["user_answer"],
        )

        # 7. Show the user what was read so they can spot a bad extraction.
        lines = [f"Photo received (question #{question_id})."]
        lines.append(f"Question: {data['question_text'][:300]}")
        lines.extend(f"{letter}) {text}" for letter, text in data["options"].items())
        if data["user_answer"]:
            lines.append(f"Marked answer: {data['user_answer']}")
        await update.message.reply_text("\n".join(lines))

    except Exception:
        # Downloading or saving failed, so the row would point to a file that
        # doesn't exist. Roll back: delete the row (and any partial file) so
        # the DB stays consistent with the images/ folder.
        if question_id is not None:
            try:
                delete_question(question_id)
            except Exception:
                pass
        if image_absolute_path is not None:
            image_absolute_path.unlink(missing_ok=True)

        await update.message.reply_text(
            "Sorry, failed to download or save your photo. Please try again."
        )
