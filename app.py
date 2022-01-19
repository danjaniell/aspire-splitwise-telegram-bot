import os
import shlex
import logging
from turtle import clear
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_filters import SimpleCustomFilter
import asyncio
from telebot import types
from telebot import util
from datetime import datetime
from functools import wraps
from typing import Dict
from zoneinfo import ZoneInfo

import gspread
import toml

from tools import (
    create_calendar,
    create_category_inline,
    get_accounts,
    get_all_categories,
    handle_category_inline,
    process_calendar_selection,
    separate_callback_data,
    append_trx,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

config = toml.load("config.toml")

user_data = {
    'Date': '',
    'Outflow': '',
    'Inflow': '',
    'Category': '',
    'Account': '',
    'Memo': '',
}


def clear_user_data() -> None:
    global user_data
    empty_user_data = {key: '' for key in user_data}
    user_data = empty_user_data


def get_config() -> dict[str, str]:
    configuration = {
        'port': '',
        'token': '',
        'update_mode': '',
        'app_name': '',
    }

    ON_HEROKU = os.environ.get('ON_HEROKU')

    if ON_HEROKU:
        # get the heroku port
        configuration['port'] = int(os.environ.get('PORT', '8443'))
        configuration['token'] = os.environ.get('TOKEN')
        configuration['update_mode'] = os.environ.get('UPDATE_MODE')
        configuration['app_name'] = os.environ.get('HEROKU_APP_NAME')
    else:
        configuration['port'] = config["app"]["port"]
        configuration['token'] = config["telegram"]["telegram_token"]
        configuration['update_mode'] = config["app"]["update_mode"]
        configuration['app_name'] = config["app"]["app_name"]

    return configuration


tokens = get_config()


class Restrict_Access(SimpleCustomFilter):
    key = 'restrict'

    @staticmethod
    async def check(message: telebot.types.Message):
        return (
            config["telegram"]["restrict_access"]
            and message.from_user.id in config["telegram"]["list_of_users"]
        )


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        logger.error(exception)


bot = AsyncTeleBot(token=tokens.get('token'), parse_mode='MARKDOWN',
                   exception_handler=ExceptionHandler())

# initialize gspread
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

client = gspread.service_account(
    filename=config["gsheet"]["gsheet_api_key_filepath"], scopes=scope
)

sheet = client.open_by_key(config["gsheet"]["gsheet_worksheet_id"])

trx_categories = get_all_categories(sheet)
trx_accounts = get_accounts(sheet)
trx_accounts = [item for sublist in trx_accounts for item in sublist]


def format_data(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    data = []
    for key, value in user_data.items():
        if key in ("Outflow", "Inflow") and value != "":
            data.append(f"*{key}* : " +
                        config["currency"] + f" {int(value):,}")
        elif value != "":
            data.append(f"*{key}* : {value}")
    return "\n".join(data).join(["\n", "\n"])


@bot.message_handler(regexp='^(D|d)one$', restrict=True)
async def done(message):
    """Display gathered info"""
    user_data["Date"] = datetime.today().strftime('%m/%d/%Y')
    await bot.send_message(
        message.chat.id, f"\[Received Data]\n{format_data(user_data)}")

    await upload(message)


async def upload(message):
    """Upload info to aspire google sheet"""
    upload_data = [
        user_data["Date"],
        user_data["Outflow"],
        user_data["Inflow"],
        user_data["Category"],
        user_data["Account"],
        user_data["Memo"],
    ]
    append_trx(sheet, upload_data)
    clear_user_data()
    await bot.reply_to(message, f"✅ Transaction Saved\n")


@bot.message_handler(regexp='^(A|a)dd(I|i)nc.+$', restrict=True)
async def income_trx(message):
    """Add income transaction using Today's date, Inflow Amount and Memo"""
    text = message.text
    result = []

    for i in shlex.split(text):
        result.append(i)
    del result[0]

    paramCount = len(result)
    if paramCount != 2:
        await bot.reply_to(
            message, f"Expected 2 parameters, received {paramCount}: [{result}]")
        return
    else:
        x, y = result
        user_data["Inflow"] = x
        user_data["Memo"] = y

    await done(message)


@bot.message_handler(regexp='^(A|a)dd(E|e)xp.+$', restrict=True)
async def expense_trx(message):
    """Add expense transaction using Today's date, Outflow Amount and Memo"""
    text = message.text
    result = []

    for i in shlex.split(text):
        result.append(i)
    del result[0]

    paramCount = len(result)
    if paramCount != 2:
        await bot.reply_to(
            message, f"Expected 2 parameters, received {paramCount}: [{result}]")
        return
    else:
        x, y = result
        user_data["Outflow"] = x
        user_data["Memo"] = y

    await done(message)


@bot.message_handler(commands=['start'])
async def command_start(message):
    await bot.reply_to(message, "This is still in progress.")


def main() -> None:
    """Run the bot."""
    bot.add_custom_filter(Restrict_Access())
    asyncio.run(bot.polling())


if __name__ == "__main__":
    main()
