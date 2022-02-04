import shlex
import aspire_util
from kink import di
from app_config import Configuration
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData
from telebot import types
from services import Action, Formatting, TransactionData, DateUtil, KeyboardUtil
from gspread import Spreadsheet


def async_bot_functions(bot_instance: AsyncTeleBot):
    trx_categories = di["trx_categories"]
    trx_accounts = di["trx_accounts"]
    groups = di["groups"]
    categories = di["categories"]
    accounts = di["accounts"]

    @bot_instance.message_handler(state="*", commands=["cancel", "q"])
    async def async_cancel_trx(message: types.Message):
        """
        Clears state and cancel current transaction
        """
        di[TransactionData].reset()
        message = di["current_trx_message"]
        await bot_instance.delete_state(di["state"])
        await bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Transaction cancelled.",
        )

    @bot_instance.message_handler(state=[Action.outflow, Action.inflow], is_digit=False)
    async def async_invalid_amt(message: types.Message):
        await bot_instance.reply_to(message, "Please enter a number")

    async def async_upload_trx(message: types.Message):
        """
        Clears state and upload transaction to sheets
        """
        await bot_instance.delete_state(di["state"])
        await async_upload(message)

    @bot_instance.message_handler(
        state=[Action.outflow, Action.inflow, Action.memo], restrict=True
    )
    async def async_save_current(message: types.Message):
        """
        Saves user input to selected option
        """
        current_action = await bot_instance.get_state(di["state"])
        di[TransactionData][current_action.name.capitalize()] = message.text
        await async_item_selected(current_action, di["current_trx_message"])

    async def async_quick_save(message: types.Message):
        await bot_instance.set_state(di["state"], Action.quick_end)
        di["current_trx_message"] = await bot_instance.send_message(
            chat_id=message.chat.id,
            text="Current Transaction:",
            reply_markup=KeyboardUtil.create_options_keyboard(),
        )

    async def async_upload(message: types.Message):
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
        await bot_instance.reply_to(message, "✅ Transaction Saved\n")

    @bot_instance.message_handler(regexp="^(A|a)dd(I|i)nc.+$", restrict=True)
    async def async_income_trx(message: types.Message):
        """
        Add income transaction using Today's date, Inflow Amount and Memo
        """
        di["state"] = message.from_user.id
        di[TransactionData].reset()

        text = message.text
        result = list(shlex.split(text))
        del result[0]
        paramCount = len(result)
        if paramCount != 2:
            await bot_instance.reply_to(
                message, f"Expected 2 parameters, received {paramCount}: [{result}]"
            )
            return
        else:
            inflow, memo = result
            try:
                inflow = float(inflow)
            except ValueError:
                await async_invalid_amt(message)
            else:
                di[TransactionData]["Date"] = DateUtil.date_today()
                di[TransactionData]["Inflow"] = inflow
                di[TransactionData]["Memo"] = memo
                await async_quick_save(message)

    @bot_instance.message_handler(regexp="^(A|a)dd(E|e)xp.+$", restrict=True)
    async def async_expense_trx(message: types.Message):
        """
        Add expense transaction using Today's date, Outflow Amount and Memo
        """
        di["state"] = message.from_user.id
        di[TransactionData].reset()

        text = message.text
        result = list(shlex.split(text))
        del result[0]
        paramCount = len(result)
        if paramCount != 2:
            await bot_instance.reply_to(
                message, f"Expected 2 parameters, received {paramCount}: [{result}]"
            )
            return
        else:
            outflow, memo = result
            try:
                outflow = float(outflow)
            except ValueError:
                await async_invalid_amt(message)
            else:
                di[TransactionData]["Date"] = DateUtil.date_today()
                di[TransactionData]["Outflow"] = outflow
                di[TransactionData]["Memo"] = memo
                await async_quick_save(message)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data == "back;category", state=Action.category_list
    )
    async def async_back_to_category_groups_menu(call: types.CallbackQuery):
        """
        Return to category groups selection menu
        """
        await bot_instance.set_state(di["state"], Action.category)
        await category_select_start(call.message)

    async def category_select_start(message: types.Message):
        # Creates a keyboard, each key has a callback_data : group_sel;"group name" e.g. group_sel:"Expenses"
        await bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Select Group:",
            reply_markup=aspire_util.create_category_inline(
                trx_categories.keys(), "group_sel"
            ),
        )

    async def account_sel_start(message: types.Message):
        await bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Select Account:",
            reply_markup=aspire_util.create_account_inline(trx_accounts, "acc_sel"),
        )

    async def date_sel_start(message: types.Message):
        await bot_instance.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.id,
            text="Select Date:",
            reply_markup=aspire_util.create_calendar(),
        )

    async def async_item_selected(action: Action, message: types.Message):
        """
        Process item selected through /start command
        """
        await bot_instance.set_state(di["state"], action)
        data = di[TransactionData][action.name.capitalize()]

        if action == Action.outflow or action == Action.inflow:
            displayData = (
                (di[Configuration]["currency"] + f" {data}") if data != "" else "''"
            )
        else:
            displayData = data if data != "" else "''"

        if action == Action.category:
            await category_select_start(message)
        elif action == Action.account:
            await account_sel_start(message)
        elif action == Action.date:
            await date_sel_start(message)
        else:
            text = (
                f"\[Current Value: "
                + f" *{displayData}*]"
                + "\n"
                + f"Enter {action.name.capitalize()} : "
            )
            await bot_instance.edit_message_text(
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
    async def async_actions_callback(call: types.CallbackQuery):
        """
        Read and save state of bot depending on item selected from /start command
        """
        callback_data: dict = di[CallbackData].parse(callback_data=call.data)
        actionId = int(callback_data["action_id"])
        action = Action(actionId)

        if action == Action.cancel:
            await async_cancel_trx(di["current_trx_message"])
        elif action == Action.done:
            await async_upload_trx(call.message)
        else:
            await async_item_selected(action, call.message)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data in categories, state=Action.category_list, restrict=True
    )
    async def async_get_category(call: types.CallbackQuery):
        """
        Get user selection and store to Category
        """
        action, choice = aspire_util.separate_callback_data(call.data)
        di[TransactionData]["Category"] = choice
        await async_save_callback(call)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data in accounts, state=Action.account, restrict=True
    )
    async def async_get_account(call: types.CallbackQuery):
        """
        Read user input and store to Account
        """
        action, choice = aspire_util.separate_callback_data(call.data)
        di[TransactionData]["Account"] = choice
        await async_save_callback(call)

    @bot_instance.callback_query_handler(func=None, state=Action.date)
    async def async_get_date(call: types.CallbackQuery):
        """
        Read user selection from calendar and store to Date
        """
        selected, date = await aspire_util.async_process_calendar_selection(
            call, bot_instance
        )
        if selected:
            di[TransactionData]["Date"] = date.strftime("%m/%d/%Y")
            await async_save_callback(call)

    @bot_instance.callback_query_handler(
        func=lambda c: c.data in groups, state=Action.category
    )
    async def async_list_categories(call: types.CallbackQuery):
        """
        Show categories as InlineKeyboard
        """
        await bot_instance.set_state(di["state"], Action.category_list)
        action, choice = aspire_util.separate_callback_data(call.data)
        await bot_instance.edit_message_text(
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
    async def async_save_callback(call: types.CallbackQuery):
        """
        Return to main menu of /start command showing new saved values
        """
        await bot_instance.set_state(di["state"], Action.start)
        await bot_instance.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Current Transaction:",
            reply_markup=KeyboardUtil.create_options_keyboard(),
        )

    @bot_instance.callback_query_handler(
        func=lambda c: c.data == "quick_save", state=Action.quick_end
    )
    async def async_savequick_callback(call: types.CallbackQuery):
        """
        Clears state and upload to sheets for quick add functions
        """
        await bot_instance.delete_state(di["state"])
        await async_upload(call.message)

    @bot_instance.message_handler(commands=["start", "s"], restrict=True)
    async def async_command_start(message: types.Message):
        """
        Start the conversation and ask user for input.
        Initialize with options to fill in.
        """
        di["state"] = message.from_user.id
        await bot_instance.set_state(di["state"], Action.start)
        di[TransactionData]["Date"] = DateUtil.date_today()
        di["current_trx_message"] = await bot_instance.send_message(
            message.chat.id,
            "Select Option:",
            reply_markup=KeyboardUtil.create_default_options_keyboard(),
        )
