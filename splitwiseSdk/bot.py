from kink.errors.service_error import ServiceError
from kink import di
from app_config import Configuration
from telebot.callback_data import CallbackData
from telebot import TeleBot, types
from splitwise import Splitwise
from splitwise.user import ExpenseUser
from shared.services import TransactionData, TextUtil, Action, KeyboardUtil
from shared.utils import *


def bot_functions(bot_instance: TeleBot):
    splitwise: Splitwise = di["splitwise"]

    @bot_instance.message_handler(state="*", commands=["cancel", "q"])
    def cancel_trx(message: types.Message):
        """
        Clears state and cancel current transaction
        """
        di[TransactionData].reset()
        message = di["current_trx_message"]
        if bot_instance.get_state(di["state"]):
            bot_instance.delete_state(di["state"])
        bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Transaction cancelled.",
        )

    @bot_instance.message_handler(state=[Action.outflow, Action.inflow], is_digit=False)
    def invalid_amt(message: types.Message):
        bot_instance.reply_to(message, "Please enter a number")

    def save(message: types.Message, amount: float, description: str):
        bot_instance.set_state(di["state"], Action.quick_end)
        # create another function for this as callback
        friends = splitwise.getFriends()
        bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Select friend:",
            reply_markup=KeyboardUtil.get_keyboard_layout(
                splitwise, friends, column_size=3),
        )
        # need to access callback here
        query = call.callback_query
        friend_id = int(query.data)
        id_name_mapping = get_id_name_mapping(splitwise)
        name = id_name_mapping[friend_id]
        bot_instance.reply_to(f'Expense to be created with <b>{name}</b> with amount <b>{di[Configuration]["currency"]}{amount}</b>'
                              f' and description <b>{description}</b>', parse_mode=types.ParseMode.HTML)

        query = bot_instance.callback_query
        self_id = splitwise.getCurrentUser().getId()
        splitwise.create_expense_object(
            self_id, friend_id, amount, description)
        bot_instance.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text='New expense created!')

    @bot_instance.message_handler(regexp="^(A|a)dd(S|s)plit.+$", restrict=True)
    def expense_trx(message: types.Message):
        """
        Add expense transaction using Today's date, Amount and Description
        """
        try:
            cancel_trx(di["current_trx_message"])
        except ServiceError as e:
            print("No current transaction.")
        except Exception as e:
            error_msg = getattr(e, "message", repr(e))
            if "Bad Request: message is not modified" in error_msg:
                print("Previous transaction was already cancelled.")

        di["state"] = message.from_user.id
        di[TransactionData].reset()

        result = TextUtil.text_splitter(message.text)
        del result[0]
        paramCount = len(result)
        if paramCount != 2:
            bot_instance.reply_to(
                message, f"Expected 2 parameters, received {paramCount}: [{result}]"
            )
            return
        else:
            amount, description = result
            try:
                amount = float(amount)
            except ValueError:
                invalid_amt(message)
            else:
                save(message, amount, description)
