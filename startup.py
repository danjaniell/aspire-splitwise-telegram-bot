import telebot
import aspire_util
from kink import di
from app_config import Configuration
from telebot import TeleBot
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData
from logging import Logger
from services import (
    Formatting,
    BotFactory,
    TransactionData,
    KeyboardUtil,
    RestrictAccessFilter,
    ExceptionHandler,
    StateFilter,
    IsDigitFilter,
    ActionsCallbackFilter,
    AsyncRestrictAccessFilter,
    AsyncStateFilter,
    AsyncIsDigitFilter,
    AsyncActionsCallbackFilter,
)
from gspread import auth, Client, Spreadsheet


def configure_services() -> None:
    """
    Setup services into the container for dependency injection
    """
    trx_data = {
        "Date": "",
        "Outflow": "",
        "Inflow": "",
        "Category": "",
        "Account": "",
        "Memo": "",
    }

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]

    di[Logger] = telebot.logger
    di[Configuration] = Configuration().values

    if di[Configuration]["run_async"]:
        bot_instance = AsyncTeleBot(
            token=di[Configuration]["token"],
            parse_mode="MARKDOWN",
            exception_handler=ExceptionHandler(),
        )
        di["bot_instance"] = BotFactory(
            bot_instance=bot_instance,
            restrict_access_filter=AsyncRestrictAccessFilter(),
            state_filter=AsyncStateFilter(bot_instance),
            is_digit_filter=AsyncIsDigitFilter(),
            actions_callback_filter=AsyncActionsCallbackFilter(),
        ).create_bot()
    else:
        bot_instance = TeleBot(
            token=di[Configuration]["token"],
            parse_mode="MARKDOWN",
            exception_handler=ExceptionHandler(),
            threaded=False,
        )
        di["bot_instance"] = BotFactory(
            bot_instance=bot_instance,
            restrict_access_filter=RestrictAccessFilter(),
            state_filter=StateFilter(bot_instance),
            is_digit_filter=IsDigitFilter(),
            actions_callback_filter=ActionsCallbackFilter(),
        ).create_bot()

    di[TransactionData] = TransactionData(trx_data)
    di[CallbackData] = CallbackData("action_id", prefix="Action")
    di[KeyboardUtil] = KeyboardUtil()
    di[Formatting] = Formatting()
    di[Client] = auth.service_account_from_dict(
        di[Configuration]["credentials_json"], scopes=scope
    )

    di["WEBHOOK_URL_BASE"] = di[Configuration]["webhook_base_url"]
    spreadsheet = di[Client].open_by_key(di[Configuration]["worksheet_id"])
    trx_categories = aspire_util.get_all_categories(spreadsheet)
    di["trx_categories"] = trx_categories
    trx_accounts = [i for s in aspire_util.get_accounts(spreadsheet) for i in s]
    di["trx_accounts"] = trx_accounts
    di["groups"] = ["group_sel;" + s for s in trx_categories.keys()]
    di["categories"] = ["save;" + s for l in trx_categories.values() for s in l]
    di["accounts"] = ["acc_sel;" + s for s in trx_accounts]
