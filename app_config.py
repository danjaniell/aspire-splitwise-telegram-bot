from calendar import c
import os
import toml
import base64
import json


class Configuration():
    def __init__(self):
        self.get_values()

    file_config = toml.load('config.toml')
    values = {}

    def read_config(self) -> dict[str, str]:
        config = {
            'currency': '',
            'port': '',
            'token': '',
            'update_mode': '',
            'app_name': '',
            'restrict_access': False,
            'list_of_users': [],
            'credentials_json': {},
            'worksheet_id': '',
        }

        ON_HEROKU = os.environ.get('ON_HEROKU')
        ON_DOCKER = os.environ.get('ON_DOCKER')

        if ON_HEROKU or ON_DOCKER:
            config['currency'] = os.environ.get('CURRENCY', '₱')
            config['port'] = os.environ.get('PORT', '8443')
            config['token'] = os.environ.get('TOKEN', 'no_token')
            config['update_mode'] = os.environ.get(
                'UPDATE_MODE', 'polling')
            config['app_name'] = os.environ.get(
                'HEROKU_APP_NAME', 'heroku_app_name')
            config['restrict_access'] = os.environ.get(
                'RESTRICT_ACCESS', False)
            config['list_of_users'] = [int(i) for i in list(
                filter(None, os.environ.get('USER_IDS', '').replace(' ', '').split(',')))]
            config['credentials_json'] = json.loads(base64.b64decode(
                os.environ.get('CREDENTIALS', '')))
            config['worksheet_id'] = os.environ.get('WORKSHEET_ID', '')
        else:
            config['currency'] = self.file_config['currency']
            config['port'] = self.file_config['app']['port']
            config['token'] = self.file_config['telegram']['telegram_token']
            config['update_mode'] = self.file_config['app']['update_mode']
            config['app_name'] = self.file_config['app']['app_name']
            config['restrict_access'] = self.file_config['telegram']['restrict_access']
            config['list_of_users'] = self.file_config['telegram']['list_of_users']
            config['credentials_json'] = json.loads(base64.b64decode(
                self.file_config['gsheet']['credentials_json']))
            config['worksheet_id'] = self.file_config['gsheet']['gsheet_worksheet_id']

        return config

    def get_values(self):
        if (not hasattr(self.values, 'token')):
            self.values = self.read_config()
