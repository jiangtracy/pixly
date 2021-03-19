# Pixly

- An image editing web app built with Python, Flask, Pillow, and AWS S3.

# Functionality

- Users can upload images from their laptops or mobile devices and edit their images. All the images will be saved to AWS S3 and available for public to view. 
- Under the picture tab, users can search image by title or photographer name.
- https://pixly.herokuapp.com/

# Run the app

- `git clone` this repo
-  (optional) `python3 -m venv venv`
- pip3 install requirements.txt
- one small change in the source file due to flask not aware of a werkzeug update therefore throwing an import error
  - go to `flask_uploads.py` in lib
  - comment out `from werkzeug import secure_filename, FileStorage`
  - replace with 
  `from werkzeug.datastructures import  FileStorage`
  `from werkzeug.datastructures import  FileStorage`
 - `flask run`
