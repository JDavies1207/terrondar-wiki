import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Constants
FOLDER_ID = '1rd9vQDchQaCPp60Mc9C_MEmj4v8QZ8ZJ'  # Your Google Drive vault folder ID
TARGET_DIR = 'docs'  # Where to put files in your repo

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate():
    creds_json = os.environ.get('GDRIVE_SERVICE_ACCOUNT')
    if not creds_json:
        raise Exception("Missing GDRIVE_SERVICE_ACCOUNT environment variable")
    creds_info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return creds

def list_files(service, folder_id):
    """List all files and folders inside a Google Drive folder"""
    query = f"'{folder_id}' in parents and trashed = false"
    results = []
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType)',
            pageToken=page_token
        ).execute()
        results.extend(response.get('files', []))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return results

def download_file(service, file_id, filepath):
    """Download a single file by ID to the given local filepath"""
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(filepath, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

def sync_folder(service, folder_id, target_path):
    """Recursively sync files and folders from Drive to local"""
    if not os.path.exists(target_path):
        os.makedirs(target_path)
    items = list_files(service, folder_id)
    for item in items:
        name = item['name']
        mime = item['mimeType']
        file_id = item['id']
        if mime == 'application/vnd.google-apps.folder':
            # Recurse into folder
            sync_folder(service, file_id, os.path.join(target_path, name))
        else:
            # Download only Markdown files and images (optional: add more extensions)
            if name.lower().endswith(('.md', '.png', '.jpg', '.jpeg', '.gif')):
                print(f"Downloading {name} to {target_path}")
                download_file(service, file_id, os.path.join(target_path, name))

def clean_target_dir(path):
    """Remove all files/folders inside the target docs folder to prevent stale files"""
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))

def main():
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    # Clean docs folder first
    clean_target_dir(TARGET_DIR)

    # Sync files recursively
    sync_folder(service, FOLDER_ID, TARGET_DIR)

if __name__ == "__main__":
    main()
