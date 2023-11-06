from kink import di
from kink.errors.service_error import ServiceError
from splitwise import Splitwise
from telebot import TeleBot, types

from shared.services import (Action, DateUtil, KeyboardUtil, TextUtil,
                             TransactionData)
from shared.utils import *


def bot_functions(bot_instance: TeleBot):
    splitwise: Splitwise = di["splitwise"]
    sw_categories = [category.name for category in di["sw_categories"]]
    sw_groups = [group.name for group in di["sw_groups"]]
    sw_currencies = [currency.code for currency in di["sw_currencies"]]
    sw_subcategories = [subcategory.name for category in di["sw_categories"]
                        for subcategory in category.subcategories]

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

    # TODO - apply state filtering
    @bot_instance.callback_query_handler(func=lambda c: c.data in sw_categories)
    def get_sw_subcategories(call: types.CallbackQuery):
        current_group = "<b>{}</b>".format(di["sw_group"].name)
        currency_used = "<b>{}</b>".format(di["sw_currency"].unit)
        di["current_trx_message"] = bot_instance.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            text=f'[{currency_used} in {current_group}] Select subcategory:',
            reply_markup=KeyboardUtil.create_subcategory_keyboard(call.data),
            parse_mode="HTML"
        )

    # TODO - apply state filtering
    @bot_instance.callback_query_handler(func=lambda c: c.data in sw_subcategories)
    def selected_sw_category(call: types.CallbackQuery):
        save(call.message, call.data)

    # TODO - apply state filtering
    @bot_instance.callback_query_handler(func=lambda c: c.data in sw_groups)
    def selected_sw_group(call: types.CallbackQuery):
        sw_group = next(
            (group for group in di["splitwise"].getGroups()
             if group.name == call.data),
            None
        )
        di["sw_group"] = sw_group
        bot_instance.reply_to(
            call.message, f'✅ Transactions will now save to {call.data} group')

    # TODO - apply state filtering
    @bot_instance.callback_query_handler(func=lambda c: c.data in sw_currencies)
    def selected_sw_currency(call: types.CallbackQuery):
        sw_currency = next(
            (currency for currency in di["sw_currencies"]
             if currency.code == call.data),
            None
        )
        di["sw_currency"] = sw_currency
        bot_instance.reply_to(
            call.message, f'✅ Transactions will use {call.data} currency')

    @bot_instance.message_handler(state=[Action.outflow, Action.inflow], is_digit=False)
    def invalid_amt(message: types.Message):
        bot_instance.reply_to(message, "Please enter a number")

    def save(message: types.Message, category):
        bot_instance.set_state(di["state"], Action.quick_end)
        create_expense_object(splitwise,
                              di["self_id"], di["friend_id"], di["group_id"], category, di[TransactionData]["Outflow"], di[TransactionData]["Memo"])
        bot_instance.reply_to(message, "✅ Transaction Saved\n")

    @bot_instance.message_handler(commands=["swgroup", "swg"], restrict=True)
    def set_sw_group(message: types.Message):
        """
        Sets the group where transactions belong to
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

        bot_instance.set_state(di["state"], Action.sw_set_group)
        di["current_trx_message"] = bot_instance.send_message(
            chat_id=message.chat.id,
            text="Select group:",
            reply_markup=KeyboardUtil.create_sw_keyboard(
                sw_groups, column_size=3),
        )

    @bot_instance.message_handler(commands=["swcurrency", "swc"], restrict=True)
    def set_sw_currency(message: types.Message):
        """
        Set which currency to use for transactions
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

        bot_instance.set_state(di["state"], Action.sw_set_currency)
        di["current_trx_message"] = bot_instance.send_message(
            chat_id=message.chat.id,
            text="Select currency:",
            reply_markup=KeyboardUtil.create_sw_keyboard(
                sw_currencies, column_size=4),
        )

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
                bot_instance.set_state(di["state"], Action.sw_category_list)
                di[TransactionData]["Date"] = DateUtil.date_today()
                di[TransactionData]["Outflow"] = amount
                di[TransactionData]["Memo"] = description

                current_group = "<b>{}</b>".format(di["sw_group"].name)
                currency_used = "<b>{}</b>".format(di["sw_currency"].unit)
                di["current_trx_message"] = bot_instance.send_message(
                    chat_id=message.chat.id,
                    text=f'[{currency_used} in {current_group}] Select category:',
                    reply_markup=KeyboardUtil.create_sw_keyboard(
                        sw_categories),
                    parse_mode="HTML"
                )
