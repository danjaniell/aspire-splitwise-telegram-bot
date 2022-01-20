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
from enum import IntEnum
from zoneinfo import ZoneInfo
from typing import Dict


class MyTeleBot():
    Instance = None

    def init(self):
        self.Instance = AsyncTeleBot(token=Configuration.values['token'],
                                     parse_mode='MARKDOWN',
                                     exception_handler=app_logging.ExceptionHandler())
        self.Instance.add_custom_filter(Restrict_Access())
        self.Instance.add_custom_filter(StateFilter(self.Instance))
        self.Instance.add_custom_filter(IsDigitFilter())
        self.Instance.add_custom_filter(ActionsCallbackFilter())


class Restrict_Access(SimpleCustomFilter):
    key = 'restrict'

    @staticmethod
    async def check(message: types.Message):
        return (
            Configuration.values.get['telegram']['restrict_access']
            and message.from_user.id in Configuration.values['telegram']['list_of_users']
        )


class Action(IntEnum):
    outflow = 1
    inflow = 2
    category = 3
    account = 4
    memo = 5
    start = 101
    end = 102
    quick_end = 103


class ActionsCallbackFilter(AdvancedCustomFilter):
    key = 'config'

    async def check(self, call: types.CallbackQuery, config: CallbackDataFilter):
        return config.check(query=call)


class Formatting():
    def format_data(user_data: Dict[str, str]) -> str:
        """Helper function for formatting the gathered user info."""
        data = []
        for key, value in user_data.items():
            if key in ('Outflow', 'Inflow') and value != '':
                data.append(f'*{key}* : ' +
                            Configuration.values['currency'] + f' {int(value):,}')
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
    actions = CallbackData('action_id', prefix='Action')

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

    def create_default_options_keyboard(self):
        keyboard = []
        for action in Action:
            if (action == Action.start):
                continue
            btnList = [
                types.InlineKeyboardButton(
                    text=action.name.capitalize(),
                    callback_data=self.actions.new(action_id=int(action))
                )
            ]
            keyboard.append(btnList)
        return types.InlineKeyboardMarkup(keyboard)

    def create_options_keyboard(self):
        keyboard = []
        for action in Action:
            if (action == Action.start):
                continue
            if (action == Action.end or action == Action.quick_end):
                btnList = [
                    types.InlineKeyboardButton(
                        text=action.name.capitalize(),
                        callback_data=self.actions.new(action_id=int(action))
                    )
                ]
            else:
                data = TransactionData.values[action.name.capitalize()]
                if action == Action.outflow or action == Action.inflow:
                    displayData = f'{action.name.capitalize()}: ' + \
                        (Configuration.values['currency'] +
                         f' {data}') if data != '' else action.name.capitalize()
                else:
                    displayData = f'{action.name.capitalize()}: ' + \
                        data if data != '' else action.name.capitalize()
                btnList = [
                    types.InlineKeyboardButton(
                        text=f"{displayData}",
                        callback_data=self.actions.new(action_id=int(action))
                    )
                ]
            keyboard.append(btnList)
        return types.InlineKeyboardMarkup(keyboard)
