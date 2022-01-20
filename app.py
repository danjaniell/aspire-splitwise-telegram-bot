import shlex
import asyncio
from app_config import Configuration
from telebot import types
from aspire_util import append_trx
from services import (
    Action,
    Formatting,
    TransactionData,
    DateUtil,
    KeyboardUtil,
    MyTeleBot
)
from gspread_helper import GSpreadHelper


class App():
    @MyTeleBot.Instance.message_handler(state='*', commands=['cancel', 'q'])
    async def command_cancel(message):
        """
        Cancel transaction from any state
        """
        await MyTeleBot.Instance.send_message(message.chat.id, 'Transaction cancelled.')
        await MyTeleBot.Instance.current_states.finish(message.chat.id)

    @MyTeleBot.Instance.message_handler(state=[Action.outflow, Action.inflow], is_digit=False)
    async def invalid_amt(message):
        await MyTeleBot.Instance.reply_to(message, 'Please enter a number')

    async def quick_save(message):
        await MyTeleBot.Instance.set_state(message.from_user.id, Action.quick_end)
        await MyTeleBot.Instance.send_message(message.chat.id,
                                              '\[Received Data]' +
                                              f'\n{Formatting.format_data(TransactionData.values)}',
                                              reply_markup=KeyboardUtil.create_save_keyboard('quick_save'))

    async def upload(message):
        """Upload info to aspire google sheet"""
        upload_data = [
            TransactionData.values['Date'],
            TransactionData.values['Outflow'],
            TransactionData.values['Inflow'],
            TransactionData.values['Category'],
            TransactionData.values['Account'],
            TransactionData.values['Memo'],
        ]
        append_trx(GSpreadHelper.sheet, upload_data)
        TransactionData.clear_transaction_data()
        await MyTeleBot.Instance.reply_to(message, '✅ Transaction Saved\n')

    @MyTeleBot.Instance.message_handler(regexp='^(A|a)dd(I|i)nc.+$', restrict=True)
    async def income_trx(message):
        """Add income transaction using Today's date, Inflow Amount and Memo"""
        TransactionData.clear_transaction_data()
        text = message.text
        result = list(shlex.split(text))

        del result[0]

        paramCount = len(result)
        if paramCount != 2:
            await MyTeleBot.Instance.reply_to(
                message, f'Expected 2 parameters, received {paramCount}: [{result}]')
            return
        else:
            inflow, memo = result
            TransactionData.values['Date'] = DateUtil.date_today()
            TransactionData.values['Inflow'] = inflow
            TransactionData.values['Memo'] = memo

        await quick_save(message)

    @MyTeleBot.Instance.message_handler(regexp='^(A|a)dd(E|e)xp.+$', restrict=True)
    async def expense_trx(message):
        """Add expense transaction using Today's date, Outflow Amount and Memo"""
        TransactionData.clear_transaction_data()
        text = message.text
        result = list(shlex.split(text))

        del result[0]

        paramCount = len(result)
        if paramCount != 2:
            await MyTeleBot.Instance.reply_to(
                message, f'Expected 2 parameters, received {paramCount}: [{result}]')
            return
        else:
            outflow, memo = result
            TransactionData.values['Date'] = DateUtil.date_today()
            TransactionData.values['Outflow'] = outflow
            TransactionData.values['Memo'] = memo

        await quick_save(message)

    async def item_selected(action: Action, user_id, message_id):
        await MyTeleBot.Instance.set_state(user_id, action)

        data = TransactionData.values[action.name.capitalize()]
        if action == Action.outflow or action == Action.inflow:
            displayData = (Configuration.values['currency'] +
                           f' {data}') if data != '' else '\'\''
        else:
            displayData = data if data != '' else '\'\''

        text = f'\[Current Value: ' + f' *{displayData}*]' + '\n' + \
            f'Enter {action.name.capitalize()} : '
        await MyTeleBot.Instance.edit_message_text(chat_id=user_id, message_id=message_id,
                                                   text=text, reply_markup=KeyboardUtil.create_save_keyboard('save'))

    @MyTeleBot.Instance.callback_query_handler(func=None, config=KeyboardUtil.actions.filter(), state=Action.start, restrict=True)
    async def actions_callback(call: types.CallbackQuery):
        callback_data: dict = KeyboardUtil.actions.parse(
            callback_data=call.data)
        actionId = int(callback_data['action_id'])
        action = Action(actionId)
        user_id = call.from_user.id
        message_id = call.message.message_id

        await item_selected(action, user_id, message_id)

    @MyTeleBot.Instance.message_handler(state=Action.outflow, restrict=True)
    async def get_outflow(message):
        TransactionData.values['Outflow'] = message.text

    @MyTeleBot.Instance.callback_query_handler(func=lambda c: c.data == 'save')
    async def save_callback(call: types.CallbackQuery):
        await MyTeleBot.Instance.set_state(call.from_user.id, Action.start)
        await MyTeleBot.Instance.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                                   text='Update:', reply_markup=KeyboardUtil.create_options_keyboard())

    @MyTeleBot.Instance.callback_query_handler(func=lambda c: c.data == 'quick_save')
    async def savequick_callback(call: types.CallbackQuery):
        await MyTeleBot.Instance.current_states.finish(call.from_user.id)
        await upload(call.message)

    @MyTeleBot.Instance.message_handler(commands=['start', 's'], restrict=True)
    async def command_start(message):
        """
        Start the conversation and ask user for input.
        Initialize with options to fill in.
        """
        await MyTeleBot.Instance.set_state(message.from_user.id, Action.start)
        await MyTeleBot.Instance.send_message(message.chat.id, 'Select Option:', reply_markup=KeyboardUtil.create_default_options_keyboard())

    def main() -> None:
        """Run the bot."""
        asyncio.run(MyTeleBot.Instance.polling())


if __name__ == '__main__':
    Configuration.get_values()
    MyTeleBot.init()
    App.main()
