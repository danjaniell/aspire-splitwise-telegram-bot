import os
import shlex
import logging
import telebot
from enum import IntEnum
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_filters import SimpleCustomFilter
from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.asyncio_filters import StateFilter
from telebot.asyncio_filters import IsDigitFilter
import asyncio
from telebot import types
from datetime import datetime
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

config = toml.load('config.toml')

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
        configuration['port'] = os.environ.get('PORT', '8443')
        configuration['token'] = os.environ.get('TOKEN', 'token')
        configuration['update_mode'] = os.environ.get('UPDATE_MODE', 'polling')
        configuration['app_name'] = os.environ.get(
            'HEROKU_APP_NAME', 'heroku_app_name')
    else:
        configuration['port'] = config['app']['port']
        configuration['token'] = config['telegram']['telegram_token']
        configuration['update_mode'] = config['app']['update_mode']
        configuration['app_name'] = config['app']['app_name']

    return configuration


tokens = get_config()


class Restrict_Access(SimpleCustomFilter):
    key = 'restrict'

    @staticmethod
    async def check(message: telebot.types.Message):
        return (
            config['telegram']['restrict_access']
            and message.from_user.id in config['telegram']['list_of_users']
        )


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        logger.error(exception)


bot = AsyncTeleBot(token=tokens.get('token'), parse_mode='MARKDOWN',
                   exception_handler=ExceptionHandler())

# initialize gspread
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
]

client = gspread.service_account(
    filename=config['gsheet']['gsheet_api_key_filepath'], scopes=scope
)

sheet = client.open_by_key(config['gsheet']['gsheet_worksheet_id'])

trx_categories = get_all_categories(sheet)
trx_accounts = get_accounts(sheet)
trx_accounts = [item for sublist in trx_accounts for item in sublist]


actions = CallbackData('action_id', prefix='Action')


class ActionsCallbackFilter(AdvancedCustomFilter):
    key = 'config'

    async def check(self, call: types.CallbackQuery, config: CallbackDataFilter):
        return config.check(query=call)


class Action(IntEnum):
    outflow = 1
    inflow = 2
    category = 3
    account = 4
    memo = 5
    start = 101
    end = 102
    quick_end = 103


def default_options_keyboard():
    keyboard = []
    for action in Action:
        if (action == Action.start):
            continue
        btnList = [
            types.InlineKeyboardButton(
                text=action.name.capitalize(),
                callback_data=actions.new(action_id=int(action))
            )
        ]
        keyboard.append(btnList)
    return types.InlineKeyboardMarkup(keyboard)


def options_keyboard():
    keyboard = []
    for action in Action:
        if (action == Action.start):
            continue
        if (action == Action.end or action == Action.quick_end):
            btnList = [
                types.InlineKeyboardButton(
                    text=action.name.capitalize(),
                    callback_data=actions.new(action_id=int(action))
                )
            ]
        else:
            data = user_data[action.name.capitalize()]
            if action == Action.outflow or action == Action.inflow:
                displayData = f'{action.name.capitalize()}: ' + \
                    (config['currency'] +
                     f' {data}') if data != '' else action.name.capitalize()
            else:
                displayData = f'{action.name.capitalize()}: ' + \
                    data if data != '' else action.name.capitalize()
            btnList = [
                types.InlineKeyboardButton(
                    text=f"{displayData}",
                    callback_data=actions.new(action_id=int(action))
                )
            ]
        keyboard.append(btnList)
    return types.InlineKeyboardMarkup(keyboard)


def save_keyboard(callback_data: str):
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


