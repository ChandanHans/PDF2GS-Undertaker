import json
import os
from dotenv import load_dotenv

from .utils import resource_path


load_dotenv(dotenv_path=resource_path(".env"))


GPT_KEY = os.environ["GPT_KEY"]
CREDS_JSON = json.loads(os.environ["CREDS_JSON"])
ASSISTANT_ID = "asst_Wrua6AjqnBlWvXM9IOWcSfot"
UNDERTAKER_SHEET_KEY = "12xP7d6R-lhoT39z2b4Jk2Ap07bP_nN6m1j2UXMHaVuk"
FOLDER_ID1 = '1VrTXTEhSKh3E-vkUKbiF-5UqU0K41bgk'
FOLDER_ID2 = '1U7ndJLnj8A7OZc4a9gbIc7RWuSZg4pUg'
SHEET_ID = '1gfaZg1Pju51w7NrjB5PvXNyymWD7_clsXFc8Zbjc33I'
INPUT_FOLDER = "./Input"
OUTPUT_FOLDER = "./Output"
IMAGE_FOLDER = "./images"
COMPLETED_FOLDER = "./Completed"
TOKEN_FILE = 'token.pickle'