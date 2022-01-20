import gspread
from app_config import Configuration
from aspire_util import get_accounts, get_all_categories


class GSpreadHelper():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive',
    ]

    def get_client(self):
        return gspread.service_account(
            filename=Configuration.values['gsheet']['gsheet_api_key_filepath'], scopes=self.scope)

    def get_sheet(self):
        return self.client.open_by_key(
            Configuration.values['gsheet']['gsheet_worksheet_id'])

    def fetch_categories(self):
        return get_all_categories(self.sheet)

    def fetch_accounts(self):
        accounts = get_accounts(self.sheet)
        return [item for sublist in accounts for item in sublist]
