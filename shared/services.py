import platform
import shlex
from asyncio.proactor_events import _ProactorBasePipeTransport
from datetime import datetime
from enum import IntEnum
from functools import wraps
from logging import Logger
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pytz
import telebot
from kink import di
from telebot import TeleBot, types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_filters import \
    AdvancedCustomFilter as AsyncAdvancedCustomFilter
from telebot.asyncio_filters import IsDigitFilter as AsyncIsDigitFilter
from telebot.asyncio_filters import \
    SimpleCustomFilter as AsyncSimpleCustomFilter
from telebot.asyncio_filters import StateFilter as AsyncStateFilter
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot.custom_filters import (AdvancedCustomFilter, IsDigitFilter,
                                    SimpleCustomFilter, StateFilter)

from app_config import Configuration
from shared.utils import *


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        di[Logger].error(exception)


class AsyncRestrictAccessFilter(AsyncSimpleCustomFilter):
    key = "restrict"

    async def check(self, message: types.Message):
        return (
            di[Configuration]["restrict_access"]
            and message.from_user.id in di[Configuration]["list_of_users"]
        )


class AsyncActionsCallbackFilter(AsyncAdvancedCustomFilter):
    key = "config"

    async def check(self, call: types.CallbackQuery, config: CallbackDataFilter):
        return config.check(query=call)


class ActionsCallbackFilter(AdvancedCustomFilter):
    key = "config"

    def check(self, call: types.CallbackQuery, config: CallbackDataFilter):
        return config.check(query=call)


class RestrictAccessFilter(SimpleCustomFilter):
    key = "restrict"

    def check(self, message: types.Message):
        return (
            di[Configuration]["restrict_access"]
            and message.from_user.id in di[Configuration]["list_of_users"]
        )


class BotFactory:
    def __init__(
        self,
        restrict_access_filter,
        state_filter,
        is_digit_filter,
        actions_callback_filter,
        bot_instance,
    ):
        bot_instance.add_custom_filter(restrict_access_filter)
        bot_instance.add_custom_filter(state_filter)
        bot_instance.add_custom_filter(is_digit_filter)
        bot_instance.add_custom_filter(actions_callback_filter)
        self._instance = bot_instance

    def create_bot(self):
        return self._instance


class Action(IntEnum):
    date = 1
    outflow = 2
    inflow = 3
    category = 4
    account = 5
    memo = 6
    cancel = 10
    done = 11
    start = 100
    quick_end = 200
    category_list = 300
    category_end = 301
    sw_category_list = 400
    sw_set_group = 401
    sw_set_currency = 402


class TextUtil:
    def format_data(self, user_data: Dict[str, str]) -> str:
        """Helper function for formatting the gathered user info."""
        data = []
        for key, value in user_data.items():
            if key in ("Outflow", "Inflow") and value != "":
                data.append(
                    f"*{key}* : " +
                    di[Configuration]["currency"] + f" {int(value):,}"
                )
            else:
                data.append(f"*{key}* : {value}")
        return "\n".join(data).join(["\n", "\n"])

    def text_splitter(text):
        lex = shlex.shlex(text)
        lex.quotes = '"'
        lex.whitespace_split = True
        lex.commenters = ""
        return list(lex)


class DateUtil:
    def date_today() -> str:
        ph_tz = pytz.timezone('Asia/Manila')
        today = datetime.datetime.now(tz=ph_tz)
        today = str(today.strftime("%m/%d/%y"))
        return today


class TransactionData(dict[str, Any]):
    def reset(self):
        self["Date"] = ""
        self["Outflow"] = ""
        self["Inflow"] = ""
        self["Category"] = ""
        self["Account"] = ""
        self["Memo"] = ""


class KeyboardUtil:
    def create_save_keyboard(callback_data: str):
        return types.InlineKeyboardMarkup(
            keyboard=[
                [types.InlineKeyboardButton(
                    text="💾 Save", callback_data=callback_data)]
            ]
        )

    def create_default_options_keyboard():
        """
        Menu keyboard for start command
        """
        filtered_actions = list(
            filter(lambda x: x <= Action.cancel, list(Action)))
        keyboard = [
            filtered_actions[i: i + 2] for i in range(0, len(filtered_actions), 2)
        ]
        for i, x in enumerate(keyboard):
            for j, k in enumerate(x):
                keyboard[i][j] = types.InlineKeyboardButton(
                    k.name.capitalize(),
                    callback_data=di[CallbackData].new(action_id=int(k)),
                )
        return types.InlineKeyboardMarkup(keyboard)

    def create_options_keyboard():
        """
        Menu keyboard for updating transaction data
        """
        keyboard = []
        for action in list(filter(lambda x: x <= Action.done, list(Action))):
            if action == Action.done or action == Action.cancel:
                btnList = [
                    types.InlineKeyboardButton(
                        text=action.name.capitalize(),
                        callback_data=di[CallbackData].new(
                            action_id=int(action)),
                    )
                ]
            else:
                data = di[TransactionData][action.name.capitalize()]
                if action == Action.outflow or action == Action.inflow:
                    displayData = (
                        f"{action.name.capitalize()}: "
                        + (di[Configuration]["currency"] + f" {data}")
                        if data != ""
                        else action.name.capitalize()
                    )
                else:
                    displayData = (
                        f"{action.name.capitalize()}: " + data
                        if data != ""
                        else action.name.capitalize()
                    )
                btnList = [
                    types.InlineKeyboardButton(
                        text=f"{displayData}",
                        callback_data=di[CallbackData].new(
                            action_id=int(action)),
                    )
                ]
            keyboard.append(btnList)
        return types.InlineKeyboardMarkup(keyboard)

    def create_sw_friend_keyboard(friends, column_size=3):
        keyboard = []
        row = []
        for friend in friends:
            name = f"{get_friend_full_name(friend)}"
            row.append(types.InlineKeyboardButton(
                name, callback_data=friend.getId()))
            if len(row) == column_size:
                keyboard.append(row)
                row = []
        keyboard.append(row)
        return types.InlineKeyboardMarkup(keyboard)

    def create_sw_keyboard(categories, column_size=2):
        keyboard = []
        row = []
        for category in categories:
            row.append(types.InlineKeyboardButton(
                category, callback_data=category))
            if len(row) == column_size:
                keyboard.append(row)
                row = []
        keyboard.append(row)
        return types.InlineKeyboardMarkup(keyboard)

    def create_subcategory_keyboard(category_name, column_size=3):
        subcategories = get_subcategories(di["sw_categories"], category_name)
        return KeyboardUtil.create_sw_keyboard(subcategories, column_size)


def silence_event_loop_closed(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except RuntimeError as e:
            if str(e) != "Event loop is closed":
                raise

    return wrapper


if platform.system() == "Windows":
    _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(
        _ProactorBasePipeTransport.__del__
    )
