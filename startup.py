from logging import Logger

import telebot
from gspread import Client, Spreadsheet, auth
from kink import di
from splitwise import Splitwise
from telebot import TeleBot
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData

import shared.utils
from app_config import Configuration
from shared.services import (ActionsCallbackFilter, AsyncActionsCallbackFilter,
                             AsyncIsDigitFilter, AsyncRestrictAccessFilter,
                             AsyncStateFilter, BotFactory, ExceptionHandler,
                             IsDigitFilter, KeyboardUtil, RestrictAccessFilter,
                             StateFilter, TransactionData)


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
    di[Client] = auth.service_account_from_dict(
        di[Configuration]["credentials_json"], scopes=scope
    )

    di["WEBHOOK_URL_BASE"] = di[Configuration]["webhook_base_url"]
    spreadsheet = di[Client].open_by_key(di[Configuration]["worksheet_id"])
    di[Spreadsheet] = spreadsheet
    trx_categories = shared.utils.get_all_categories(spreadsheet)
    di["trx_categories"] = trx_categories
    trx_accounts = [i for s in shared.utils.get_accounts(
        spreadsheet) for i in s]
    di["trx_accounts"] = trx_accounts
    di["groups"] = ["group_sel;" + s for s in trx_categories.keys()]
    di["categories"] = ["save;" + s for l in trx_categories.values()
                        for s in l]
    di["accounts"] = ["acc_sel;" + s for s in trx_accounts]

    di["splitwise"] = Splitwise(
        di[Configuration]["splitwise_key"],
        di[Configuration]["splitwise_secret"],
        api_key=di[Configuration]["splitwise_token"],
    )
    di["self_id"] = di["splitwise"].getCurrentUser().getId()
    di["friend_id"] = di[Configuration]["friend_id"]
    di["group_id"] = di[Configuration]["group_id"]
    sw_categories = di["splitwise"].getCategories()
    di["sw_categories"] = sorted(sw_categories, key=lambda x: x.name)
    sw_groups = di["splitwise"].getGroups()
    di["sw_groups"] = [
        group for group in sw_groups if group.name != "Non-group expenses"]
    sw_group = next(
        (group for group in di["splitwise"].getGroups()
         if group.id == int(di["group_id"])),
        None
    )
    di["sw_group"] = sw_group
    sw_currencies = di["splitwise"].getCurrencies()
    filtered_currencies = [
        currency for currency in sw_currencies if currency.code in ["USD", "PHP", "KRW", "HKD", "SGD", "IDR", "THB"]]
    di["sw_currencies"] = sorted(filtered_currencies, key=lambda x: x.code)
    di["sw_currency"] = next(
        (currency for currency in sw_currencies
         if currency.code == "PHP"),
        None
    )
