import logging
from telegram import Update, constants, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
# from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datepicker_detailed import DetailedTelegramCalendar, LSTEP
from timepicker import InlineTimepicker
from time import sleep
import datetime
from config import bot_data
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from locator import location_render
from utils import SessionCM, Poller
from models import init_db, insert_chat_log, DataclassFactory, get_user, add_user
from state import UserState

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

db_interface = "sqlite+pysqlite:///mydb.db"
Session = scoped_session(
    sessionmaker(
        autocommit=False, autoflush=False, bind=create_engine(db_interface, echo=False)
    )
)
location_poller = Poller(db_interface)


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
        ["/register", "/locator"],
        ["/calender"],
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
        user_id = int(update.effective_user.id)
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
    user = get_user(session=session, user_id=update.effective_user.id)
    if not user:
        user = add_user(session=session, user_id=update.effective_user.id)
    user = UserState(user, session)
    if user.state not in ["initial", "running"]:
        msg = str(user.run(update.effective_message.text))
        if user.state == "configured":
            msg = str(user.run(location_poller))
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=msg
        )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(session=session, user_id=update.effective_user.id)
    if not user:
        user = add_user(session=session, user_id=update.effective_user.id)

    user = UserState(user, session)
    msg = user.run()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


async def locator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(context.args)
    user = get_user(session=session, user_id=update.effective_user.id)
    if not user:
        msg = "You need to register the location service first. /register"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    elif UserState(user, session).state == "running":
        nickname, day = context.args
        timeframe = [f"{day} 00:00:00", f"{day} 23:59:59"]
        picture = location_render(session, owner_id=user.user_id, nickname='Наталья', timeframe=timeframe, length=100)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=picture)
        return




inline_timepicker = InlineTimepicker()


# async def calender(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     inline_timepicker.init(
#         datetime.time(12),
#         datetime.time(0),
#         datetime.time(23),
#         chat_id=update.effective_chat.id,
#     )
#     reply_markup = inline_timepicker.get_keyboard(update.effective_chat.id)
#     await context.bot.send_message(chat_id=update.effective_chat.id,
#                                    text='test',
#                                    reply_markup=reply_markup)
#
#
#
# async def calender_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     handle_result = inline_timepicker.handle(chat_id=query.message.chat.id, callback_data=query)
#     print(handle_result)
#     if handle_result is not None:
#         await context.bot.edit_message_text(text=str(handle_result),
#                                             chat_id=query.message.chat.id,
#                                             message_id=query.message.message_id)
#     else:
#         keyboard = inline_timepicker.get_keyboard(update.effective_chat.id)
#         await context.bot.edit_message_reply_markup(chat_id=query.from_user.id,
#                                                     message_id=query.message.message_id,
#                                                     reply_markup=keyboard)

async def calender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    calendar, step = DetailedTelegramCalendar().build()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Select {LSTEP[step]}",
                                   reply_markup=calendar)


async def calender_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    result, key, step = DetailedTelegramCalendar().process(query.data)
    if not result and key:
        await context.bot.edit_message_text(f"Select {LSTEP[step]}",
                                            query.message.chat.id,
                                            query.message.message_id,
                                            reply_markup=key)
    elif result:
        await context.bot.edit_message_text(f"You selected {result}",
                                            query.message.chat.id,
                                            query.message.message_id)


if __name__ == "__main__":
    with SessionCM(Session) as session:
        init_db(session)
    # location_poller.start()
    bot_data = bot_data
    bot = BotData(*bot_data)
    reset_message()
    application = ApplicationBuilder().token(bot.TOKEN).build()

    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", bot_help)
    feedback_handler = CommandHandler("feedback", feedback)
    message_handler = CommandHandler("message", message)
    register_handler = CommandHandler("register", register)
    locator_handler = CommandHandler("locator", locator)
    calender_handler = CommandHandler("calender", calender)
    receiver_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), receiver)
    callback_handler = CallbackQueryHandler(calender_callback)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(feedback_handler)
    application.add_handler(message_handler)
    application.add_handler(receiver_handler)
    application.add_handler(register_handler)
    application.add_handler(locator_handler)
    application.add_handler(calender_handler)
    application.add_handler(callback_handler)
    application.add_handler(unknown_handler)

    application.run_polling()
    location_poller.stop()
    print(inline_timepicker.data)
