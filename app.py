from flask import Flask, render_template, request, flash, redirect, url_for
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import secrets
import os.path
import json
import os
import cv2
import face_recognition
import numpy as np

secret_key = secrets.token_hex(16)
app = Flask(__name__)
app.secret_key = secret_key
file_locations = []
credentials_path = "C:/Users/Cyril/Downloads/csecret.json"
folder_name = "FriendLens"
users_json_path = "C:\\Users\\Cyril\\Desktop\\users_data.json"
# Set the upload folder
app.config["UPLOAD_FOLDER"] = "C:/Users/Cyril/Downloads/"
name = ""
gemail = ""
pfp = ""
trained = False
person_info = {}

# The scopes required for accessing Google Drive files
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/contacts.readonly", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/userinfo.profile",]

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

def add_editor_permission(service, folder_id):
    # Define the permission body
    permission = {
        'type': 'anyone',
        'role': 'writer'  # 'writer' grants editor permissions
    }

    # Execute API call to add permission
    service.permissions().create(fileId=folder_id, body=permission).execute()

def load_users_data(file_path):
    # Load existing users' data from the JSON file
    users_data = {}

    try:
        with open(file_path, "r") as json_file:
            # Attempt to load the JSON data
            loaded_data = json.load(json_file)

            if isinstance(loaded_data, list):
                # If the loaded data is a list, convert it to a dictionary
                for user_entry in loaded_data:
                    if isinstance(user_entry, dict):
                        for email, user_info in user_entry.items():
                            users_data[email] = user_info

            elif isinstance(loaded_data, dict):
                # If the loaded data is already a dictionary, use it directly
                users_data = loaded_data

    except (json.JSONDecodeError, FileNotFoundError):
        # Handle the case when the file is empty or not properly formatted
        print(f"Warning: Unable to load data from {file_path}. Starting with an empty user data dictionary.")

    return users_data

def save_users_data(file_path, users_data):
    # Save updated users' data to the JSON file
    with open(file_path, "w") as json_file:
        json.dump(users_data, json_file, indent=2)

def add_user_data(users_data, user_email, friendlens_folder_id, home_folder_id, feed_folder_id, full_name):
    
    if isinstance(users_data, list):
        # Case: users_data is a list of dictionaries
        
        for user_entry in users_data:
            if user_email in user_entry:
                # Update existing user entry
                user_entry[user_email]["name"] = full_name
                user_entry[user_email]["friendlens_folder_id"] = friendlens_folder_id
                user_entry[user_email]["home_folder_id"] = home_folder_id
                user_entry[user_email]["feed_folder_id"] = feed_folder_id
                return

        new_user_entry = {
            user_email: {
                "name": full_name,
                "friendlens_folder_id": friendlens_folder_id,
                "home_folder_id": home_folder_id,
                "feed_folder_id": feed_folder_id,
                "training_status": "False"
            }
        }
        users_data.append(new_user_entry)

    elif isinstance(users_data, dict):
        # Case: users_data is a dictionary
        if user_email in users_data:
            # Update existing user entry
            users_data[user_email]["name"] = full_name
            users_data[user_email]["friendlens_folder_id"] = friendlens_folder_id
            users_data[user_email]["home_folder_id"] = home_folder_id
            users_data[user_email]["feed_folder_id"] = feed_folder_id
        else:
            # If the user_email is not found, add a new entry
            users_data[user_email] = {
                "name": full_name,
                "friendlens_folder_id": friendlens_folder_id,
                "home_folder_id": home_folder_id,
                "feed_folder_id": feed_folder_id,
                "training_status": "False"
            }

def upload_file_to_folder(service, file_metadata, media):
    try:
        # Execute API call to upload the file
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        # print(f'File ID: {file.get("id")}')
        return file.get("id")

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def upload_image_to_home(service, home_folder_id, file_path):
    try:
        # Extract file name from the path
        file_name = os.path.basename(file_path)

        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"The file {file_path} does not exist.")
            return

        # Set up file metadata
        file_metadata = {"name": file_name, "parents": [home_folder_id]}  # Specify the parent folder

        # Set up media upload
        media = MediaFileUpload(file_path, mimetype="image/jpeg")

        # Upload the image to the home folder
        upload_file_to_folder(service, file_metadata, media)
        print(f"Uploaded file to folder  {home_folder_id}")
    except HttpError as error:
        print(f"An error occurred: {error}")


def train_image(image_path, user_email):
    known_face_encodings = []
    face_encoding_path = "C:\\Users\\Cyril\\Desktop\\known_face_encodings.json"
    # Load existing encodings if available
    if Path(face_encoding_path).is_file() and Path(face_encoding_path).stat().st_size > 0:
        with open(face_encoding_path, 'r') as json_file:
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
    with open(face_encoding_path, 'w') as json_file:
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

