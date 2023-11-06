# aspire-splitwise-telegram-bot

A telegram bot that connects to [Aspire Budgeting](https://aspirebudget.com/) and [Splitwise](splitwise.com) (WIP)

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

Configure .env:

```
export CURRENCY=₱
export TOKEN=
export UPDATE_MODE=webhook
export APP_NAME=
export RESTRICT_ACCESS=True
export USER_IDS=
export CREDENTIALS=
export WORKSHEET_ID=
export PORT=
export SECRET=
export RUN_ASYNC=False
export GIT_WEBHOOK=
export API_TOKEN=
export CONSUMER_KEY=
export CONSUMER_SECRET=
export SPLITWISE_TOKEN=
export FRIEND_ID=
export GROUP_ID=
```

1. Follow this [gspread docs](https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account) to get your API key and share spreadsheet access to the service account.
   Add the base64 encoded json string to _**crdentials_json**_
2. Copy **your** Aspire Budgeting spreadsheet key (obtained from the url e.g. _1jUkhoC3CbaO0H4H01iYtTNPf1-ybi0UQ4aZ2aBG7q40_) to _**gsheet_worksheet_id**_
3. Get your telegram API key from [BotFather](https://t.me/botfather) and add it to _**telegram_token**_
4. Set _**restrict_access**_ to true if you want to limit access to certain users. If so, add the telegram user ids to _**list_of_users**_

Run the bot with:

```
python app.py
```

Deploy in Docker:

```
docker build -t [name] .

Make sure to setup config vars in config.env file

docker run --rm -it -p [port:port] --env-file [config.env] name
```

Deploy in PythonAnywhere:

Setup environment [Virtual Env Setup](https://help.pythonanywhere.com/pages/Virtualenvs)

```
workon [virtual_env_name]

pip install --no-cache-dir --upgrade pip -r requirements.txt

Make sure to setup config vars

Modify wsgi app as needed /var/www/[username]_pythonanywhere_com_wsgi.py
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
