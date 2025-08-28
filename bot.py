from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

TOKEN = "8244380773:AAGZE3T74x-IYHxDqJFja_j4vaGdpsni4Kk"
ADMIN_ID = 564401901   # Replace with your numeric ID

# Products with their access links (can be file, code, or Google Drive link etc.)
PRODUCTS = {
    "p1": {"name": "Product A", "price": 100, "access": "🔑 Here is your access to Product A: https://google.com/a"},
    "p2": {"name": "Product B", "price": 200, "access": "🔑 Here is your access to Product B: https://example.com/b"},
    "p3": {"name": "Product C", "price": 300, "access": "🔑 Here is your access to Product C: https://example.com/c"},
}

# Store selected product
user_product = {}

# Store unverified transactions
pending_txns = {}

# --- Ensure transactions.txt exists ---
if not os.path.exists("transactions.txt"):
    with open("transactions.txt", "w") as f:
        f.write("📂 Transactions Log\n\n")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products_text = "\n".join([f"{key}: {p['name']} – ₹{p['price']}" for key, p in PRODUCTS.items()])
    await update.message.reply_text(
        "👋 Welcome to the Payment Bot!\n\n"
        "Available products:\n\n"
        f"{products_text}\n\n"
        "👉 Use /buy <product_code> to select.\nExample: /buy p1"
    )

# /buy
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide a product code.\nExample: /buy p1")
        return

    product_code = context.args[0]
    if product_code not in PRODUCTS:
        await update.message.reply_text("❌ Invalid product code. Try again.")
        return

    product = PRODUCTS[product_code]
    user_product[update.effective_user.id] = product_code

    # Send text + QR image
    await update.message.reply_photo(
        photo=open("qr.png", "rb"),   # <- Your BharatPe QR image here
        caption=(
            f"🛒 You selected: {product['name']} (₹{product['price']})\n\n"
            f"💳 Pay via UPI: *800846077@bharatpe*\n"
            "📌 After payment, confirm with:\n"
            "/confirm <UTR>"
        ),
        parse_mode="Markdown"
    )

# /confirm
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide your transaction ID.\nExample: /confirm 1234567890")
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or "NoUsername"
    txn_id = context.args[0]

    if user_id not in user_product:
        await update.message.reply_text("⚠️ Please select a product first using /buy.")
        return

    product_code = user_product[user_id]
    product = PRODUCTS[product_code]

    # Save as pending
    pending_txns[txn_id] = {"user_id": user_id, "username": username, "product_code": product_code}

    with open("transactions.txt", "a") as f:
        f.write(f"UserID: {user_id}, Username: @{username}, Product: {product['name']}, Txn: {txn_id}, Status: PENDING\n")

    await update.message.reply_text(
        f"✅ Thank you! Your payment for *{product['name']}* is received.\n"
        f"Txn ID: `{txn_id}`\n"
        "We will verify and send your product access shortly."
    )

# /approve (Admin only) → Approve a txn and send access
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("⚠️ Usage: /approve <txn_id>")
        return

    txn_id = context.args[0]
    if txn_id not in pending_txns:
        await update.message.reply_text("❌ Transaction not found in pending list.")
        return

    txn = pending_txns.pop(txn_id)
    user_id = txn["user_id"]
    product_code = txn["product_code"]
    product = PRODUCTS[product_code]

    # Update file with APPROVED status
    with open("transactions.txt", "a") as f:
        f.write(f"UserID: {user_id}, Product: {product['name']}, Txn: {txn_id}, Status: APPROVED\n")

    # Send product access to the user
    await context.bot.send_message(chat_id=user_id, text=product["access"])
    await update.message.reply_text(f"✅ Approved Txn {txn_id} for user {txn['username']} and sent product access.")

# /list → Show pending
async def list_txns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    if not pending_txns:
        await update.message.reply_text("📂 No pending transactions.")
        return

    msg = "📋 Pending Transactions:\n\n"
    for txn_id, txn in pending_txns.items():
        msg += f"Txn: {txn_id}, User: @{txn['username']}, Product: {PRODUCTS[txn['product_code']]['name']}\n"

    await update.message.reply_text(msg)


# /approved → Show approved transactions from file
async def approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    try:
        with open("transactions.txt", "r") as f:
            lines = [line for line in f.readlines() if "APPROVED" in line]
    except FileNotFoundError:
        lines = []

    if not lines:
        await update.message.reply_text("✅ No approved transactions yet.")
        return

    msg = "📋 Approved Transactions:\n\n" + "".join(lines[-10:])  # show last 10
    await update.message.reply_text(msg)


# /users → Show all paid users
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    try:
        with open("transactions.txt", "r") as f:
            lines = [line for line in f.readlines() if "APPROVED" in line]
    except FileNotFoundError:
        lines = []

    if not lines:
        await update.message.reply_text("✅ No paid users yet.")
        return

    msg = "👥 Paid Users:\n\n"
    for line in lines:
        msg += line
    await update.message.reply_text(msg)


# Run bot
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("list", list_txns))
    app.add_handler(CommandHandler("approved", approved))
    app.add_handler(CommandHandler("users", users))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
