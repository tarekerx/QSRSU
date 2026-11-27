"""Entry point for the QSRSU Telegram bot."""

from telegram.ext import ApplicationBuilder, MessageHandler, filters

from ai.transcriber import check_vlm
from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers import echo_handler
from bot.photo_handler import photo_handler
from db.database import init_db


def main() -> None:
    """Start the bot."""
    init_db()

    # Load/verify the local VLM once, before polling starts. This is the slow
    # part (minutes on CPU), and it only logs a warning on failure so the bot
    # still runs - photos would just come back as "couldn't read".
    check_vlm()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.run_polling()


if __name__ == "__main__":
    main()
