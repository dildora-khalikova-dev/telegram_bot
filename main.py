from typing import Final, Dict
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import os

# ================= CONFIG =================
TOKEN: Final = os.getenv("TOKEN")
ADMIN_ID: Final = 7750500022

CONTACT_USERNAME: Final = "@Apteka_dostavka_24_7"
CONTACT_PHONE: Final = "+998937747133"
# =========================================

user_states: Dict[int, str] = {}
user_orders: Dict[int, Dict] = {}
admin_reply_state: Dict[int, int] = {}

# ================= KEYBOARDS ==============
main_keyboard = ReplyKeyboardMarkup(
    [
        ["📄 Retsept yuklash"],
        ["🚚 Yetkazib berish"],
        ["📞 Aloqa"],
    ],
    resize_keyboard=True
)

recipe_choice_keyboard = ReplyKeyboardMarkup(
    [
        ["📝 Dorini nomini yozish"],
        ["📸 Retsept rasmini yuklash"],
        ["⬅️ Ortga"],
    ],
    resize_keyboard=True
)

location_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📍 Lokatsiyani yuborish", request_location=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

phone_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ================= START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states.pop(user_id, None)
    user_orders.pop(user_id, None)

    await update.message.reply_text(
        "Assalomu alaykum! 👋\n"
        "Dostavka botga xush kelibsiz.",
        reply_markup=main_keyboard
    )

# ================= TEXT ===================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = user_states.get(user_id)

    if text == "📄 Retsept yuklash":
        user_states[user_id] = "CHOOSE_RECIPE_TYPE"
        user_orders[user_id] = {}
        await update.message.reply_text(
            "Qanday yubormoqchisiz?",
            reply_markup=recipe_choice_keyboard
        )
        return

    if text == "📝 Dorini nomini yozish":
        user_states[user_id] = "WAIT_DRUG_NAME"
        await update.message.reply_text("✍️ Dorining nomini yozing:")
        return

    if state == "WAIT_DRUG_NAME":
        user_orders[user_id]["drug_name"] = text
        user_states[user_id] = "WAIT_LOCATION"
        await update.message.reply_text(
            "📍 Manzilingizni yuboring:",
            reply_markup=location_keyboard
        )
        return

    if text == "📸 Retsept rasmini yuklash":
        user_states[user_id] = "WAIT_RECIPE"
        await update.message.reply_text("📸 Retsept rasmini yuklang.")
        return

    if text == "🚚 Yetkazib berish":
        await update.message.reply_text(
            f"Bizga murojaat qilmoqchimisiz?\n\n"
            f"👉 Telegram: {CONTACT_USERNAME}\n"
            f"📞 Telefon: {CONTACT_PHONE}"
        )
        return

    if text == "📞 Aloqa":
        await update.message.reply_text(
            f"Bizga murojaat qilmoqchimisiz?\n\n"
            f"👉 Telegram: {CONTACT_USERNAME}\n"
            f"📞 Telefon: {CONTACT_PHONE}"
        )
        return

    await update.message.reply_text("❗ Iltimos, menyudan foydalaning.")

# ================= PHOTO ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_states.get(user_id) != "WAIT_RECIPE":
        return

    user_orders[user_id]["recipe"] = update.message.photo[-1].file_id
    user_states[user_id] = "WAIT_LOCATION"

    await update.message.reply_text(
        "📍 Manzilingizni yuboring:",
        reply_markup=location_keyboard
    )

# ================= LOCATION ===============
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_states.get(user_id) != "WAIT_LOCATION":
        return

    user_orders[user_id]["location"] = update.message.location
    user_states[user_id] = "WAIT_PHONE"

    await update.message.reply_text(
        "📞 Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard
    )

# ================= CONTACT ================
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_states.get(user_id) != "WAIT_PHONE":
        return

    user_orders[user_id]["phone"] = update.message.contact.phone_number
    user_states[user_id] = "DONE"

    await update.message.reply_text(
        "✅ Buyurtma qabul qilindi!",
        reply_markup=main_keyboard
    )

    await send_order_to_admin(context, user_id)

# ============== SEND TO ADMIN ==============
async def send_order_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    order = user_orders.get(user_id)
    if not order:
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Reply", callback_data=f"reply:{user_id}")]]
    )

    loc = order.get("location")
    if loc:
        await context.bot.send_location(
            ADMIN_ID, loc.latitude, loc.longitude
        )

    text = (
        f"🆕 YANGI BUYURTMA\n\n"
        f"👤 User ID: {user_id}\n"
        f"📞 Telefon: {order.get('phone')}\n"
        f"💊 Dori: {order.get('drug_name', 'Retsept orqali')}"
    )

    if "recipe" in order:
        await context.bot.send_photo(
            ADMIN_ID, order["recipe"], caption=text, reply_markup=keyboard
        )
    else:
        await context.bot.send_message(
            ADMIN_ID, text, reply_markup=keyboard
        )

# ============== ADMIN =====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split(":")[1])
    admin_reply_state[query.from_user.id] = user_id
    await query.message.reply_text("✍️ Javob yozing:")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_id = admin_reply_state.get(ADMIN_ID)
    if not user_id:
        return

    await context.bot.send_message(
        user_id, f"📩 Admindan:\n{update.message.text}"
    )
    del admin_reply_state[ADMIN_ID]

# ================= MAIN ===================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.User(ADMIN_ID), handle_text))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.User(ADMIN_ID), handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_admin_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.run_polling()

if __name__ == "__main__":
    main()

