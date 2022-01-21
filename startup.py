import app_logging
import asyncio
import aspire_util
from flask import Flask
from kink import di
from app_config import Configuration
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
    ActionsCallbackFilter
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

    di[Configuration] = Configuration().values
    di[TransactionData] = TransactionData(trx_data)
    di[AsyncTeleBot] = AsyncTeleBot(token=di[Configuration]['token'],
                                    parse_mode='MARKDOWN',
                                    exception_handler=app_logging.ExceptionHandler())
    di[Restrict_Access] = Restrict_Access()
    di[StateFilter] = StateFilter(di[AsyncTeleBot])
    di[IsDigitFilter] = IsDigitFilter()
    di[ActionsCallbackFilter] = ActionsCallbackFilter()
    di[MyTeleBot] = MyTeleBot()
    di[CallbackData] = CallbackData('action_id', prefix='Action')
    di[KeyboardUtil] = KeyboardUtil()
    di[Formatting] = Formatting()
    di[Client] = auth.service_account_from_dict(
        di[Configuration]['credentials_json'])
    di[Spreadsheet] = di[Client].open_by_key(
        di[Configuration]['worksheet_id'])
    di['trx_accounts'] = [
        item for sublist in aspire_util.get_accounts(di[Spreadsheet]) for item in sublist
    ]


configure_services()

app = Flask(__name__)


@app.route('/start', methods=['GET'])
def start():
    asyncio.run(di[MyTeleBot].Instance.polling(skip_pending=True))
    return "Bot ended."
