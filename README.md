# Run the app

# One change in the source file due to flask not aware of a werkzeug update therefore throwing an import error
- go to `flask_uploads.py` in lib
- comment out `from werkzeug import secure_filename, FileStorage`
- replace with 
`from werkzeug.datastructures import  FileStorage`
`from werkzeug.datastructures import  FileStorage`