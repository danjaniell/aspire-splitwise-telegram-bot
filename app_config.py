import os
import toml
import base64
import json
from dotenv import load_dotenv


class Configuration:
    def __init__(self):
        self.get_values()

    load_dotenv()
    values = {}

    def read_config(self) -> dict[str, str]:
        config = {
            "currency": "",
            "port": 0,
            "token": "",
            "secret": "",
            "update_mode": "",
            "app_name": "",
            "restrict_access": False,
            "list_of_users": [],
            "credentials_json": {},
            "worksheet_id": "",
            "webhook_base_url": "",
            "run_async": True,
        }

        ON_HEROKU = os.getenv("ON_HEROKU", "False").lower() in ("true", "1")
        ON_DOCKER = os.getenv("ON_DOCKER", "False").lower() in ("true", "1")
        ON_PYTHONANYWHERE = os.getenv("ON_PYTHONANYWHERE", "False").lower() in (
            "true",
            "1",
        )

        config["currency"] = os.environ.get("CURRENCY", "₱")
        config["port"] = int(os.environ.get("PORT", "8443"))
        config["token"] = os.environ.get("TOKEN", "no_token")
        config["secret"] = os.environ.get("SECRET", "no_secret")
        config["update_mode"] = os.environ.get("UPDATE_MODE", "polling")
        config["app_name"] = os.environ.get("APP_NAME", "app_name")
        config["restrict_access"] = os.getenv(
            "RESTRICT_ACCESS", "False"
        ).lower() in ("true", "1")
        config["list_of_users"] = [
            int(i)
            for i in list(
                filter(
                    None, os.environ.get("USER_IDS", "").replace(
                        " ", "").split(",")
                )
            )
        ]
        config["credentials_json"] = json.loads(
            base64.b64decode(os.environ.get("CREDENTIALS", ""))
        )
        config["worksheet_id"] = os.environ.get("WORKSHEET_ID", "")
        config["run_async"] = os.getenv("RUN_ASYNC", "False").lower() in (
            "true",
            "1",
        )

        if ON_HEROKU:
            config["webhook_base_url"] = "https://%s.herokuapp.com" % (
                config["app_name"]
            )

        config["webhook_base_url"] = "https://%s.pythonanywhere.com" % (
            config["app_name"]
        )

        return config

    def get_values(self):
        if not hasattr(self.values, "token"):
            self.values = self.read_config()
