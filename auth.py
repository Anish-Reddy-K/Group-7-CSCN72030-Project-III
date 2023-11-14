from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os.path
import json
import os
import cv2
import face_recognition
import numpy as np

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
        "training_status": "False",
    }

def upload_file_to_folder(service, file_metadata, media):
    try:
        # Execute API call to upload the file
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        print(f'File ID: {file.get("id")}')
        return file.get("id")

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None
    
def upload_image_to_home(service, home_folder_id, file_path):
    try:
        # Extract file name from the path
        file_name = os.path.basename(file_path)

        # Set up file metadata
        file_metadata = {"name": file_name, "parents": [home_folder_id]}  # Specify the parent folder

        # Set up media upload
        media = MediaFileUpload(file_path, mimetype="image/jpeg")

        # Upload the image to the home folder
        upload_file_to_folder(service, file_metadata, media)

    except HttpError as error:
        print(f"An error occurred: {error}")

def train_image(image_path, user_email):
    known_face_encodings = []

    # Load existing encodings if available
    if Path('known_face_encodings.json').is_file() and Path('known_face_encodings.json').stat().st_size > 0:
        with open('known_face_encodings.json', 'r') as json_file:
            try:
                known_face_encodings = json.load(json_file)
            except json.decoder.JSONDecodeError:
                print("Error: The existing JSON file is not valid. Creating a new one.")

    # Convert Path object to string
    image_path_str = str(image_path)

    # Load the image to train
    img = cv2.imread(image_path_str)
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Get the filename only from the initial file path.
    basename = Path(image_path_str).name
    (filename, ext) = os.path.splitext(basename)

    # Get encoding
    img_encoding = face_recognition.face_encodings(rgb_img)[0]

    # Store email ID and face encoding in a dictionary
    known_face_encodings.append({"email": user_email, "encoding": img_encoding.tolist()})  # Convert to list

    # Save the updated known_face_encodings to a JSON file
    with open('known_face_encodings.json', 'w') as json_file:
        json.dump(known_face_encodings, json_file)

    print(f"Image '{filename}' trained and encoding saved.")


def load_known_faces_from_json(json_file_path):
    known_face_encodings = []
    known_face_names = []

    with open(json_file_path, 'r') as file:
        trained_faces = json.load(file)

    for face_data in trained_faces:
        email = face_data["email"]
        encoding_list = face_data["encoding"]
        encoding_np = np.array(encoding_list)
        known_face_encodings.append({"email": email, "encoding": encoding_np})
        known_face_names.append(email)

    return known_face_encodings, known_face_names

def detect_known_faces(frame, known_face_encodings):
    frame_resizing = 0.25
    small_frame = cv2.resize(frame, (0, 0), fx=frame_resizing, fy=frame_resizing)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    detected_faces = []
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces([f["encoding"] for f in known_face_encodings], face_encoding)
        email = "Unknown"

        face_distances = face_recognition.face_distance([f["encoding"] for f in known_face_encodings], face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            email = known_face_encodings[best_match_index]["email"]
            detected_faces.append(email)

    return detected_faces

def main(credentials_path, folder_name, users_json_path):
    try:
        creds = authenticate(credentials_path)
        drive_service = build("drive", "v3", credentials=creds)

        # Fetch authenticated user's email
        user_info = drive_service.about().get(fields="user").execute()
        user_email = user_info["user"]["emailAddress"]
        editor_email = "friendlens2@gmail.com"
        friendlens_folder_id = create_folder(drive_service, folder_name)
        home_folder_id = create_folder(drive_service, "home", parent_folder_id=friendlens_folder_id)
        feed_folder_id = create_folder(drive_service, "feed", parent_folder_id=friendlens_folder_id)

        add_editor_permission(drive_service, friendlens_folder_id, editor_email)

        # Load existing users' data
        users_data = load_users_data(users_json_path)

        # Fetch user's full name from the People API
        people_service = build("people", "v1", credentials=creds)
        person_info = people_service.people().get(resourceName="people/me", personFields="names").execute()
        full_name = person_info.get("names", [{}])[0].get("displayName", "Unknown")

        # Check if the user's data is already in the JSON file
        if user_email not in users_data:
            # If not, add the user's data
            add_user_data(users_data, user_email, friendlens_folder_id, home_folder_id, feed_folder_id, full_name)

            # Save the updated users' data to the JSON file
            save_users_data(users_json_path, users_data)
            print(f"User {user_email} added to the JSON file.")

        # Example image file upload to the home folder
        users_data = load_users_data(users_json_path)
        if users_data[user_email]["training_status"]=="False":
            train_image_path=Path(input("Please enter the training file path: "))
            train_image(train_image_path, user_email)
            users_data[user_email]["training_status"]="True"
            save_users_data(users_json_path, users_data)
        while True:
            num=input("Type 1 to upload image: ")
            if num=='1':
                image_file_path = Path(input("Please enter the file path: "))  # Replace with the actual image file path
                upload_image_to_home(drive_service, home_folder_id, image_file_path)
                # Example usage
                known_face_encodings, known_face_names = load_known_faces_from_json("known_face_encodings.json")
                image_path_str = str(image_file_path)
                frame = cv2.imread(image_path_str)  # Replace with the path to your image
                detected_faces = detect_known_faces(frame, known_face_encodings)
                if user_email in detected_faces:
                    detected_faces.remove(user_email)
                users_data = load_users_data(users_json_path)
                feed_folder_ids = []
                for email in detected_faces:
                    if email in users_data:
                        feed_folder_id = users_data[email]["feed_folder_id"]
                        feed_folder_ids.append(feed_folder_id)
                for feed_id in feed_folder_ids:
                    print(feed_id)
                    #upload to link
            else:
                break

    except HttpError as err:
        print(err)


if __name__ == "__main__":
    credentials_path = "C:\\Users\\prais\\OneDrive\\Desktop\\FriendLens\\csecret.json"
    folder_name = "FriendLens"
    users_json_path = "C:\\Users\\prais\\OneDrive\\Desktop\\FriendLens\\user_data.json"

    main(credentials_path, folder_name, users_json_path)