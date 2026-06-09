# run this once locally to generate token.json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials as GoogleCredentials


import logging , os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

token_path = os.getenv("GMAIL_TOKEN_FILE", "token.json")

def validate_token():
    """Make a test API call to validate the token."""
    try:
        if not os.path.exists(token_path):
            return False
        creds = GoogleCredentials.from_authorized_user_file(token_path)
        # auto-refresh if expired
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
            return True
        return not creds.expired
    except Exception as e:
        logger.error(f"Token is invalid: {e}")
        return False


def gen_token():
    if validate_token():
        logger.info("Existing token is valid. No need to generate a new one.")
        return
    
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    cerd = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(cerd.to_json())
    logger.info("Token generated successfully. Save the following content as token.json:")
