#!/usr/bin/python3.6

import os, sqlite3, json, sys, time

from datetime import datetime
from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import argparse


SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary',
    'https://www.googleapis.com/auth/photoslibrary.sharing'
]
CLIENT_SECRET_FILE = 'credentials.json'
API_SERVICE_NAME = 'photoslibrary.googleapis.com'
API_VERSION = 'v1'


class CriticalException(Exception):
    pass


class IgnoreFileException(Exception):
    pass


def print_message(message):
    if args.verbose:
        print(message)


def create_database_structure():
    """
    Sets up the database structure only if the tables do not exist
    :return: None
    """
    sql = "create table if not exists imagelist(localpath, google_id, dateuploaded)"
    connsql.execute(sql)
    sql = "create table if not exists albumname(album_name, increment)"
    connsql.execute(sql)
    sql = "create table if not exists token(token, refresh_token, token_uri, " \
          "client_id, client_secret, datesaved)"
    connsql.execute(sql)


def create_album(album_name, authed_session):
    """
    Creates the album in Google Photos
    :param album_name: Name of the album to create
    :param authed_session: AuthorizedSession object
    :return: album_id - the Google ID for the album
    """
    url = 'https://photoslibrary.googleapis.com/v1/albums'
    payload = {
        "album": {
            "title": album_name
        }
    }
    try:
        response = authed_session.post(url, data=json.dumps(payload))
    except Exception as e:
        raise CriticalException(e)
    if response.status_code != 200:
        raise CriticalException("Could not create album:{}".format(response.text))
    return json.loads(response.text)["id"]


def get_active_album_name(increment=0):
    """
    Returns the name of the current album, optionally with an increment. This is used if the Google Album size limit is reached.
    The album name is automatically incremented by 1 every time the size is exceeded.
    The active album name is the album name specified in the parameters + _{increment}.
    Note - only one record is expected in this table. Ever.
    :return: albumname and google_id for the album
    """
    c = connsql.cursor()
    c.execute('select album_name, increment, google_id from albumname')
    album = c.fetchone()

    if album is None:
        return args.albumname, None
    if album[1] > 0:
        return args.albumname + "_{}".format(album[1]+increment), album[2]
    else:
        return args.albumname, album[2]


def increment_album_name(authed_session):
    """
    Adds an increment to the album name if the count of items exceed 20000.
    Creates the new album on Google Photos
    :param authed_session:
    :return: album_id, album_name
    """

    album_name, album_id = get_active_album_name(1)
    album_id = create_album(album_name, authed_session)
    try:
        c = connsql.cursor()
        sql = "UPDATE albumname set increment = increment+1, google_id = '{}'".format(album_id)
        c.execute(sql)
        connsql.commit()
    except Exception as e:
        raise CriticalException(e)
    print_message("Incremented album - new album is:{}".format(album_name))
    return album_id, album_name


def create_album_name(authed_session):
    """
    Creates a backup album - this may either be at initialisation of the process or when the album name
    is "incremented" when the media count exceeds 20000 (the limit imposed by Google)
    :param authed_session:
    :return: album_id, album_name
    """

    album_name, album_id = get_active_album_name()
    print_message("Using album:{}".format(album_name))

    if not album_id:
        # Album was not found, create it.
        album_id = create_album(album_name, authed_session)
        try:
            c = connsql.cursor()
            sql_parameters = (args.albumname, 0, album_id)
            c.execute("INSERT INTO albumname (album_name, increment, google_id) VALUES (?,?,?)", sql_parameters)
            connsql.commit()
        except Exception as e:
            raise CriticalException(e)
    return album_id, album_name


def set_file_status(rowid, google_id):
    c = connsql.cursor()
    sql_parameters = (google_id, datetime.now().isoformat(), rowid)
    c.execute("UPDATE imagelist set google_id = ?, dateuploaded = ?  where rowid = ?", sql_parameters)
    connsql.commit()


