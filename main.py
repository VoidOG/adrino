import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from pymongo import MongoClient

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

client = MongoClient("mongodb+srv://Cenzo:Cenzo123@cenzo.azbk1.mongodb.net/")
db = client['adrino_bot']
users_collection = db['users']

OWNER_ID = 6663845789
LOG_GROUP_ID = -1002183841044

LINK_SHORTENING = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ensure the bot only responds in direct messages (DMs)
    if update.message.chat.type != 'private':
        return  # Ignore messages from groups or channels

    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    profile_url = f"https://t.me/{username}" if username else f"tg://openmessage?user_id={user_id}"

    # Log user info when they start the bot
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})
        log_message = (
            f"User started the bot:\n"
            f"Name: {first_name}\n"
            f"User ID: {user_id}\n"
            f"Username: @{username}\n"
            f"Profile URL: {profile_url}"
        )
        await context.bot.send_message(LOG_GROUP_ID, log_message)

    image_url = "https://i.ibb.co/dWpzhvW/file-1538.jpg"
    caption_text = (
        "Welcome to the Adrino Link Creator Bot!\n\n"
        "Use /SetApi to set up your Adrino API key, and then send any link to shorten it. "
        "You can also use /track <shortened_link> to track clicks."
    )

    keyboard = [
        [InlineKeyboardButton("Bot Updates", url="https://t.me/AlcyoneBots")],
        [InlineKeyboardButton("Support Chat", url="https://t.me/Alcyone_Support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(photo=image_url, caption=caption_text, reply_markup=reply_markup)

async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ensure the bot only works in DM
    if update.message.chat.type != 'private':
        return  # Ignore messages from groups or channels

    user_id = update.effective_user.id
    api_key = update.message.text.split(" ", 1)[1] if len(update.message.text.split(" ", 1)) > 1 else None

    if not api_key:
        await update.message.reply_text("Please provide your Adrino API key after the /SetApi command.")
        return

    users_collection.update_one({"user_id": user_id}, {"$set": {"api_key": api_key}})
    await update.message.reply_text("API key saved! Now, send a link to shorten.")

async def shorten_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ensure the bot only works in DM
    if update.message.chat.type != 'private':
        return  # Ignore messages from groups or channels

    user_id = update.effective_user.id
    link = update.message.text

    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data or "api_key" not in user_data:
        await update.message.reply_text("Please set up your Adrino API key first using /SetApi.")
        return

    api_key = user_data["api_key"]
    alias = None
    if len(link.split(" ", 1)) > 1:
        alias = link.split(" ", 1)[1]  # Extract alias if available
        link = link.split(" ", 1)[0]  # The first part is the actual URL

    shortened_link = shorten_with_adrino(api_key, link, alias)

    if shortened_link:
        await update.message.reply_text(f"Here is your shortened link: {shortened_link}")
        await context.bot.send_message(LOG_GROUP_ID, f"User {user_id} shortened a link:\nOriginal: {link}\nShortened: {shortened_link}")
    else:
        await update.message.reply_text("Error shortening link, please try again.")

def shorten_with_adrino(api_key, link, alias=None):
    url = "https://adrinolinks.com/api"
    params = {
        "api": api_key,
        "url": link
    }

    if alias:
        params["alias"] = alias

    response = requests.get(url, params=params)
    if response.status_code == 200:
        json_data = response.json()
        return json_data.get("shortened_link")
    return None

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure the bot only works in DM
    if update.message.chat.type != 'private':
        return  # Ignore messages from groups or channels

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /track <adrinolink>")
        return

    adrino_link = context.args[0]
    user_id = update.effective_user.id
    click_count = track_adrino_link_clicks(adrino_link, user_id)

    await update.message.reply_text(f"{adrino_link} has been clicked {click_count} time(s).")

def track_adrino_link_clicks(adrino_link, user_id):
    # For now, returning a mock click count.
    return 1

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        user_count = users_collection.count_documents({})
        await update.message.reply_text(f"Total users: {user_count}")
    else:
        await update.message.reply_text("You're not authorized to use this command.")

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

def main():
    application = Application.builder().token("7577228032:AAEXXukC2MKgyab7_Br56vGtPm0NxuHlUNI").build()

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
