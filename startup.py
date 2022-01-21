from logging import Logger
import time
import flask
import telebot
import asyncio
import aspire_util
from flask import Flask
from kink import di
from app_config import Configuration
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData
from services import (
    Formatting,
    TransactionData,
    KeyboardUtil,
    MyTeleBot,
    Restrict_Access,
    StateFilter,
    IsDigitFilter,
    ActionsCallbackFilter,
    ExceptionHandler
)
from gspread import auth, Client, Spreadsheet


def configure_services() -> None:
    """
    Setup services into the container for dependency injection
    """
    trx_data = {
        'Date': '',
        'Outflow': '',
        'Inflow': '',
        'Category': '',
        'Account': '',
        'Memo': '',
    }

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive',
    ]
    di[Logger] = telebot.logger
    di[Configuration] = Configuration().values
    di[TransactionData] = TransactionData(trx_data)
    di[AsyncTeleBot] = AsyncTeleBot(token=di[Configuration]['token'],
                                    parse_mode='MARKDOWN',
                                    exception_handler=ExceptionHandler())
    di[Restrict_Access] = Restrict_Access()
    di[StateFilter] = StateFilter(di[AsyncTeleBot])
    di[IsDigitFilter] = IsDigitFilter()
    di[ActionsCallbackFilter] = ActionsCallbackFilter()
    di[MyTeleBot] = MyTeleBot()
    di[CallbackData] = CallbackData('action_id', prefix='Action')
    di[KeyboardUtil] = KeyboardUtil()
    di[Formatting] = Formatting()
    di[Client] = auth.service_account_from_dict(
        di[Configuration]['credentials_json'], scopes=scope)
    di[Spreadsheet] = di[Client].open_by_key(
        di[Configuration]['worksheet_id'])
    di['trx_accounts'] = [
        item for sublist in aspire_util.get_accounts(di[Spreadsheet]) for item in sublist
    ]
    di['WEBHOOK_URL_BASE'] = di[Configuration]['webhook_base_url']


configure_services()

WEBHOOK_URL_BASE = di['WEBHOOK_URL_BASE']
WEBHOOK_URL_PATH = "/%s/" % (di[Configuration]['secret'])

app = Flask(__name__)


@app.route('/start', methods=['GET'])
def start():
    asyncio.run(di[MyTeleBot].Instance.delete_webhook(
        drop_pending_updates=True))
    time.sleep(0.1)
    if (di[Configuration]['update_mode'] == 'polling'):
        asyncio.run(di[MyTeleBot].Instance.infinity_polling(skip_pending=True))
    elif (di[Configuration]['update_mode'] == 'webhook'):
        asyncio.run(di[MyTeleBot].Instance.set_webhook(
            url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH))
    return 'Bot started.'


@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        asyncio.run(di[MyTeleBot].Instance.process_new_updates([update]))
        return ''
    else:
        flask.abort(403)