def format_data(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    data = []
    for key, value in user_data.items():
        if key in ('Outflow', 'Inflow') and value != '':
            data.append(f'*{key}* : ' +
                        config['currency'] + f' {int(value):,}')
        else:
            data.append(f'*{key}* : {value}')
    return '\n'.join(data).join(['\n', '\n'])


def date_today() -> str:
    today = datetime.now(tz=ZoneInfo('Hongkong'))
    today = str(today.strftime('%m/%d/%y'))
    return today


@ bot.message_handler(state='*', commands=['cancel', 'q'])
async def command_cancel(message):
    """
    Cancel transaction from any state
    """
    await bot.send_message(message.chat.id, 'Transaction cancelled.')
    await bot.current_states.finish(message.chat.id)


@ bot.message_handler(state=[Action.outflow, Action.inflow], is_digit=False)
async def invalid_amt(message):
    await bot.reply_to(message, 'Please enter a number')


async def quick_save(message):
    await bot.set_state(message.from_user.id, Action.quick_end)
    await bot.send_message(message.chat.id,
                           '\[Received Data]' + f'\n{format_data(user_data)}',
                           reply_markup=save_keyboard('quick_save'))


async def upload(message):
    """Upload info to aspire google sheet"""
    upload_data = [
        user_data['Date'],
        user_data['Outflow'],
        user_data['Inflow'],
        user_data['Category'],
        user_data['Account'],
        user_data['Memo'],
    ]
    append_trx(sheet, upload_data)
    clear_user_data()
    await bot.reply_to(message, '✅ Transaction Saved\n')


@ bot.message_handler(regexp='^(A|a)dd(I|i)nc.+$', restrict=True)
async def income_trx(message):
    """Add income transaction using Today's date, Inflow Amount and Memo"""
    clear_user_data()
    text = message.text
    result = list(shlex.split(text))

    del result[0]

    paramCount = len(result)
    if paramCount != 2:
        await bot.reply_to(
            message, f'Expected 2 parameters, received {paramCount}: [{result}]')
        return
    else:
        inflow, memo = result
        user_data['Date'] = date_today()
        user_data['Inflow'] = inflow
        user_data['Memo'] = memo

    await quick_save(message)


@ bot.message_handler(regexp='^(A|a)dd(E|e)xp.+$', restrict=True)
async def expense_trx(message):
    """Add expense transaction using Today's date, Outflow Amount and Memo"""
    clear_user_data()
    text = message.text
    result = list(shlex.split(text))

    del result[0]

    paramCount = len(result)
    if paramCount != 2:
        await bot.reply_to(
            message, f'Expected 2 parameters, received {paramCount}: [{result}]')
        return
    else:
        outflow, memo = result
        user_data['Date'] = date_today()
        user_data['Outflow'] = outflow
        user_data['Memo'] = memo

    await quick_save(message)


async def item_selected(action: Action, user_id, message_id):
    await bot.set_state(user_id, action)

    data = user_data[action.name.capitalize()]
    if action == Action.outflow or action == Action.inflow:
        displayData = (config['currency'] +
                       f' {data}') if data != '' else '\'\''
    else:
        displayData = data if data != '' else '\'\''

    text = f'\[Current Value: ' + f' *{displayData}*]' + '\n' + \
        f'Enter {action.name.capitalize()} : '
    await bot.edit_message_text(chat_id=user_id, message_id=message_id,
                                text=text, reply_markup=save_keyboard('save'))


@ bot.callback_query_handler(func=None, config=actions.filter(), state=Action.start, restrict=True)
async def actions_callback(call: types.CallbackQuery):
    callback_data: dict = actions.parse(callback_data=call.data)
    actionId = int(callback_data['action_id'])
    action = Action(actionId)
    user_id = call.from_user.id
    message_id = call.message.message_id

    await item_selected(action, user_id, message_id)


@ bot.message_handler(state=Action.outflow, restrict=True)
async def get_outflow(message):
    user_data['Outflow'] = message.text


@ bot.callback_query_handler(func=lambda c: c.data == 'save')
async def save_callback(call: types.CallbackQuery):
    await bot.set_state(call.from_user.id, Action.start)
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text='Update:', reply_markup=options_keyboard())


@ bot.callback_query_handler(func=lambda c: c.data == 'quick_save')
async def savequick_callback(call: types.CallbackQuery):
    await bot.current_states.finish(call.from_user.id)
    # await upload(call.message)


@ bot.message_handler(commands=['start', 's'], restrict=True)
async def command_start(message):
    """
    Start the conversation and ask user for input.
    Initialize with options to fill in.
    """
    await bot.set_state(message.from_user.id, Action.start)
    await bot.send_message(message.chat.id, 'Select Option:', reply_markup=default_options_keyboard())


def main() -> None:
    """Run the bot."""
    bot.add_custom_filter(Restrict_Access())
    bot.add_custom_filter(StateFilter(bot))
    bot.add_custom_filter(IsDigitFilter())
    bot.add_custom_filter(ActionsCallbackFilter())
    asyncio.run(bot.polling())


if __name__ == '__main__':
    main()