def initialize():
    global email, drive_service, friendlens_folder_id, home_folder_id, feed_folder_id, users_data, person_info, user_email, name
    drive_service = build("drive", "v3", credentials=creds)

    # Fetch authenticated user's email
    user_info = drive_service.about().get(fields="user").execute()
    user_email = user_info["user"]["emailAddress"]
    global gemail
    gemail = user_email
    email = user_email
    friendlens_folder_id = create_folder(drive_service, folder_name)
    home_folder_id = create_folder(drive_service, "home", parent_folder_id=friendlens_folder_id)
    feed_folder_id = create_folder(drive_service, "feed", parent_folder_id=friendlens_folder_id)

    add_editor_permission(drive_service, friendlens_folder_id)

    # Load existing users' data
    users_data = load_users_data(users_json_path)

    # Fetch user's full name from the People API
    people_service = build("people", "v1", credentials=creds)
    global person_info
    person_info = people_service.people().get(resourceName="people/me", personFields="names").execute()
    person = people_service.people().get(resourceName="people/me", personFields='photos').execute()
    global pfp
    if 'photos' in person:
        pfp = person['photos'][0]['url']

    print(friendlens_folder_id, home_folder_id, feed_folder_id,user_email)
    name = person_info.get("names", [{}])[0].get("displayName", "Unknown")
    print(email)

    # Check if the user's data is already in the JSON file
    if user_email not in users_data:
        # If not, add the user's data
        add_user_data(users_data, user_email, friendlens_folder_id, home_folder_id, feed_folder_id, name)

        # Save the updated users' data to the JSON file
        save_users_data(users_json_path, users_data)
        print(f"User {user_email} added to the JSON file.")
    
    # Example image file upload to the home folder
    users_data = load_users_data(users_json_path)

        
            


def upload(users_json_path, path):
    try:
        global email, drive_service, friendlens_folder_id, home_folder_id, feed_folder_id, users_data, person_info, user_email, trained, name
        initialize()

        

        if path is not None and users_data[user_email]["training_status"] == "False":
            train_image_path = path
            train_image(train_image_path, user_email)
            users_data[user_email]["training_status"] = "True"
            save_users_data(users_json_path, users_data)
            trained = True

        if path is not None:
            image_file_path = path
            upload_image_to_home(drive_service, home_folder_id, image_file_path)
            # Example usage
            known_face_encodings, known_face_names = load_known_faces_from_json("C:\\Users\\Cyril\\Desktop\\known_face_encodings.json")
            image_path_str = str(image_file_path)
            frame = cv2.imread(image_path_str)  # Replace with the path to your image
            detected_faces = set(detect_known_faces(frame, known_face_encodings))
            if user_email in detected_faces:
                detected_faces.remove(user_email)
            users_data = load_users_data(users_json_path)
            feed_folder_ids = []
            for email in detected_faces:
                if email in users_data:
                    feed_folder_id = users_data[email]["feed_folder_id"]
                    feed_folder_ids.append(feed_folder_id)
            
            print(detected_faces)
            print(feed_folder_ids)
            for feed_id in feed_folder_ids:
                upload_image_to_home(drive_service, feed_id, image_file_path)

    except HttpError as err:
        print(err)


def get_image_links(image_id):
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    results = drive_service.files().list(
        q=f"'{image_id}' in parents",
        fields="*",
        pageSize=1000
    ).execute()

    files = results.get('files', [])
    image_info_list = []
    for file in files:
        name = file.get('name', '')
        web_content_link = file.get('webContentLink', '').split('&')[0]
        created_time = file.get('createdTime', '')
        last_modifying_user = file.get('lastModifyingUser', {})
        email_address = last_modifying_user.get('emailAddress', '')
        display_name = last_modifying_user.get('displayName', '')

        # Check if the file has an image extension
        if any(name.lower().endswith(ext) for ext in image_extensions):
            # Extract user information from createdTime (assuming it contains user email)
            user_email = created_time.split("@")[0]  # Extract user email from createdTime (example assumption)
            user_info = users_data.get(user_email, {})

            image_info = {
                'name': name,
                'webContentLink': web_content_link,
                'user_name': user_info.get('name', 'Unknown'),
                'user_email': user_email,
                'last_modifying_user_email': email_address,
                'last_modifying_user_display_name': display_name
            }

            image_info_list.append(image_info)

    return image_info_list



global home_len, feed_len

@app.route('/', methods=['GET', 'POST'])
def index():
    global file_locations  # List to store file paths
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'files[]' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('index'))
        

        files = request.files.getlist('files[]')

        for file in files:
            # If the user does not select a file, the browser submits an empty file without a filename
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(url_for('index'))

            # Check if the file is allowed based on the file extension
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                flash('Invalid file extension', 'error')
                return redirect(url_for('index'))

            # Capture the file path without saving the file
            file_location = os.path.join("C:/Users/Cyril/Downloads/", file.filename)
            file_locations.append(file_location) 
            upload(users_json_path, path=file_location)
            flash('File successfully uploaded!', 'success')
    if users_data[user_email]["training_status"] == "False":
        flash("Click here to train your very first image!", 'success')
    images = []
    links = users_data[gemail]["home_folder_id"]
    images = get_image_links(links)
    link_list = [img['webContentLink'] for img in images]
    name_list = [img['last_modifying_user_display_name'] for img in images]
    global home_len
    home_len = len(link_list)
    print(name_list)
    return render_template('index.html', images=link_list, name=name, email=gemail, pfp=pfp, name_list=name_list)

# Feed page
@app.route('/feed')
def feed():
    images = []
    links = users_data[gemail]["feed_folder_id"]
    images = get_image_links(links)

    link_list = [img['webContentLink'] for img in images]
    name_list = [img['last_modifying_user_display_name'] for img in images]
    print(name_list)
    global feed_len
    feed_len = len(link_list)
    return render_template('feed.html', images=link_list, name=name, email=gemail, pfp=pfp, name_list=name_list)

@app.route('/settings')
def settings():
    global home_len, feed_len
    return render_template('settings.html', home_len=home_len, feed_len=feed_len)

if __name__ == "__main__":
    creds = authenticate(credentials_path)
    upload(users_json_path, path=None)
    app.run(debug=True, port=5050)