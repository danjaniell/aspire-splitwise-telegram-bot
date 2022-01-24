import startup
import shlex
import asyncio
import time
import flask
import aspire_util
from logging import Logger
from flask import Flask
from kink import di
from app_config import Configuration
from telebot.async_telebot import AsyncTeleBot
from telebot.callback_data import CallbackData
from telebot import TeleBot, types
from services import (
    Action,
    Formatting,
    TransactionData,
    DateUtil,
    KeyboardUtil
)
from gspread import Spreadsheet

# inject dependencies
startup.configure_services()

trx_categories = aspire_util.get_all_categories(di[Spreadsheet])
groups = ["group_sel;" + s for s in trx_categories.keys()]


def async_bot_functions(bot_instance: AsyncTeleBot):
    # Set all async bot handlers inside this function
    @bot_instance.message_handler(state='*', commands=['cancel', 'q'])
    async def async_command_cancel(message: types.Message):
        """
        Cancel transaction from any state
        """
        await bot_instance.delete_state(message.chat.id)
        await bot_instance.send_message(message.chat.id, 'Transaction cancelled.')

    @bot_instance.message_handler(state=[Action.outflow, Action.inflow], is_digit=False)
    async def async_invalid_amt(message: types.Message):
        await bot_instance.reply_to(message, 'Please enter a number')

    async def async_upload_trx(message: types.Message):
        """
        Clears state and upload transaction to sheets
        """
        await bot_instance.delete_state(message.chat.id)
        await async_upload(message)

    async def async_cancel_trx(message: types.Message):
        """
        Clears state and cancel current transaction
        """
        await bot_instance.delete_state(message.chat.id)
        await bot_instance.edit_message_text(chat_id=message.chat.id, message_id=message.id, text='Transaction cancelled.')

    async def async_quick_save(message: types.Message):
        await bot_instance.set_state(message.chat.id, Action.quick_end)
        await bot_instance.send_message(message.chat.id,
                                        '\[Received Data]' +
                                        f'\n{di[Formatting].format_data(di[TransactionData])}',
                                        reply_markup=KeyboardUtil.create_save_keyboard('quick_save'))

    async def async_upload(message: types.Message):
        """
        Upload info to aspire google sheet
        """
        upload_data = [
            di[TransactionData]['Date'],
            di[TransactionData]['Outflow'],
            di[TransactionData]['Inflow'],
            di[TransactionData]['Category'],
            di[TransactionData]['Account'],
            di[TransactionData]['Memo'],
        ]
        aspire_util.append_trx(di[Spreadsheet], upload_data)
        di[TransactionData].reset()
        await bot_instance.reply_to(message, '✅ Transaction Saved\n')

    @bot_instance.message_handler(regexp='^(A|a)dd(I|i)nc.+$', restrict=True)
    async def async_income_trx(message: types.Message):
        """
        Add income transaction using Today's date, Inflow Amount and Memo
        """
        di[TransactionData].reset()
        text = message.text
        result = list(shlex.split(text))
        del result[0]
        paramCount = len(result)
        if paramCount != 2:
            await bot_instance.reply_to(
                message, f'Expected 2 parameters, received {paramCount}: [{result}]')
            return
        else:
            inflow, memo = result
            di[TransactionData]['Date'] = DateUtil.date_today()
            di[TransactionData]['Inflow'] = inflow
            di[TransactionData]['Memo'] = memo
        await async_quick_save(message)

    @bot_instance.message_handler(regexp='^(A|a)dd(E|e)xp.+$', restrict=True)
    async def async_expense_trx(message: types.Message):
        """
        Add expense transaction using Today's date, Outflow Amount and Memo
        """
        di[TransactionData].reset()
        text = message.text
        result = list(shlex.split(text))
        del result[0]
        paramCount = len(result)
        if paramCount != 2:
            await bot_instance.reply_to(
                message, f'Expected 2 parameters, received {paramCount}: [{result}]')
            return
        else:
            outflow, memo = result
            di[TransactionData]['Date'] = DateUtil.date_today()
            di[TransactionData]['Outflow'] = outflow
            di[TransactionData]['Memo'] = memo
        await async_quick_save(message)

    async def async_item_selected(action: Action, message: types.Message):
        """
        Process item selected through /start command
        """
        await bot_instance.set_state(message.chat.id, action)
        data = di[TransactionData][action.name.capitalize()]

        if action == Action.outflow or action == Action.inflow:
            displayData = (di[Configuration]['currency'] +
                           f' {data}') if data != '' else '\'\''
        else:
            displayData = data if data != '' else '\'\''

        if action == Action.category:
            # Creates a keyboard, each key has a callback_data : group_sel;"group name" e.g. group_sel:"Expenses"
            await bot_instance.edit_message_text(chat_id=message.chat.id, message_id=message.id,
                                                 text='Select Group', reply_markup=aspire_util.create_category_inline(trx_categories.keys(), "group_sel"))
        else:
            text = f'\[Current Value: ' + f' *{displayData}*]' + '\n' + \
                f'Enter {action.name.capitalize()} : '
            await bot_instance.edit_message_text(chat_id=message.chat.id, message_id=message.id,
                                                 text=text, reply_markup=KeyboardUtil.create_save_keyboard('save'))

    @ bot_instance.callback_query_handler(func=None, config=di[CallbackData].filter(), state=Action.start, restrict=True)
    async def async_actions_callback(call: types.CallbackQuery):
        """
        Read and save state of bot depending on item selected from /start command
        """
        callback_data: dict = di[CallbackData].parse(
            callback_data=call.data)
        actionId = int(callback_data['action_id'])
        action = Action(actionId)

        if (action == Action.cancel):
            await async_cancel_trx(call.message)
        elif (action == Action.done):
            await async_upload_trx(call.message)
        else:
            await async_item_selected(action, call.message)

    @ bot_instance.message_handler(state=Action.outflow, restrict=True)
    async def async_get_outflow(message: types.Message):
        """
        Read user input and store to Outflow
        """
        di[TransactionData]['Outflow'] = message.text

    @ bot_instance.message_handler(state=Action.inflow, restrict=True)
    async def async_get_inflow(message: types.Message):
        """
        Read user input and store to Inflow
        """
        di[TransactionData]['Inflow'] = message.text

    @ bot_instance.message_handler(state=Action.category, restrict=True)
    async def async_get_category(message: types.Message):
        """
        Read user input and store to Category
        """
        di[TransactionData]['Category'] = message.text

    @ bot_instance.message_handler(state=Action.account, restrict=True)
    async def async_get_account(message: types.Message):
        """
        Read user input and store to Account
        """
        di[TransactionData]['Account'] = message.text

    @ bot_instance.message_handler(state=Action.memo, restrict=True)
    async def async_get_memo(message: types.Message):
        """
        Read user input and store to Memo
        """
        di[TransactionData]['Memo'] = message.text

    @ bot_instance.callback_query_handler(func=lambda c: c.data in groups)
    async def async_list_category(call: types.CallbackQuery):
        """
        Show categories as InlineKeyboard
        """
        # TODO
        await bot_instance.set_state(call.message.chat.id, Action.category_list)
        choice = call.data.split(';')[1]
        await bot_instance.edit_message_text(chat_id=call.message.chat.id,
                                             message_id=call.message.message_id,
                                             text='Select Category:',
                                             reply_markup=aspire_util.create_category_inline(trx_categories[choice], 'cat_selection'))

    @ bot_instance.callback_query_handler(func=lambda c: c.data == 'save')
    async def async_save_callback(call: types.CallbackQuery):
        """
        Return to main menu of /start command showing new saved values
        """
        await bot_instance.set_state(call.message.chat.id, Action.start)
        await bot_instance.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                             text='Update:', reply_markup=KeyboardUtil.create_options_keyboard())

    @ bot_instance.callback_query_handler(func=lambda c: c.data == 'quick_save')
    async def async_savequick_callback(call: types.CallbackQuery):
        """
        Clears state and upload to sheets for quick add functions
        """
        await bot_instance.delete_state(call.message.chat.id)
        await async_upload(call.message)

    @ bot_instance.message_handler(commands=['start', 's'], restrict=True)
    async def async_command_start(message: types.Message):
        """
        Start the conversation and ask user for input.
        Initialize with options to fill in.
        """
        await bot_instance.set_state(message.chat.id, Action.start)
        await bot_instance.send_message(message.chat.id, 'Select Option:', reply_markup=KeyboardUtil.create_default_options_keyboard())


