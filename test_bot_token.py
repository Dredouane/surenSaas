import os
from app.api.telegram_core import get_bot_token
# Mock bot_config
bot_config = {'bot_username': 'Arev_travaux_test_e2e_bot'}
os.environ["TEST_TELEGRAM_CONSTRUCTION_E2E_BOT_TOKEN"] = "REDACTED_BOT_TOKEN"

token = get_bot_token(bot_config)
print(f"Token retrieved: {token}")
