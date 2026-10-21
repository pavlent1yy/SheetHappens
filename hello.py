import os

import gspread
from dotenv import load_dotenv

load_dotenv()

gc = gspread.service_account(filename=os.getenv("GOOGLE_CREDENTIALS", "credits.json"))
sheet = gc.open_by_key(os.environ["SPREADSHEET_ID"]).sheet1
sheet.update_acell("B12", "Hello from Python!")
print("OK")