def sync_bot_functions(bot_instance: TeleBot):
    # Set all sync bot handlers inside this function
    @ bot_instance.message_handler(commands=['start', 's'], restrict=True,)
    def command_start(message: types.Message):
        """
        Start the conversation and ask user for input.
        Initialize with options to fill in.
        """
        bot_instance.set_state(message.chat.id, Action.start)
        bot_instance.send_message(message.chat.id, 'Select Option:',
                                  reply_markup=KeyboardUtil.create_default_options_keyboard())


WEBHOOK_URL_BASE = di['WEBHOOK_URL_BASE']
WEBHOOK_URL_PATH = "/%s/" % (di[Configuration]['secret'])


app = Flask(__name__)


if di[Configuration]['run_async']:
    async_bot_functions(di['bot_instance'])
else:
    sync_bot_functions(di['bot_instance'])

if isinstance(di['bot_instance'], AsyncTeleBot):
    asyncio.run(di['bot_instance'].delete_webhook(
        drop_pending_updates=True))
    time.sleep(0.1)
    if (di[Configuration]['update_mode'] == 'polling'):
        asyncio.run(di['bot_instance'].infinity_polling(
            skip_pending=True))
    elif (di[Configuration]['update_mode'] == 'webhook'):
        asyncio.run(di['bot_instance'].set_webhook(
            url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH))
elif isinstance(di['bot_instance'], TeleBot):
    di['bot_instance'].delete_webhook(drop_pending_updates=True)
    time.sleep(0.1)
    if (di[Configuration]['update_mode'] == 'polling'):
        di['bot_instance'].infinity_polling(skip_pending=True)
    elif (di[Configuration]['update_mode'] == 'webhook'):
        di['bot_instance'].set_webhook(
            url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)


@ app.route(WEBHOOK_URL_PATH, methods=['POST'])
def receive_updates():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        if isinstance(di['bot_instance'], AsyncTeleBot):
            asyncio.run(di['bot_instance'].process_new_updates([update]))
        elif isinstance(di['bot_instance'], TeleBot):
            di['bot_instance'].process_new_updates([update])
        return ''
    else:
        flask.abort(403)


if __name__ == '__main__':
    app.run(port=8084)