def store_file_details(localpath):
    """
    Simply store the file's path in the database - GoogleID is defaulted to None
    Performs a check to see if the file is already in the database, if it is, do not add it again
    :param localpath: full local path to the file
    :param google_id: the google ID of the file if available
    :param uploaded: TRUE if it has been successfully uploaded
    :return: None
    """
    exists = False
    c = connsql.cursor()
    parms = (localpath,)
    c.execute('select rowid from imagelist where localpath = ?;', parms)
    exists = c.fetchone() is not None

    if not exists:  # Do not add to database if google ID exists or filepath exists
        print_message("Adding:{0}".format(localpath))
        sql_parameters = (localpath, None, None)
        c.execute("INSERT INTO imagelist (localpath, google_id, dateuploaded) VALUES (?,?,?)", sql_parameters)
        connsql.commit()
        return
    print_message("File already in list - name:{}".format(localpath))


def check_files(local_dir):
    """
    Walks the local directory and adds files which are not registered in the database. Does NOT upload
    files. Only check for JPG (jpg) files.
    TODO: Add command line argument to check for other types
    :param local_dir: The local folder to check for files which have not been uploaded
    :return: None
    """
    print_message("::Walking local folder")
    for (dirpath, dirnames, filenames) in os.walk(local_dir):
        for f in filenames:
            ext = os.path.splitext(f)[1].upper()
            if ext in [".JPG"]:
                filepath = os.path.join(dirpath, f)
                store_file_details(filepath)


def get_authed_session():
    """
    Returns an AuthorizedSession object based on stored credentials
    :return: sAuthorizedSession
    """
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    credentials = read_credentials()
    if credentials is None:
        credentials = get_oauth_credentials()
        store_token(credentials)
    return AuthorizedSession(credentials)


def upload_file(authed_session, album_id, file_name):
    """

    :param authed_session:
    :param album_id:
    :param file_name:
    :return: True if saved OK, new item id, and album id (which may have been modified)
    """

    # Upload the file
    f = open(file_name,'rb').read()
    if len(f) == 0:
        raise IgnoreFileException("This file is zero length:{}".format(file_name))
    headers = {
        'Content-type': 'application/octet-stream',
        'X-Goog-Upload-File-Name': os.path.basename(file_name),
        'X-Goog-Upload-Protocol': 'raw'
    }
    url = "https://photoslibrary.googleapis.com/v1/uploads"
    response = authed_session.post(url, headers=headers, data=f)
    if response.status_code != 200:
        raise IgnoreFileException("Upload failed:{}".format(response.text))
    # Add it to an album
    url = "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate"
    upload_token = str(response.content, 'utf-8')
    new_media_item = {
        "description": os.path.basename(file_name),
        "simpleMediaItem": {
            "uploadToken": upload_token
        }
    }
    payload = {
        "albumId": album_id,
        "newMediaItems": [new_media_item]
    }
    response = authed_session.post(url, data=json.dumps(payload))
    new_media_item_results = json.loads(response.content)['newMediaItemResults'][0]

    if new_media_item_results["status"]["message"] == "OK":
        id = new_media_item_results["mediaItem"]["id"]
    elif new_media_item_results["status"]["code"] == 8: #8 means ERR_PHOTO_PER_ALBUM_LIMIT
        if args.dontincrementalbum:
            return
        album_id = increment_album_name(authed_session)
    else:
        id = None
        print_message("Upload Failed: {}".format(new_media_item_results["status"]))
    return new_media_item_results["status"]["message"] =="OK", id, album_id


