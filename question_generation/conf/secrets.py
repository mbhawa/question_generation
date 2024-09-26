import os

import dotenv

dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ORG_ID = os.getenv("ORG_ID")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")