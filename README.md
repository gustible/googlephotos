# googlephotos bulk uploader
Bulk uploads photos from a local folder to Google Photos. Uses a specified album to categorise the photos.
Progress of upload is stored locally.
Meant for uploading large numbers of files - personally used it to upload more than 60,000 photos.
---
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
---
