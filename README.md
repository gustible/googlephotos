# googlephotos bulk uploader
Bulk uploads photos from a local folder to Google Photos. Uses a specified album to categorise the photos.
Progress of upload is stored locally.
Meant for uploading large numbers of files - personally used it to upload more than 60,000 photos 
to Google Drive.

---
## Deployment
This is a command line tool.
Download and create a virtual environment:

    mkvirtualenv -p python3 googlephotos (_or any other name_)
    pip install -r requirements.txt
    python ./gp.py -?
    
*Note: On on Windows use Python 3.8 version max to avoid legacy-install-failure error while trying to install package `cffi`*

## Configuration
To avoid having to re-authenticate with Google all the time, the application expects credentials to be
available in a local file. The default file name is _credentials.json_

The method for obtaining the credentials are described here - https://www.syncwithtech.org/authorizing-google-apis/
Run the script with option -gc to obtain new OAuth credentials via the command line.

Folders (image directory) are set to default values but can be overridden on the command line.
The root folder for media (IMAGEDIR) is NOT saved in the database, but only read from the command line. This means that
if you want to change the root folder you can do so via configuration only. Folder below the root ARE stored in the 
database. For example: if the root folder is "PICTURES", and you add an image with path "PICTURES/October/100.JPG" then
the image's local path will be stored as "October/100.JPG" in the database. The combination of IMAGEDIR and localpath is
used to locate files that will be uploaded.

## Credentials
Follow those steps to download the credentials required:

1. Create project on google cloud
2. Enable Google Photos Library API for this project: go to https://developers.google.com/photos/library/guides/get-started then click button "Enable the Google Photos Library API"
3. For "Configure OAuth client" screen select ~~"Installed Application"~~ "Desktop app"
4. Download client configuration and place this file `credentials.json` at project root (optional: store client_id and client_secret somewhere safe)
5. Run `python ./gp.py --get_credentials`, open link in web browser then paste Authorization code back in console

## Usage
usage: gp.py [-h] [-i IMAGEDIR] [-a ALBUMNAME] [-x] [-c] [-u] [-v] [-m MAXSIZE]

 -h, --help            show this help message and exit

  -gc, --get_credentials
                        Obtains new OAuth credentials and saves them. Other
                        parameters are ignored.

  -i IMAGEDIR, --imagedir IMAGEDIR 
                        Specify root image directory
                        
  -a ALBUMNAME, --albumname ALBUMNAME
                        Specify Google Photos album
                        
  -x, --dontincrementalbum
                        Auto increment album name for large albums
                        
  -c, --check           Walk local folder and update database of files, mark
                        new files for upload. Files are NOT uploaded unless -u
                        is True. The folder is first walked, then uploaded.
                        
  -u, --upload          Upload images to Google Drive
  
  -v, --verbose         Provide verbose messaging
  
  -m MAXSIZE, --maxsize MAXSIZE
                        Max file size to upload (MB), default=-1 (no limit)

__Example:__

Basic usage patter is as follows:
- Run the script to create a list of all files to be uploaded (/.gp.py -v)
- Run the script to upload each file in the database (.gp.py -u)
 
To upload all JPG files in the default image folder that are small 
than 10MB, and with verbose output, use:

    python ./gp.py -u -v -m 10

To update the database of all files that must be uploaded, showing verbose 
messages use: 

    python ./gp.py -c -v


__Notes:__
- The script will ONLY upload files with a JPG extension (it is not case sensitive).
- The script can easily be modified to accommodate other files, the JPG limitation is just a personal requirement
- The SQLite database is called GDriveimages, and is created in the folder where the script is located


---

