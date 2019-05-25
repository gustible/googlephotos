# googlephotos bulk uploader
Bulk uploads photos from a local folder to Google Photos. Uses a specified album to categorise the photos.
Progress of upload is stored locally.
Meant for uploading large numbers of files - personally used it to upload more than 60,000 photos 
to Google Drive.

---
## Deployment
This is a command line tool.
Download and create a virtual environment:
- mkvirtualenv -p python3 googlephotos (_or any other name_)
- pip install -r requirements.txt
- python ./gp.py -?


## Configuration
To avoid having to re-authenticate with Google all the time, the application expects credentials to be
available in a local file. The default file name is _credentials.json_

The method for obtaining the credentials are described here - https://www.syncwithtech.org/authorizing-google-apis/

Folders (image directory) are set to default values but can be overridden on the command line

## Usage
usage: gp.py [-h] [-i IMAGEDIR] [-a ALBUMNAME] [-x] [-c] [-u] [-v] [-m MAXSIZE]

 -h, --help            show this help message and exit
 
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
 
To upload all JPG files in the default image folder that are small 
than 10MB, and with verbose output, use:
 `python ./gp.py -u -v -m 10`

To update the database of all files that must be uploaded, showing verbose 
messages use: `python ./gp.py -c -v`

__Notes:__
- The script will ONLY upload files with a JPG extension (it is not case sensitive).
- The SQLite database is called GDriveimages, and is created in the folder where the script is run


---

