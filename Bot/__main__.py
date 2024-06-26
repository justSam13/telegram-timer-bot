import os
import datetime

from time import sleep
from Storage import Storage
from Logger import setlogger
from dotenv import load_dotenv
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.client import Client
from constants import CALLBACK_DICT, ERROR_CMD_MSG, ZERO_TIME_DELTA, TIMER_FORMAT, EVENT_ENDED_FORMAT, POLLING_INTERVAL, CANCEL_MSG, ERROR_CANCEL_MSG, EVENT_CANCELLED_FORMAT, CMD_START, CMD_DEFAULT, CMD_CANCEL, CMD_TIMER, BOT_NAME, FOOTER

load_dotenv()
logger = setlogger(BOT_NAME)
storage = Storage(logger)

app = Client(
    BOT_NAME,
    api_id=os.environ.get('API_ID', ""),
    api_hash=os.environ.get('API_HASH', ""),
    bot_token=os.environ.get("BOT_TOKEN", ""),
)

@app.on_message(filters.command(CMD_START))
async def start(_, message: Message):
    await message.reply(
        text=CALLBACK_DICT[CMD_START].get_msg(),
        reply_markup=CALLBACK_DICT[CMD_START].get_markup()
    )


@app.on_message(filters.command(CMD_CANCEL))
async def cancel(_, message: Message):
    try:
        _, event_name = message.text.split(' ', 1)
        if not storage.delete_event(message.chat.id, event_name):
            raise Exception(ERROR_CANCEL_MSG)
        await message.reply(
            text=CANCEL_MSG.format(event_name=event_name),
        )
    except:
        await message.reply(
            text=ERROR_CANCEL_MSG,
        )


@app.on_message(filters.command(CMD_TIMER))
async def start_timer(_, message: Message):
    """The main method for the timer message"""
    try:
        # [command, date, time, event_name]
        _, date, time, event_name = message.text.split(' ', 3)
        deadline = storage.add_event(
            message.chat.id, event_name, f"{date} {time}")
        logger.info(f"Event {event_name} added for {deadline}")

        time_left: datetime.timedelta = deadline - datetime.datetime.now()
        if time_left < ZERO_TIME_DELTA:
            await message.reply(
                text=EVENT_ENDED_FORMAT.format(event_name=event_name),
            )
            return

        event_string = get_event_string(time_left, event_name)
        msg = await app.send_message(message.chat.id, event_string)

        await refresh_msg(msg, deadline, event_name)

    except (ValueError, TypeError) as e:
        logger.error(str(e))
        await message.reply(text=ERROR_CMD_MSG)


async def refresh_msg(msg: Message, deadline: datetime.datetime, event_name: str):
    """Updates the event message until it is pass the deadline"""
    sleep_time = max(POLLING_INTERVAL, 5)
    while True:
        sleep(sleep_time)
        time_left = deadline - datetime.datetime.now()
        if not time_left.days and time_left.seconds < 10: sleep_time = 1
        if storage.get_events(msg.chat.id, event_name) is None:
            format = EVENT_CANCELLED_FORMAT
            logger.info(f"Event {event_name} was cancelled")
            break
        if time_left.total_seconds() < 0:
            format = EVENT_ENDED_FORMAT
            logger.info(f"Event {event_name} has ended")
            break
        event_string = get_event_string(time_left, event_name)
        await msg.edit(event_string)
        # logger.info(f"Event {event_name} updated for {time_left}")
    await msg.edit(format.format(event_name=event_name))


def get_event_string(time: datetime.timedelta, event_name: str):
    """Get the string format for event message"""
    return TIMER_FORMAT.format(time=get_time_string(time), event_name=event_name, footer = FOOTER)


def get_time_string(time: datetime.timedelta):
    time_string = ""
    if time.days: time_string += f"{time.days}**d** "
    minutes, seconds = divmod(time.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours: time_string += f"{hours}**h** {minutes}**m** {seconds}**s**"
    elif minutes: time_string += f"{minutes}**m** {seconds}**s**"
    else: time_string += f"{seconds}**s**"
    return time_string

@app.on_callback_query()
async def callback(_, query) -> None:
    msgpack = CALLBACK_DICT.get(query.data, CALLBACK_DICT[CMD_DEFAULT])

    # Get the message
    text = msgpack.get_msg()
    markup = msgpack.get_markup()

    # Update the message
    await query.edit_message_text(text, reply_markup=markup)
    logger.info(f"Callback {query.data} is called")

if __name__ == "__main__":
    logger.info("Starting the bot")
    app.run()
