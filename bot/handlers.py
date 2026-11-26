from telegram import Update
from telegram.ext import ContextTypes


async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user's text message back to them."""
    if update.message and update.message.text:
        await update.message.reply_text(update.message.text)
