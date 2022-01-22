from logging import Logger
import telebot
import aspire_util
from kink import di
from app_config import Configuration
from telebot import TeleBot
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData
from services import (
    Formatting,
    MyTeleBot,
    TransactionData,
    KeyboardUtil,
    MyAsyncTeleBot,
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

    if not di[Configuration]['run_async']:
        async_bot = AsyncTeleBot(token=di[Configuration]['token'],
                                 parse_mode='MARKDOWN',
                                 exception_handler=ExceptionHandler())
        di[MyTeleBot] = MyAsyncTeleBot(bot_instance=async_bot,
                                       restrict_access_filter=Restrict_Access(),
                                       state_filter=StateFilter(async_bot),
                                       is_digit_filter=IsDigitFilter(),
                                       actions_callback_filter=ActionsCallbackFilter())
    else:
        bot = TeleBot(token=di[Configuration]['token'],
                      parse_mode='MARKDOWN',
                      exception_handler=ExceptionHandler(),
                      threaded=False)
        di[MyTeleBot] = MyTeleBot(bot_instance=bot,
                                  restrict_access_filter=Restrict_Access(),
                                  state_filter=StateFilter(bot),
                                  is_digit_filter=IsDigitFilter(),
                                  actions_callback_filter=ActionsCallbackFilter())

    di[TransactionData] = TransactionData(trx_data)
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
