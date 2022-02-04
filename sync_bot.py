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

    @bot_instance.message_handler(state="*", commands=["cancel", "q"])
    def cancel_trx(message: types.Message):
        """
        Clears state and cancel current transaction
        """
        di[TransactionData].reset()
        message = di["current_trx_message"]
        bot_instance.delete_state(di["state"])
        bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Transaction cancelled.",
        )

    @bot_instance.message_handler(state=[Action.outflow, Action.inflow], is_digit=False)
    def invalid_amt(message: types.Message):
        bot_instance.reply_to(message, "Please enter a number")

    def upload_trx(message: types.Message):
        """
        Clears state and upload transaction to sheets
        """
        bot_instance.delete_state(di["state"])
        upload(message)

    @bot_instance.message_handler(
        state=[Action.outflow, Action.inflow, Action.memo], restrict=True
    )
    def save_current(message: types.Message):
        """
        Saves user input to selected option
        """
        current_action = bot_instance.get_state(di["state"])
        di[TransactionData][current_action.name.capitalize()] = message.text
        item_selected(current_action, di["current_trx_message"])

    def quick_save(message: types.Message):
        bot_instance.set_state(di["state"], Action.quick_end)
        di["current_trx_message"] = bot_instance.send_message(
            chat_id=message.chat.id,
            text="Current Transaction:",
            reply_markup=KeyboardUtil.create_options_keyboard(),
        )

    def upload(message: types.Message):
        """
        Upload info to aspire google sheet
        """
        upload_data = [
            di[TransactionData]["Date"],
            di[TransactionData]["Outflow"],
            di[TransactionData]["Inflow"],
            di[TransactionData]["Category"],
            di[TransactionData]["Account"],
            di[TransactionData]["Memo"],
        ]
        aspire_util.append_trx(di[Spreadsheet], upload_data)
        di[TransactionData].reset()
        bot_instance.reply_to(message, "✅ Transaction Saved\n")

    @bot_instance.message_handler(regexp="^(A|a)dd(I|i)nc.+$", restrict=True)
    def income_trx(message: types.Message):
        """
        Add income transaction using Today's date, Inflow Amount and Memo
        """
        di[TransactionData].reset()
        if bot_instance.get_state(di["state"]):
            bot_instance.delete_state(di["state"])

        text = message.text
        result = list(shlex.split(text))
        del result[0]
        paramCount = len(result)
        if paramCount != 2:
            bot_instance.reply_to(
                message, f"Expected 2 parameters, received {paramCount}: [{result}]"
            )
            return
        else:
            inflow, memo = result
            di[TransactionData]["Date"] = DateUtil.date_today()
            di[TransactionData]["Inflow"] = inflow
            di[TransactionData]["Memo"] = memo
        quick_save(message)

    @bot_instance.message_handler(regexp="^(A|a)dd(E|e)xp.+$", restrict=True)
    def expense_trx(message: types.Message):
        """
        Add expense transaction using Today's date, Outflow Amount and Memo
        """
        di[TransactionData].reset()
        if bot_instance.get_state(di["state"]):
            bot_instance.delete_state(di["state"])

        text = message.text
        result = list(shlex.split(text))
        del result[0]
        paramCount = len(result)
        if paramCount != 2:
            bot_instance.reply_to(
                message, f"Expected 2 parameters, received {paramCount}: [{result}]"
            )
            return
        else:
            outflow, memo = result
            di[TransactionData]["Date"] = DateUtil.date_today()
            di[TransactionData]["Outflow"] = outflow
            di[TransactionData]["Memo"] = memo
        quick_save(message)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data == "back;category", state=Action.category_list
    )
    def back_to_category_groups_menu(call: types.CallbackQuery):
        """
        Return to category groups selection menu
        """
        bot_instance.set_state(di["state"], Action.category)
        category_select_start(call.message)

    def category_select_start(message: types.Message):
        # Creates a keyboard, each key has a callback_data : group_sel;"group name" e.g. group_sel:"Expenses"
        bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Select Group:",
            reply_markup=aspire_util.create_category_inline(
                trx_categories.keys(), "group_sel"
            ),
        )

    def account_sel_start(message: types.Message):
        bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Select Account:",
            reply_markup=aspire_util.create_account_inline(trx_accounts, "acc_sel"),
        )

    def date_sel_start(message: types.Message):
        bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Select Date:",
            reply_markup=aspire_util.create_calendar(),
        )

    def item_selected(action: Action, message: types.Message):
        """
        Process item selected through /start command
        """
        bot_instance.set_state(di["state"], action)
        data = di[TransactionData][action.name.capitalize()]

        if action == Action.outflow or action == Action.inflow:
            displayData = (
                (di[Configuration]["currency"] + f" {data}") if data != "" else "''"
            )
        else:
            displayData = data if data != "" else "''"

        if action == Action.category:
            category_select_start(message)
        elif action == Action.account:
            account_sel_start(message)
        elif action == Action.date:
            date_sel_start(message)
        else:
            text = (
                f"\[Current Value: "
                + f" *{displayData}*]"
                + "\n"
                + f"Enter {action.name.capitalize()} : "
            )
            bot_instance.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.id,
                text=text,
                reply_markup=KeyboardUtil.create_save_keyboard("save"),
            )

    @bot_instance.callback_query_handler(
        func=None,
        config=di[CallbackData].filter(),
        state=[Action.start, Action.quick_end],
        restrict=True,
    )
    def actions_callback(call: types.CallbackQuery):
        """
        Read and save state of bot depending on item selected from /start command
        """
        callback_data: dict = di[CallbackData].parse(callback_data=call.data)
        actionId = int(callback_data["action_id"])
        action = Action(actionId)

        if action == Action.cancel:
            cancel_trx(di["current_trx_message"])
        elif action == Action.done:
            upload_trx(call.message)
        else:
            item_selected(action, call.message)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data in categories, state=Action.category_list, restrict=True
    )
    def get_category(call: types.CallbackQuery):
        """
        Get user selection and store to Category
        """
        action, choice = aspire_util.separate_callback_data(call.data)
        di[TransactionData]["Category"] = choice
        save_callback(call)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data in accounts, state=Action.account, restrict=True
    )
    def get_account(call: types.CallbackQuery):
        """
        Read user input and store to Account
        """
        action, choice = aspire_util.separate_callback_data(call.data)
        di[TransactionData]["Account"] = choice
        save_callback(call)

    @bot_instance.callback_query_handler(func=None, state=Action.date)
    def get_date(call: types.CallbackQuery):
        """
        Read user selection from calendar and store to Date
        """
        selected, date = aspire_util.process_calendar_selection(call, bot_instance)
        if selected:
            di[TransactionData]["Date"] = date.strftime("%m/%d/%Y")
            save_callback(call)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data in groups, state=Action.category
    )
    def list_categories(call: types.CallbackQuery):
        """
        Show categories as InlineKeyboard
        """
        bot_instance.set_state(di["state"], Action.category_list)
        action, choice = aspire_util.separate_callback_data(call.data)
        bot_instance.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Select Category:",
            reply_markup=aspire_util.create_category_inline(
                trx_categories[choice], "save"
            ),
        )

    @bot_instance.callback_query_handler(
        func=lambda c: c.data == "save",
        state=[
            Action.outflow,
            Action.inflow,
            Action.category,
            Action.account,
            Action.memo,
            Action.date,
        ],
    )
    def save_callback(call: types.CallbackQuery):
        """
        Return to main menu of /start command showing new saved values
        """
        bot_instance.set_state(di["state"], Action.start)
        bot_instance.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Current Transaction:",
            reply_markup=KeyboardUtil.create_options_keyboard(),
        )

    @bot_instance.callback_query_handler(
        func=lambda c: c.data == "quick_save", state=Action.quick_end
    )
    def savequick_callback(call: types.CallbackQuery):
        """
        Clears state and upload to sheets for quick add functions
        """
        bot_instance.delete_state(di["state"])
        upload(call.message)

    @bot_instance.message_handler(commands=["start", "s"], restrict=True)
    def command_start(message: types.Message):
        """
        Start the conversation and ask user for input.
        Initialize with options to fill in.
        """
        di["state"] = message.from_user.id
        bot_instance.set_state(di["state"], Action.start)
        di[TransactionData]["Date"] = DateUtil.date_today()
        di["current_trx_message"] = bot_instance.send_message(
            message.chat.id,
            "Select Option:",
            reply_markup=KeyboardUtil.create_default_options_keyboard(),
        )
