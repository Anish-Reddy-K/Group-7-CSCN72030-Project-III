# import os

# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

# def get_drive_service():
#     creds = Credentials.from_authorized_user_file(os.path.expanduser('C:/Users/Cyril/Desktop/FriendLens/client_secrets.json'))
#     return build('drive', 'v3', credentials=creds)

# def get_image_links(folder_id):
#     service = get_drive_service()
#     query = f"'{folder_id}' in parents and mimeType contains 'image/'"
#     results = service.files().list(q=query, fields="nextPageToken, files(id, name, webContentLink)").execute()
#     items = results.get('files', [])
#     links = []
#     for item in items:
#         link = item['webContentLink']
#         links.append(link)
#     return links

# folder_id = 'https://drive.google.com/file/d/10J0ZFzGWSoIfOVF6XN9VuyrATGsa7Ig7/view?usp=drive_link'
# links = get_image_links(folder_id)
# for link in links:
#     print(link)


def access_user_data(users_data, user_email):
    # Iterate through the list of dictionaries
    for user_entry in users_data:
        # Check if the user_email is a key in the current dictionary
        if user_email in user_entry:
            user_values = user_entry[user_email]
            print(f"User values for {user_email}: {user_values}")
            return user_values

    # If the user_email is not found in any dictionary
    print(f"User with email {user_email} not found.")
    return None

# Example Usage
users_data = [
    {
        "cyrilcomputer1@gmail.com": {
            "name": "Cyril Shaji",
            "friendlens_folder_id": "1vY-jL8MvSQmnVHigogtb0xvXN29KtCgV",
            "home_folder_id": "1xVahY6UchW3ey3qsv77U7xLCAmCgvmeP",
            "feed_folder_id": "1pkZHxGUf7or8y6TtRSJyrfSOtM7gTYU_",
            "training_status": "True"
        }
    },
    {
        "cyrilshaji7@gmail.com": {
            "name": "cyril shaji",
            "friendlens_folder_id": "1emO34bfXbtsN4aDQ9MLzJiDPw8BKHoqt",
            "home_folder_id": "1p3vOFFlrmkcWnRu78JlgdKgRfGFO59nU",
            "feed_folder_id": "1uV3je7MJUHDiOkTZ5ydzn7rEednugngN",
            "training_status": "True"
        }
    }
]

user_email_to_access = "cyrilcomputer1@gmail.com"

# Access user data using the Gmail address as an index
user_data = access_user_data(users_data, user_email_to_access)
