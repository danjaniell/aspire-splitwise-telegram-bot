from calendar import c
import os
import toml


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
        }

        ON_HEROKU = os.environ.get('ON_HEROKU')

        if ON_HEROKU:
            config['currency'] = os.environ.get('CURRENCY', '₱')
            config['port'] = os.environ.get('PORT', '8443')
            config['token'] = os.environ.get('TOKEN', 'token')
            config['update_mode'] = os.environ.get(
                'UPDATE_MODE', 'polling')
            config['app_name'] = os.environ.get(
                'HEROKU_APP_NAME', 'heroku_app_name')
            config['restrict_access'] = os.environ.get(
                'RESTRICT_ACCESS', False)
            config['list_of_users'] = os.environ.get('USER_IDS', [])
        else:
            config['currency'] = self.file_config['currency']
            config['port'] = self.file_config['app']['port']
            config['token'] = self.file_config['telegram']['telegram_token']
            config['update_mode'] = self.file_config['app']['update_mode']
            config['app_name'] = self.file_config['app']['app_name']
            config['restrict_access'] = self.file_config['telegram']['restrict_access']
            config['list_of_users'] = self.file_config['telegram']['list_of_users']

        return config

    def get_values(self):
        if (not hasattr(self.values, 'token')):
            self.values = self.read_config()
