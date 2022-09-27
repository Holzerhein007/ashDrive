import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tabulate import tabulate

import io

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/drive.file']
global current_folder

def get_gdrive_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)


def search(service, query):
    # search for the file
    global result
    #  for the easy file and folder navigating system
    global numb
    numb = 0
    result = []
    page_token = None
    while True:
        response = service.files().list(q=query,
                                        spaces="drive",
                                        fields="nextPageToken, files(id, name, mimeType, parents)",
                                        pageToken=page_token).execute()
        # iterate over filtered files
        for file in response.get("files", []):
            result.append((file["id"], file["name"], file["mimeType"], file["parents"], numb))
            numb += 1
        page_token = response.get('nextPageToken', None)
        if not page_token:
            # no more files
            break
    
    return result


def main():
    global previous_folder
    global current_folder
    current_folder="root"
    previous_folder = []
    # filter to text files
    filetype = "application/vnd.google-apps.folder"
    # authenticate Google Drive API
    service = get_gdrive_service()
    # search for files that has type of text/plain
    copy = str(current_folder)        
    previous_folder.append(copy.strip("]'["))
    #search_result = search(service, query=f"mimeType='{filetype}'")
    search_result = search(service, query=f"parents='{current_folder}' and trashed = false")
    current_folder = result[0][3]
    # convert to table to print well
    table = tabulate(search_result, headers=["ID", "Name", "Type", "Parents", "File Number"])
    print(table)
    nav()

#navigate google drive folders
def nav():
    going = True
    global current_folder
    global previous_folder
    global to_folder
    
    while going == True:
        #get the folder id
        navigate = input("Select folder number: ")
                
        if navigate=="q" or navigate=="quit":
            going=False
            break
        
        elif navigate=="back":
            #initiate Google Drive API
            service = get_gdrive_service()
            #search for the last folder stored in the previous_folder list
            search_result = search(service, query=f"parents='{previous_folder[-1]}' and trashed = false")
            current_folder = previous_folder[-1]
            #remove the last folder from the previous_folder list as it is now the current folder
            previous_folder.pop(-1)
            #print the files in a table list
            table = tabulate(search_result, headers=["ID", "Name", "Type", "Parents", "File Number"])
            print(table)
            nav()
        
        elif navigate=="mkdir":
            create_folder()
        
        elif navigate=="root":
            navigate_root()
            
        elif navigate=="download":
            f_id = int(input("Enter file number: "))
            global f_name
            f_name = result[f_id][1]
            download_file(real_file_id=result[f_id][0])
            nav()
        
        elif int(navigate) <= result[-1][4]:
            to_folder = result[int(navigate)][0]
            copy = str(current_folder)
            previous_folder.append(copy.strip("]'["))
            service = get_gdrive_service()
            search_result = search(service, query=f"parents='{to_folder}' and trashed = false")
            current_folder = str(result[0][3])
            current_folder = current_folder.strip("]'[")
            table = tabulate(search_result, headers=["ID", "Name", "Type", "Parents", "File Number"])
            print(table)
            nav()
        
        else:
            nav()
            
def navigate_root():
    # authenticate Google Drive API
    service = get_gdrive_service()
    #get search results for the My Drive root directory
    search_result = search(service, query=f"parents='root' and trashed = false")
    #display the search results in a table
    table = tabulate(search_result, headers=["ID", "Name", "Type", "Parents", "File Number"])
    print(table)
    nav()

def download_file(real_file_id):
    """Downloads a file
    Args:
        real_file_id: ID of the file to download
    Returns : IO object with location.

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    #creds= None
    #get_gdrive_service()

    try:
        # create drive api client
        #service = build('drive', 'v3', credentials=creds)
        service = get_gdrive_service()
        file_id = real_file_id

        # pylint: disable=maybe-no-member
        request = service.files().get_media(fileId=file_id)
        file = io.FileIO(f_name, 'wb')
        
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(F'Download {int(status.progress() * 100)}.')
        file.close()

    except HttpError as error:
        print(F'An error occurred: {error}')
        file = None

    nav()

def create_folder():
    """
    Creates a folder and upload a file to it
    """
    global current_folder
    # authenticate account
    service = get_gdrive_service()
    # 'TV Shows' folder id
    #tvshows = "1JWG5hS05nB8J924oUxL2ssLauoCnYXTw"
    folder_name = input("Enter new folder name: ")
    # folder details we want to make    
    new_folder = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [current_folder]
    }
    # create the folder
    file = service.files().create(body=new_folder, fields="id").execute()
    # get the folder id
    new_folder_id = file.get("id")
    print("Folder ID:", new_folder_id)
    current_folder = str(result[0][3])
    current_folder = current_folder.strip("]'[")
    search_result = search(service, query=f"parents='{current_folder}' and trashed = false")
    current_folder = str(result[0][3])
    current_folder = current_folder.strip("]'[")
    table = tabulate(search_result, headers=["ID", "Name", "Type", "Parents", "File Number"])
    print(table)
    nav()
    

if __name__ == '__main__':
    
    
    navigate=""
    main()