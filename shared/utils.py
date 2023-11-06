import calendar
import datetime
from itertools import groupby

from gspread import utils
from kink import di
from splitwise import Splitwise
from splitwise.expense import Expense
from splitwise.user import ExpenseUser
from telebot import types


def get_all_categories(spreadsheet) -> dict[str, list]:
    worksheet = spreadsheet.worksheet("Configuration")
    values = worksheet.get("r_ConfigurationData")

    # Find groups and exclude credit card payments
    groups = [i[1]
              for i in values if i[0] == "✦" and "Credit Card" not in i[1]]

    # get categories from configuration worksheet
    categories = []
    for k, g in groupby(values, key=lambda x: x[0] != "✦" and x[0] != "◘"):
        if k:
            categories.append(list(g))
    categories_titles = [[k[1] for k in i] for i in categories]

    grouped_cats = dict(zip(groups, categories_titles))
    # Add missing options
    category = worksheet.get("TransactionCategories")
    grouped_cats["Others"] = list(
        set([i for j in category for i in j])
        ^ set([i for j in categories_titles for i in j])
    )

    return grouped_cats


def get_accounts(spreadsheet):
    worksheet = spreadsheet.worksheet("Configuration")
    accounts = worksheet.get("cfg_Accounts")
    cards = worksheet.get("cfg_Cards")
    accounts.extend(cards)
    return sorted(accounts)


def append_trx(spreadsheet, data: list[str]):
    worksheet = spreadsheet.worksheet("Transactions")
    next_row = next(n for n in worksheet.range("trx_Dates") if n.value == "")
    rowRange = next_row.address + ":H" + str(next_row.row)
    worksheet.append_row(
        values=data,
        table_range=rowRange,
        value_input_option=utils.ValueInputOption.user_entered,
        insert_data_option=0,
    )


def separate_callback_data(data):
    """Separate the callback data"""
    return data.split(";")


def create_calendar_callback_data(action, year, month, day):
    """Create the callback data associated to each button"""
    return "CALENDAR" + ";" + ";".join([action, str(year), str(month), str(day)])


def create_calendar(year=None, month=None):
    """
    Create an inline keyboard with the provided year and month
    """
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    data_ignore = create_calendar_callback_data("IGNORE", year, month, 0)
    keyboard = []
    # First row - Month and Year
    row = [
        types.InlineKeyboardButton(
            calendar.month_name[month] + " " + str(year), callback_data=data_ignore
        )
    ]
    keyboard.append(row)
    # Second row - Week Days
    row = []
    for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
        row.append(types.InlineKeyboardButton(day, callback_data=data_ignore))
    keyboard.append(row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(
                    " ", callback_data=data_ignore))
            else:
                row.append(
                    types.InlineKeyboardButton(
                        str(day),
                        callback_data=create_calendar_callback_data(
                            "DAY", year, month, day
                        ),
                    )
                )
        keyboard.append(row)
    # Last row - Buttons
    row = [
        types.InlineKeyboardButton(
            "<",
            callback_data=create_calendar_callback_data(
                "PREV-MONTH", year, month, day),
        ),
        types.InlineKeyboardButton(" ", callback_data=data_ignore),
        types.InlineKeyboardButton(
            ">",
            callback_data=create_calendar_callback_data(
                "NEXT-MONTH", year, month, day),
        ),
    ]
    keyboard.append(row)

    return types.InlineKeyboardMarkup(keyboard)


async def async_process_calendar_selection(call, bot_instance):
    """
    Process the callback_query. This method generates a new calendar if forward or
    backward is pressed. This method should be called inside a CallbackQueryHandler.
    """
    ret_data = (False, None)
    (_, action, year, month, day) = separate_callback_data(call.data)
    curr = datetime.datetime(int(year), int(month), 1)
    if action == "IGNORE":
        await bot_instance.answer_callback_query(callback_query_id=call.id)
    elif action == "DAY":
        ret_data = True, datetime.datetime(int(year), int(month), int(day))
    elif action == "PREV-MONTH":
        pre = curr - datetime.timedelta(days=1)
        await bot_instance.edit_message_text(
            text=call.message.text,
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=create_calendar(int(pre.year), int(pre.month)),
        )
    elif action == "NEXT-MONTH":
        ne = curr + datetime.timedelta(days=31)
        await bot_instance.edit_message_text(
            text=call.message.text,
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=create_calendar(int(ne.year), int(ne.month)),
        )
    else:
        await bot_instance.answer_callback_query(
            callback_query_id=call.id, text="Something went wrong!"
        )
    return ret_data


