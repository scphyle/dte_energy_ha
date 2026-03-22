DOMAIN = "dte_energy"
PLATFORMS = ["sensor"]

# API
NEWLOOK_BASE_URL = "https://newlook.dteenergy.com"
USAGE_BASE_URL = "https://api.customer.sites.dteenergy.com"
APIM_SUBSCRIPTION_KEY = "f3388b16c3e04a06a48c28c75520f416"

URL_TOKEN_REFRESH = f"{NEWLOOK_BASE_URL}/api/tokenRefresh"
URL_USER_DETAILS = f"{NEWLOOK_BASE_URL}/api/getUserDetails"
URL_BILL_DATA = f"{NEWLOOK_BASE_URL}/api/currentBillData"
URL_USAGE = f"{USAGE_BASE_URL}/public/usage/authenticated/accounts/{{account_number}}/usage/intervals/day/electric/timeOfDay"

# Config entry keys
CONF_WEB_SECURITY_TOKEN = "web_security_token"
CONF_ACCOUNT_NUMBER = "account_number"

# Coordinator
SCAN_INTERVAL_MINUTES = 30
TOKEN_REFRESH_BUFFER_SECONDS = 300  # refresh 5 min before expiry