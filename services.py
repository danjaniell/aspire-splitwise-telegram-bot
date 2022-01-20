from telegram import replykeyboardmarkup
import app_logging
from app_config import Configuration
from datetime import datetime
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_filters import SimpleCustomFilter
from telebot.asyncio_filters import StateFilter
from telebot.asyncio_filters import IsDigitFilter
from telebot import types
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot.asyncio_filters import AdvancedCustomFilter
from telebot import types
from kink import inject, di
from enum import IntEnum
from zoneinfo import ZoneInfo
from typing import Dict


@inject
class Restrict_Access(SimpleCustomFilter):
    key = 'restrict'

    def __init__(self, config: Configuration):
        self._config = config

    @staticmethod
    async def check(message: types.Message):
        return (
            di[Configuration].values['restrict_access']
            and message.from_user.id in di[Configuration].values['list_of_users']
        )


class ActionsCallbackFilter(AdvancedCustomFilter):
    key = 'config'

    async def check(self, call: types.CallbackQuery, config: CallbackDataFilter):
        return config.check(query=call)


@inject
class MyTeleBot(AsyncTeleBot):
    Instance = None

    def __init__(self,
                 config: Configuration,
                 restrict_access_filter: Restrict_Access,
                 state_filter: StateFilter,
                 is_digit_filter: IsDigitFilter,
                 actions_callback_filter: ActionsCallbackFilter,
                 bot_instance: AsyncTeleBot):
        self._config = config
        self._restrict_access_filter = restrict_access_filter
        self._state_filter = state_filter
        self._is_digit_filter = is_digit_filter
        self._actions_callback_filter = actions_callback_filter

        bot_instance.add_custom_filter(self._restrict_access_filter)
        bot_instance.add_custom_filter(self._state_filter)
        bot_instance.add_custom_filter(self._is_digit_filter)
        bot_instance.add_custom_filter(self._actions_callback_filter)
        self.Instance = bot_instance


class Action(IntEnum):
    outflow = 1
    inflow = 2
    category = 3
    account = 4
    memo = 5
    end = 100
    start = 101
    quick_end = 102


@inject
class Formatting():
    def __init__(self, config: Configuration):
        self._config = config

    def format_data(self, user_data: Dict[str, str]) -> str:
        """Helper function for formatting the gathered user info."""
        data = []
        for key, value in user_data.items():
            if key in ('Outflow', 'Inflow') and value != '':
                data.append(f'*{key}* : ' +
                            self._config.values['currency'] + f' {int(value):,}')
            else:
                data.append(f'*{key}* : {value}')
        return '\n'.join(data).join(['\n', '\n'])


class DateUtil():
    def date_today() -> str:
        today = datetime.now(tz=ZoneInfo('Hongkong'))
        today = str(today.strftime('%m/%d/%y'))
        return today


class TransactionData():
    values = {
        'Date': '',
        'Outflow': '',
        'Inflow': '',
        'Category': '',
        'Account': '',
        'Memo': '',
    }

    def clear_transaction_data(self) -> None:
        empty_user_data = {key: '' for key in self.values}
        self.values = empty_user_data


class KeyboardUtil():
    def create_save_keyboard(callback_data: str):
        return types.InlineKeyboardMarkup(
            keyboard=[
                [
                    types.InlineKeyboardButton(
                        text='💾 Save',
                        callback_data=callback_data
                    )
                ]
            ]
        )

    def create_default_options_keyboard():
        keyboard = []
        for action in Action:
            if (action > Action.end):
                continue
            btnList = [
                types.InlineKeyboardButton(
                    text=action.name.capitalize(),
                    callback_data=di[CallbackData].new(action_id=int(action))
                )
            ]
            keyboard.append(btnList)
        return types.InlineKeyboardMarkup(keyboard)

    def create_options_keyboard():
        keyboard = []
        for action in Action:
            if (action > Action.end):
                continue
            elif(action == Action.end):
                btnList = [
                    types.InlineKeyboardButton(
                        text=action.name.capitalize(),
                        callback_data=di[CallbackData].new(
                            action_id=int(action))
                    )
                ]
            else:
                data = TransactionData.values[action.name.capitalize()]
                if action == Action.outflow or action == Action.inflow:
                    displayData = f'{action.name.capitalize()}: ' + \
                        (di[Configuration].values['currency'] +
                         f' {data}') if data != '' else action.name.capitalize()
                else:
                    displayData = f'{action.name.capitalize()}: ' + \
                        data if data != '' else action.name.capitalize()
                btnList = [
                    types.InlineKeyboardButton(
                        text=f"{displayData}",
                        callback_data=di[CallbackData].new(
                            action_id=int(action))
                    )
                ]
            keyboard.append(btnList)
        return types.InlineKeyboardMarkup(keyboard)
