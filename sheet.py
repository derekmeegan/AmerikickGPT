from google.oauth2 import service_account
import gspread
from dotenv import load_dotenv
import json
import os

load_dotenv()

service_account_info = json.loads(os.environ["GOOGLE_SHEET_CREDENTIALS"])

credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
client = gspread.authorize(credentials)
sheet = client.open_by_key(os.environ.get('GOOGLE_SHEET_ID'))