def process_calendar_selection(call, bot_instance):
    """
    Process the callback_query. This method generates a new calendar if forward or
    backward is pressed. This method should be called inside a CallbackQueryHandler.
    """
    ret_data = (False, None)
    (_, action, year, month, day) = separate_callback_data(call.data)
    curr = datetime.datetime(int(year), int(month), 1)
    if action == "IGNORE":
        bot_instance.answer_callback_query(callback_query_id=call.id)
    elif action == "DAY":
        ret_data = True, datetime.datetime(int(year), int(month), int(day))
    elif action == "PREV-MONTH":
        pre = curr - datetime.timedelta(days=1)
        bot_instance.edit_message_text(
            text=call.message.text,
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=create_calendar(int(pre.year), int(pre.month)),
        )
    elif action == "NEXT-MONTH":
        ne = curr + datetime.timedelta(days=31)
        bot_instance.edit_message_text(
            text=call.message.text,
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=create_calendar(int(ne.year), int(ne.month)),
        )
    else:
        bot_instance.answer_callback_query(
            callback_query_id=call.id, text="Something went wrong!"
        )
    return ret_data


def create_category_callback_data(action, selection):
    return action + ";" + selection


def create_category_inline(options, action):
    cats_keyboard = [list(options)[i: i + 2]
                     for i in range(0, len(list(options)), 2)]
    for i, x in enumerate(cats_keyboard):
        for j, k in enumerate(x):
            cats_keyboard[i][j] = types.InlineKeyboardButton(
                k, callback_data=create_category_callback_data(action, str(k))
            )
    if action == "save":
        cats_keyboard.append(
            [
                types.InlineKeyboardButton(
                    "< Back",
                    callback_data=create_category_callback_data(
                        "back", "category"),
                )
            ]
        )
    return types.InlineKeyboardMarkup(cats_keyboard)


def create_account_inline(trx_accounts, action):
    accs_keyboard = [trx_accounts[i: i + 2]
                     for i in range(0, len(trx_accounts), 2)]
    for i, x in enumerate(accs_keyboard):
        for j, k in enumerate(x):
            accs_keyboard[i][j] = types.InlineKeyboardButton(
                k, callback_data=create_category_callback_data(action, str(k))
            )
    return types.InlineKeyboardMarkup(accs_keyboard)


def get_subcategories(categories, name):
    subcategories = []
    for category in categories:
        if category.name == name:
            subcategories = [
                subcategory.name for subcategory in category.subcategories]
            break
    return subcategories


def get_id_name_mapping(splitwise: Splitwise):
    friends = splitwise.getFriends()
    return {friend.getId(): f'{get_friend_full_name(friend)}' for friend in friends}


def get_friend_full_name(friend):
    first_name = friend.getFirstName()
    return f'{first_name} {friend.getLastName()}' if friend.getLastName() is not None else first_name


def create_expense_object(splitwise: Splitwise, payer_id, payee_id, group_id, categoryName, amount, description):
    expense = Expense()
    expense.setCost(amount)
    expense.setDescription(description)
    expense.setGroupId(group_id)
    category = next(
        (subcat for c in di["sw_categories"] for subcat in c.subcategories if subcat.name == categoryName), None)
    expense.setCategory(category)

    payer = ExpenseUser()
    payer.setId(payer_id)
    payer.setPaidShare(amount)
    payer.setOwedShare(0.00)

    payee = ExpenseUser()
    payee.setId(payee_id)
    payee.setPaidShare(0.00)
    payee.setOwedShare(amount)

    users = [payer, payee]
    expense.setUsers(users)
    expense = splitwise.createExpense(expense)

    return expense
