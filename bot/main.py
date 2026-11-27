"""Entry point for the QSRSU Telegram bot."""

from telegram.ext import ApplicationBuilder, MessageHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers import echo_handler
from db.database import init_db


def main() -> None:
    """Start the bot."""
    init_db()
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))
    application.run_polling()


if __name__ == "__main__":
    main()
