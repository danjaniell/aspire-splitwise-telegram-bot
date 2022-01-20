from calendar import c
import os
import toml


class Configuration():
    file_config = toml.load('config.toml')
    values = {}

    def read_config(self) -> dict[str, str]:
        config = {
            'port': '',
            'token': '',
            'update_mode': '',
            'app_name': '',
        }

        ON_HEROKU = os.environ.get('ON_HEROKU')

        if ON_HEROKU:
            # get the heroku port
            config['port'] = os.environ.get('PORT', '8443')
            config['token'] = os.environ.get('TOKEN', 'token')
            config['update_mode'] = os.environ.get(
                'UPDATE_MODE', 'polling')
            config['app_name'] = os.environ.get(
                'HEROKU_APP_NAME', 'heroku_app_name')
        else:
            config['port'] = self.file_config['app']['port']
            config['token'] = self.file_config['telegram']['telegram_token']
            config['update_mode'] = self.file_config['app']['update_mode']
            config['app_name'] = self.file_config['app']['app_name']

        return config

    def get_values(self):
        if (not hasattr(self.values, 'token')):
            self.values = self.read_config(self)
