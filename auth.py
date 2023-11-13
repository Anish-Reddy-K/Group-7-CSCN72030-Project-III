import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

# The scopes required for accessing Google Drive files
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/userinfo.profile"]

def authenticate(credentials_path):
    creds = None

    # Check if token.json file exists and load credentials if available
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If no valid credentials are available, prompt the user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Perform the OAuth2.0 authorization flow
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds



def create_folder(service, folder_name, parent_folder_id=None):
    # Check if the folder already exists
    folder_exists = False
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    results = service.files().list(q=query).execute()
    items = results.get('files', [])
    if items:
        folder_exists = True
        print(f'Folder "{folder_name}" already exists.')
        return items[0]['id']

    # Create metadata for the folder to be created
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }

    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]

    # Execute API call to create the folder
    folder = service.files().create(body=file_metadata, fields='id').execute()
    print(f'Folder "{folder_name}" created with ID: {folder["id"]}')
    return folder['id']

def add_editor_permission(service, folder_id, email):
    # Define the permission body
    permission = {
        'type': 'user',
        'role': 'writer',  # 'writer' grants editor permissions
        'emailAddress': email
    }

    # Execute API call to add permission
    service.permissions().create(fileId=folder_id, body=permission).execute()
    print(f'Permission added for {email} as editor.')

def load_users_data(file_path):
    # Load existing users' data from the JSON file
    users_data = {}
    try:
        with open(file_path, "r") as json_file:
            users_data = json.load(json_file)
    except (json.JSONDecodeError, FileNotFoundError):
        # Handle the case when the file is empty or not properly formatted
        print(f"Warning: Unable to load data from {file_path}. Starting with an empty user data dictionary.")

    return users_data


def save_users_data(file_path, users_data):
    # Save updated users' data to the JSON file
    with open(file_path, "w") as json_file:
        json.dump(users_data, json_file, indent=2)

def add_user_data(users_data, user_email, friendlens_folder_id, home_folder_id, feed_folder_id, full_name):
    # Add user's data to the dictionary
    users_data[user_email] = {
        "name": full_name,
        "friendlens_folder_id": friendlens_folder_id,
        "home_folder_id": home_folder_id,
        "feed_folder_id": feed_folder_id,
    }

def main(credentials_path, folder_name, users_json_path):
    try:
        creds = authenticate(credentials_path)
        drive_service = build("drive", "v3", credentials=creds)

        # Fetch authenticated user's email
        user_info = drive_service.about().get(fields="user").execute()
        editor_email = user_info["user"]["emailAddress"]

        friendlens_folder_id = create_folder(drive_service, folder_name)
        home_folder_id = create_folder(drive_service, "home", parent_folder_id=friendlens_folder_id)
        feed_folder_id = create_folder(drive_service, "feed", parent_folder_id=friendlens_folder_id)

        add_editor_permission(drive_service, friendlens_folder_id, editor_email)

        # Load existing users' data
        users_data = load_users_data(users_json_path)

                # Fetch user's full name from the People API
        service = build("people", "v1", credentials=creds)
        person_info = service.people().get(resourceName="people/me", personFields="names").execute()
        full_name = person_info.get("names", [{}])[0].get("displayName", "Unknown")

        # Check if the user's data is already in the JSON file
        if editor_email not in users_data:
            # If not, add the user's data
            add_user_data(users_data, editor_email, friendlens_folder_id, home_folder_id, feed_folder_id, full_name)

            # Save the updated users' data to the JSON file
            save_users_data(users_json_path, users_data)
            print(f"User {editor_email} added to the JSON file.")

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    credentials_path = "C:\\Users\\prais\\OneDrive\\Desktop\\csecret.json"
    folder_name = "FriendLens"
    users_json_path = "C:\\Users\\prais\\OneDrive\\Desktop\\user_data.json"

    main(credentials_path, folder_name, users_json_path)