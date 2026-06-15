from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from mcp.server.fastmcp import FastMCP
from googleapiclient.http import MediaIoBaseDownload
import os.path
import io

SCOPES = ['https://www.googleapis.com/auth/drive']

mcp = FastMCP("drive-server")


# Creates an authenticated Google Drive service using OAuth2.
# Refreshes or creates token.json automatically when needed.
def get_drive_service():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build("drive", "v3", credentials=creds)
    return service


@mcp.tool()
# MCP tool: find a folder by name and return all files inside it.
def list_files_in_folder(folder_name: str) -> list[dict]:
    """Returns a list of files inside a Google Drive folder by folder name.
    Each file is a dict with 'id' and 'name'. Use this when the user wants
    to see what files are in a folder (e.g. listing job descriptions or
    processed resumes)."""
    service = get_drive_service()
    # Search for the folder itself.
    q1 = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
    folder_results = (service.files().list(q=q1, fields="files(id, name)")
                      .execute())

    if not folder_results['files']:
        raise ValueError(f"Folder '{folder_name}' not found")

    folder_id = folder_results['files'][0]['id']
    # Search for files whose parent is the target folder.
    q2 = f"'{folder_id}' in parents and trashed=false"
    file_results = (service.files().list(q=q2, fields="files(id, name)")
                    .execute())
    return file_results['files']


@mcp.tool()
# MCP tool: download a text file from Google Drive by file ID.
def read_drive_file(file_id: str) -> str:
    """Downloads the text contents of a Drive file by its ID (you get the file ID from list_files_in_folder).
    Call it when you need to read a specific file (for example, a resume or job description)."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    # Download file in chunks until the transfer is complete.
    while done is False:
        status, done = downloader.next_chunk()
    return file.getvalue().decode('utf-8')


@mcp.tool()
# MCP tool: create a new text file in a Drive folder.
def upload_file_to_folder(folder_name: str, filename: str, content: str) -> str:
    """Creates a new text file in the specified Drive folder (folder name, new file name, contents).
    Call it whenever you want to save the result (for example, a tailored resume in the tailored folder)."""
    service = get_drive_service()
    q3 = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
    folder_results = ((service.files().list(q=q3, fields="files(id, name)"))
                      .execute())

    if not folder_results['files']:
        raise ValueError(f"Folder '{folder_name}' not found")
    folder_id = folder_results['files'][0]['id']
    # Convert string content into an in-memory file object for upload.
    content_bytes = content.encode('utf-8')
    buffer = io.BytesIO(content_bytes)
    media = MediaIoBaseUpload(buffer, mimetype='text/plain')
    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    result = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    return result['id']


if __name__ == "__main__":
    mcp.run()
