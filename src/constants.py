import json
import os
from dotenv import load_dotenv

from .utils import resource_path


load_dotenv(dotenv_path=resource_path(".env"))


GPT_KEY = os.environ["GPT_KEY"]
CREDS_JSON = json.loads(os.environ["CREDS_JSON"])
ASSISTANT_ID = "asst_Wrua6AjqnBlWvXM9IOWcSfot"
UNDERTAKER_SHEET_KEY = "12xP7d6R-lhoT39z2b4Jk2Ap07bP_nN6m1j2UXMHaVuk"
FOLDER_ID1 = '16r80-Mq5jDo6Lj9svu0hD7ULYMyyUnHp'
FOLDER_ID2 = '1LLs654QFtyzQ5iVqcdkV0HrnI3HC_8b6'
IMAGE_SHEET_ID = '1e4GzXCftJYFRbh3xKWnvRK8zE-FjOUut7FinhFj-2ug'
INPUT_FOLDER = "./Input"
OUTPUT_FOLDER = "./Output"
IMAGE_FOLDER = "./images"
COMPLETED_FOLDER = "./Completed"
TOKEN_FILE = 'token.pickle'