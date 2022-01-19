# aspire-telegram-async-bot

A telegram bot that connects to [Aspire Budgeting](https://aspirebudget.com/).

To start creating a transactions:

```
/start
```

Supports quick add transaction (Expense/Income):

```
AddExp [Amount] "Put some text here for remarks"
AddInc [Amount] "Put some text here for remarks"
```

More features will be added progressively.

## Usage

Copy and rename `config.toml.example` to `config.toml` file needs to be filled in with your credentials.

1. Follow this [gspread docs](https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account) to get your API key and share spreadsheet access to the service account.
   Add the file path to _**gsheet_api_key_filepath**_
2. Copy **your** Aspire Budgeting spreadsheet key (obtained from the url e.g. _1jUkhoC3CbaO0H4H01iYtTNPf1-ybi0UQ4aZ2aBG7q40_) to _**gsheet_worksheet_id**_
3. Get your telegram API key from [BotFather](https://t.me/botfather) and add it to _**telegram_token**_
4. Set _**restrict_access**_ to true if you want to limit access to certain users. If so, add the telegram user ids to _**list_of_users**_

Run the bot with:

```
python app.py
```

Deploy in Heroku:

```
Create heroku app (or use existing)

Make sure to setup config vars

using heroku cli:
heroku container:push -a [heroku_app_name] web & heroku container:release -a [heroku_app_name] web
```

Deploy in Google Cloud Platform:

```
export TOKEN={TELEGRAM_TOKEN}

export PROJECT_ID={GOOGLE_PROJECT_ID}

gcloud beta run deploy bot \
    --source . \
    --set-env-vars TOKEN=${TOKEN} \
    --platform managed \
    --allow-unauthenticated \
    --project ${PROJECT_ID}

curl "https://api.telegram.org/bot${TOKEN}/setWebhook?url=$(gcloud run services describe bot --format 'value(status.url)' --project ${PROJECT_ID})"
```