def upload_files(authed_session, album_id, album_name):
    """
    Uploads all files in the database that are marked as having no Google ID
    :return:
    """
    c = connsql.cursor()
    c.execute("SELECT rowid,* from imagelist where google_id is null")
    l = c.fetchall()

    count = 0
    print("{0} Files to be uploaded\n".format(len(l)))
    print("::Uploading files\n")
    for row in l:
        try:
            smb = os.path.getsize(row[1])
            if (args.maxsize != -1) and (smb // 1048576) > args.maxsize:
                print_message("Skipping large file: {0} - size:{1} (max={2}MB)".format(row[1], smb // 1048576, args.maxsize))
            else:
                print_message("uploading:{0}, {1} to \'{2}\'".format(row[0], row[1], album_name))
                success, id, album_id = upload_file(authed_session, album_id, row[1])
                if success:
                    set_file_status(row[0], id)
                    count += 1
                    print_message("({0}/{1}) uploaded:: {2}".format(count, len(l), row[1]))
                else:
                    print_message("Failed to upload {}".format(row[1]))
        except IgnoreFileException as e:
            print("Ignoring file {0} with error: \'{1}\'".format(row[1], e))

        except OSError:
            print("Skipping: OSError ignored for file: {0}").format(row[1])


# region Token Management
def get_oauth_credentials():
    """
    Obtain an access token using the install app flow.
    Reads the client secret from a local file
    :return: Credentials object
    """
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    credentials = flow.run_console()
    return credentials




def store_token(credentials):
    """
    Store credentials. Will only ever store a single row.
    :param credentials: credentials including access token to store
    :return: -
    """
    c = connsql.cursor()

    print_message("Storing token:{0}".format(credentials.token))
    c.execute("DELETE FROM token")
    sql_parameters = (credentials.token, credentials.refresh_token,
                      credentials.token_uri, credentials.client_id,
                      credentials.client_secret, datetime.now().isoformat())
    c.execute("INSERT INTO token (token, refresh_token, token_uri, " \
              "client_id, client_secret, datesaved) VALUES (?,?,?,?,?,?)", sql_parameters)
    connsql.commit()


def read_credentials():
    """
    Read stored credentials from the database
    See: https://www.syncwithtech.org/authorizing-google-apis/
    :return: Credentials object or None
    """
    c = connsql.cursor()
    c.execute("SELECT * FROM token")
    l = c.fetchone()
    if l is None:
        return None
    token = l[0]
    refresh_token = l[1]
    token_uri = l[2]
    client_id = l[3]
    client_secret = l[4]
    credentials = Credentials(token=token, refresh_token=refresh_token,
                              token_uri=token_uri, client_id=client_id,
                              client_secret=client_secret, scopes=SCOPES)
    return credentials
# endregion Token Management


def main():

    if args.check:
        check_files(args.imagedir)

    if args.upload:
        create_database_structure()
        authed_session = get_authed_session()
        album_id, album_name = create_album_name(authed_session)

        rcount = 0
        while True:
            try:
                upload_files(authed_session, album_id, album_name)
            except CriticalException:
                print("Critical Exception occurred: {0}".format(sys.exc_info()[1]))
                print(">>> Sorry - that was a critical error. Please sort it out and try again")
                break
            except Exception:
                # Simple retry - MAY resolve transient connectivity issue.
                rcount += 1
                print("Exception occurred: {0}".format(sys.exc_info()[1]))
                print ("Retry #{0} of 10  in {1} second(s)".format(rcount, rcount*2))
                time.sleep(rcount*2)
                if rcount > 9:
                    print(">>> Sorry - it is not working. Check exceptions and restart manually")
                    raise
                else:
                    continue
            break


# region Command line options

parser = argparse.ArgumentParser(description="A collection of utilities for C2S")

parser.add_argument("-i", "--imagedir", default="/media/jacques/FILESTORE/Pictures", help="Specify root image directory")
parser.add_argument("-a", "--albumname", default="Backup from Local", help="Specify Google Photos album")
parser.add_argument("-x", "--dontincrementalbum", action="store_false", help="Auto increment album name for large albums")
parser.add_argument("-c", "--check", action="store_true",
                    help="Walk local folder and update database of files, mark new files for upload. \
                       Files are NOT uploaded unless -u is True. The folder is first walked, then uploaded.")
parser.add_argument("-u", "--upload", action="store_true", help="Upload images to Google Drive")
parser.add_argument("-v", "--verbose", action="store_true", help="Provide verbose messaging")
parser.add_argument("-m", "--maxsize", type=int, default=-1,
                    help="Max file size to upload (MB), default=-1 (no limit)")

args = parser.parse_args()

# endregion

if __name__ == '__main__':
    print("\nRunning with options:")
    print("Imagedir             :{}".format(args.imagedir))
    print("Album Name           :{}".format(args.albumname))
    print("Increment Album      :{}".format(args.dontincrementalbum))
    print("Upload               :{}".format(args.upload))
    print("Check                :{}".format(args.check))
    print("MaxSize (MB)         :{}".format(args.maxsize))
    print("Verbose              :{}".format(args.verbose))

    try:
        connsql = sqlite3.connect('/home/jacques/workspace/googlephotos/GDriveimages')
        main()

    except Exception:
        raise
    finally:
        connsql.close()
        print("\n::Done::")
