# run this once locally to generate token.json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

# save it
with open("token.json", "w") as f:
    f.write(creds.to_json())

print("Done — token.json created")