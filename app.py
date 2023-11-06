import asyncio
import os
import time

import flask
from flask import Flask
from kink import di
from telebot import TeleBot, types
from telebot.async_telebot import AsyncTeleBot

import startup
from app_config import Configuration
from aspire.async_bot import async_bot_functions
from aspire.sync_bot import sync_bot_functions
from splitwiseSdk.bot import bot_functions

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# inject dependencies
startup.configure_services()

WEBHOOK_URL_BASE = di["WEBHOOK_URL_BASE"]
WEBHOOK_URL_PATH = "/%s/" % (di[Configuration]["secret"])

if di[Configuration]["run_async"]:
    async_bot_functions(di["bot_instance"])
else:
    sync_bot_functions(di["bot_instance"])

bot_functions(di["bot_instance"])

if isinstance(di["bot_instance"], AsyncTeleBot):
    asyncio.run(di["bot_instance"].delete_webhook(drop_pending_updates=True))
    time.sleep(0.5)
    if di[Configuration]["update_mode"] == "polling":
        asyncio.run(di["bot_instance"].infinity_polling(skip_pending=True))
    elif di[Configuration]["update_mode"] == "webhook":
        asyncio.run(
            di["bot_instance"].set_webhook(
                url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
        )
elif isinstance(di["bot_instance"], TeleBot):
    di["bot_instance"].delete_webhook(drop_pending_updates=True)
    time.sleep(0.5)
    if di[Configuration]["update_mode"] == "polling":
        di["bot_instance"].infinity_polling(skip_pending=True)
    elif di[Configuration]["update_mode"] == "webhook":
        di["bot_instance"].set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)


app = Flask(__name__)


@app.route(WEBHOOK_URL_PATH, methods=["POST"])
def receive_updates():
    if flask.request.headers.get("content-type") == "application/json":
        json_string = flask.request.get_data().decode("utf-8")
        update = types.Update.de_json(json_string)
        if isinstance(di["bot_instance"], AsyncTeleBot):
            asyncio.run(di["bot_instance"].process_new_updates([update]))
        elif isinstance(di["bot_instance"], TeleBot):
            di["bot_instance"].process_new_updates([update])
        return ""
    else:
        flask.abort(403)


if __name__ == "__main__":
    app.run(port=8084)
