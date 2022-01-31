import shlex
import aspire_util
from kink import di
from app_config import Configuration
from telebot.callback_data import CallbackData
from telebot import TeleBot, types
from services import Action, Formatting, TransactionData, DateUtil, KeyboardUtil
from gspread import Spreadsheet


def sync_bot_functions(bot_instance: TeleBot):
    trx_categories = di["trx_categories"]
    trx_accounts = di["trx_accounts"]
    groups = di["groups"]
    categories = di["categories"]
    accounts = di["accounts"]

    @bot_instance.message_handler(commands=["start", "s"], restrict=True)
    def command_start(message: types.Message):
        """
        Start the conversation and ask user for input.
        Initialize with options to fill in.
        """
        bot_instance.set_state(message.chat.id, Action.start)
        bot_instance.send_message(
            message.chat.id,
            "Select Option:",
            reply_markup=KeyboardUtil.create_default_options_keyboard(),
        )
