import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import requests
from pymongo import MongoClient

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient('your_mongodb_connection_string')
db = client['adrino_bot']
users_collection = db['users']

# Bot owner ID and log group
OWNER_ID = 123456789
LOG_GROUP_ID = -1001234567890

# States for ConversationHandler
LINK_SHORTENING = range(1)

# Start command with an image URL and caption, including inline buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})
        await context.bot.send_message(LOG_GROUP_ID, f"User started bot: {user_id}")

    image_url = "https://example.com/your_image.jpg"  # Specify the image URL here
    caption_text = (
        "Welcome to the Adrino Link Creator Bot!\n\n"
        "Use /SetApi to set up your Adrino API key, and then send any link to shorten it. "
        "You can also use /track <shortened_link> to track clicks."
    )

    # Create inline buttons
    keyboard = [
        [InlineKeyboardButton("Bot Updates", url="https://t.me/AlcyoneBots")],
        [InlineKeyboardButton("Support Chat", url="https://t.me/Alcyone_Support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send image with caption and inline buttons
    await update.message.reply_photo(photo=image_url, caption=caption_text, reply_markup=reply_markup)

# Set API command to save the Adrino API key
async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    api_key = update.message.text.split(" ", 1)[1] if len(update.message.text.split(" ", 1)) > 1 else None

    if not api_key:
        await update.message.reply_text("Please provide your Adrino API key after the /SetApi command.")
        return

    users_collection.update_one({"user_id": user_id}, {"$set": {"api_key": api_key}})
    await update.message.reply_text("API key saved! Now, send a link to shorten.")

# Link shortening handler
async def shorten_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    link = update.message.text

    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data or "api_key" not in user_data:
        await update.message.reply_text("Please set up your Adrino API key first using /SetApi.")
        return

    api_key = user_data["api_key"]
    shortened_link = shorten_with_adrino(api_key, link)

    if shortened_link:
        await update.message.reply_text(f"Here is your shortened link: {shortened_link}")
        await context.bot.send_message(LOG_GROUP_ID, f"User {user_id} shortened a link:\nOriginal: {link}\nShortened: {shortened_link}")
    else:
        await update.message.reply_text("Error shortening link, please try again.")

# Link shortening function
def shorten_with_adrino(api_key, link):
    url = "https://adrinolinks.com/api"
    response = requests.post(url, json={"api_key": api_key, "link": link})
    if response.status_code == 200:
        return response.json().get("shortened_link")
    return None

# Track link command
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /track <adrinolink>")
        return

    adrino_link = context.args[0]
    user_id = update.effective_user.id
    click_count = track_adrino_link_clicks(adrino_link, user_id)

    await update.message.reply_text(f"{adrino_link} has been clicked {click_count} time(s).")

# Link tracking function (placeholder)
def track_adrino_link_clicks(adrino_link, user_id):
    # Implementation for tracking would depend on Adrino's API
    return 1

# Stats command (owner only)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        user_count = users_collection.count_documents({})
        await update.message.reply_text(f"Total users: {user_count}")
    else:
        await update.message.reply_text("You're not authorized to use this command.")

# Broadcast command (owner only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("You're not authorized to use this command.")
        return
    
    message = update.message.text.split(" ", 1)[1] if len(update.message.text.split(" ", 1)) > 1 else None
    if not message and update.message.reply_to_message:
        message = update.message.reply_to_message.text

    if not message:
        await update.message.reply_text("Please provide a message to broadcast.")
        return
    
    users = users_collection.find({})
    for user in users:
        try:
            await context.bot.send_message(user["user_id"], message)
        except Exception as e:
            logger.error(f"Failed to send message to {user['user_id']}: {e}")
    
    await update.message.reply_text("Broadcast sent.")

# Main function to run the bot
def main():
    application = Application.builder().token("your_bot_token").build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("SetApi", set_api))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, shorten_link))
    application.add_handler(CommandHandler("track", track))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    application.run_polling()

if __name__ == "__main__":
    main()
