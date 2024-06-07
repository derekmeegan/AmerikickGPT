from google.oauth2 import service_account
import gspread
from dotenv import dotenv_values
import json


config = dotenv_values('.env')

service_account_info = json.loads(config["GOOGLE_SHEET_CREDENTIALS"])

credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
client = gspread.authorize(credentials)
sheet = client.open_by_key(config.get('GOOGLE_SHEET_ID'))