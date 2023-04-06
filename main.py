import logging
from telegram import Update, constants, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from time import sleep
from config import bot_data
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from utils import SessionCM
from models import init_db, insert_chat_log, DataclassFactory

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

db_interface = "sqlite+pysqlite:///mydb.db"
Session = scoped_session(
    sessionmaker(
        autocommit=False, autoflush=False, bind=create_engine(db_interface, echo=False)
    )
)


class BotData:
    ESCAPED_CHARS = [char for char in "_*[]()~`>#+-=|{}.!"]

    def __init__(
        self, commands, descriptions, token, owner, owner_id
    ) -> None:
        self.COMMANDS = commands
        self.DESCRIPTIONS = descriptions
        self.TOKEN = token
        self.OWNER = escape(owner)
        self.owner_id = owner_id
        # self.TEXT = text
        # self.TEXT_TO_FUNCTION = dict(zip(text, functions))

    @property
    def descriptions(self) -> str:
        result = ""
        for i in range(0, len(self.COMMANDS)):
            if i + 1 < len(self.DESCRIPTIONS):
                result += f"*{self.COMMANDS[i]}* \- {self.DESCRIPTIONS[i]};\n\n"
            else:
                result += f"*{self.COMMANDS[i]}* \- {self.DESCRIPTIONS[i]}\."
        return result


is_entering_subject = False
subject = ""
is_entering_message = False
message_text = ""
is_message = False
token = ""


def reset_message():
    global is_entering_subject
    global subject
    global is_entering_message
    global message_text
    global is_message
    is_entering_subject = False
    subject = ""
    is_entering_message = False
    message_text = ""
    is_message = False


def contains(i1, i2):
    return any([i in i2 for i in i1])


def escape(to_escape):
    result = to_escape
    esc_chars = BotData.ESCAPED_CHARS
    for char in result:
        if char in esc_chars:
            result = result.replace(char, "\\" + char)
            esc_chars.remove(char)
    return result


async def send_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    time_to_wait: float,
    action: constants.ChatAction,
):
    logging.info(f"Function 'send_action': {update.effective_message.text}")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=action, pool_timeout=time_to_wait
    )
    sleep(time_to_wait)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_message()
    reply_keyboard = [
        ["/help", "/start"],
        ["/feedback", "/message"],
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard)
    logging.info(f"Function 'start': {update.effective_message.text}")
    record = DataclassFactory(update, context).run()
    with SessionCM(Session) as session:
        insert_chat_log(session, record)
    await update.message.reply_text(
        text="I'm a bot, type *Help* if you don't know how to use me\.",
        reply_markup=markup,
        parse_mode=constants.ParseMode.MARKDOWN_V2,
    )


async def bot_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_message()
    logging.info(f"Function 'bot_help': {update.effective_message.text}")
    record = DataclassFactory(update, context).run()
    with SessionCM(Session) as session:
        insert_chat_log(session, record)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"This is *@{bot.OWNER}*'s bot, that helps him to get feedback\.",
        parse_mode=constants.ParseMode.MARKDOWN_V2,
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"*List of commands:*\n{bot.descriptions}",
        parse_mode=constants.ParseMode.MARKDOWN_V2,
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Also you can use keyboard",
        parse_mode=constants.ParseMode.MARKDOWN_V2,
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_message()
    logging.info(
        f"Function 'unknown': {update.effective_message.text}, {context.args}"
    )
    record = DataclassFactory(update, context).run()
    with SessionCM(Session) as session:
        insert_chat_log(session, record)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I don't know this command"
    )


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_entering_subject
    global is_message
    logging.info(f"Function 'feedback': {update.effective_message.text}")
    record = DataclassFactory(update, context).run()
    with SessionCM(Session) as session:
        insert_chat_log(session, record)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="You're going to write a feedback message",
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Write your message subject:"
    )
    is_entering_subject = True
    is_message = False


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_entering_subject
    global is_message
    logging.info(f"Function 'message': {update.effective_message.text}")
    record = DataclassFactory(update, context).run()
    with SessionCM(Session) as session:
        insert_chat_log(session, record)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="You're going to write a message"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Write your message subject:"
    )
    is_entering_subject = True
    is_message = True


async def receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_entering_message
    global message_text
    global is_entering_subject
    global subject
    logging.info(f"Function 'receiver': {update.effective_message}")
    record = DataclassFactory(update, context).run()
    with SessionCM(Session) as session:
        insert_chat_log(session, record)
    if is_message:
        if is_entering_subject:
            is_entering_subject = False
            subject = update.message.text
            subject = escape(subject)
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="Good. Now write your message:"
            )
            is_entering_message = True
        elif is_entering_message:
            is_entering_message = False
            message_text = update.message.text
            message_text = escape(message_text)
            user = update.message.from_user.username
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Your message was sent to {bot.OWNER}",
            )
            await context.bot.send_message(
                chat_id=bot.owner_id,
                text=f"*Message from: @{escape(user)}*\n\nSubject:\n{subject}\n\nMessage:\n{message_text}",
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                disable_notification=True,
            )
            reset_message()
    else:
        if is_entering_subject:
            is_entering_subject = False
            subject = update.message.text
            subject = escape(subject)
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="Good. Now write your message:"
            )
            is_entering_message = True
        elif is_entering_message:
            is_entering_message = False
            message_text = update.message.text
            message_text = escape(message_text)
            await context.bot.send_message(
                chat_id=bot.owner_id,
                text=f"*‼️FEEDBACK‼️*\n\n🔴 Subject: 🔴\n{subject}\n\n🔴 Message: 🔴\n{message_text}",
                parse_mode=constants.ParseMode.MARKDOWN_V2,
            )
            await send_action(
                update, context, "Thanks a lot!", 1, constants.ChatAction.TYPING
            )
            reset_message()
        else:
            await text(update, context)


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Function 'text': {update.effective_message.text}")
    await context.bot.send_message(
                chat_id=update.effective_chat.id, text="Noted!"
            )


if __name__ == "__main__":
    with SessionCM(Session) as session:
        init_db(session)

    bot_data = bot_data
    bot = BotData(*bot_data)
    reset_message()
    application = ApplicationBuilder().token(bot.TOKEN).build()

    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", bot_help)
    feedback_handler = CommandHandler("feedback", feedback)
    message_handler = CommandHandler("message", message)
    receiver_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), receiver)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(feedback_handler)
    application.add_handler(message_handler)
    application.add_handler(receiver_handler)
    application.add_handler(unknown_handler)

    application.run_polling()
