from flask import Flask, request, redirect, jsonify, render_template
from flask_debugtoolbar import DebugToolbarExtension
from flask_caching import Cache


from PIL import Image, ImageFilter, ExifTags, ImageOps, ImageEnhance, ImageFile
from PIL.ExifTags import TAGS
from forms import UploadForm
from models import (db, connect_db, Picture)
from werkzeug.utils import secure_filename

import botocore
import boto3
import os


ACCESS_KEY_ID = os.environ["ACCESS_KEY_ID"]
SECRET_KEY = os.environ["SECRET_KEY"]
BUCKET = os.environ["BUCKET"]
IMAGE_URL = os.environ["IMAGE_URL"]

config = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}

app = Flask(__name__, static_folder="./static")

# tell Flask to use the above defined config
app.config.from_mapping(config)
cache = Cache(app)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///pixly'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
# debug = DebugToolbarExtension(app)

connect_db(app)
db.create_all()

ImageFile.LOAD_TRUNCATED_IMAGES = True

client = boto3.client('s3',
                      aws_access_key_id=ACCESS_KEY_ID,
                      aws_secret_access_key=SECRET_KEY)

####################### Routes ###########################


@app.route("/", methods=["GET"])
def display_homepage():
    """ Route home page """

    return render_template("homepage.html")


@app.route("/images", methods=["GET"])
def display_all_image():
    """ Route for displaying all images """

    # search function
    if request.args.get("search"):

        pictures = Picture.query.filter(db.or_(
            Picture.caption.ilike(
                f'%{request.args.get("search")}%'), Picture.photographer.ilike(
                f'%{request.args.get("search")}%'))).all()
    
    else:
        pictures = Picture.query.all()

    # format the url and append to an array
    picturesUrl = []
    for picture in pictures:
        picturesUrl.append({"url": f'{IMAGE_URL}{picture.id}',
                            "id": f'{picture.id}',
                            "photog": f'{picture.photographer}',
                            "caption": f'{picture.caption}'})

    return render_template("all_pictures.html", pictures=picturesUrl)


@app.route("/images/add", methods=["GET", "POST"])
def add_image():
    """ Route for uploading a new image """

    form = UploadForm()

    if form.validate_on_submit():
        f = form.photo.data
        filename = secure_filename(f.filename)

        f.save(os.path.join(filename))

        image = Image.open(f'{filename}')

        # Only images taken by phone or camera will have exif info,
        # others would throw an AttricuteError because exif doesn't exist.
        # The try/except block catches the AttributeError
        # therefore all picture type can be uploaded.

        try:
            exif = {}
            for tag, value in image._getexif().items():
                if tag in TAGS:
                    exif[TAGS[tag]] = value

            picture = Picture(
                photographer=form.photographer.data,
                caption=form.caption.data,
                date_time=exif.get('DateTime'),
                camera_make=exif.get('Make'),
                camera_model=exif.get('Model'),
                iso=exif.get('ISOSpeedRatings'),
                flash=exif.get('Flash'),
                pic_width=exif.get('ExifImageWidth'),
                pic_height=exif.get('ExifImageHeight'),
                image_url=IMAGE_URL,
                file_name=filename
            )
        except AttributeError:
            picture = Picture(
                photographer=form.photographer.data,
                caption=form.caption.data,
                date_time=None,
                camera_make=None,
                camera_model=None,
                iso=None,
                flash=None,
                pic_width=None,
                pic_height=None,
                image_url=IMAGE_URL,
                file_name=filename
            )

        db.session.add(picture)
        db.session.commit()

        # upload the image to aws
        upload_file_bucket = BUCKET
        upload_file_key = picture.id
        client.upload_file(filename,
                           upload_file_bucket,
                           str(upload_file_key),
                           ExtraArgs={'ACL': 'public-read'})
        os.remove(filename)
        return redirect(f'/images/{picture.id}')
    else:
        return render_template("add_picture.html", form=form)


@app.route("/images/<int:id>", methods=["GET"])
def edit_image(id):
    """ Route for the edit page """
    return render_template('edit_picture.html', url=f'{IMAGE_URL}{id}', id=id)

@app.route("/images/<int:id>/<edit>", methods=["GET", "POST"])
def edit_image_edit(id, edit):
    """ Route for specific image edit. """

    filename = f'{id}.png'
    s3 = boto3.resource('s3',
                        aws_access_key_id=ACCESS_KEY_ID,
                        aws_secret_access_key=SECRET_KEY,
                        )

    # download the file from AWS S3
    try:
        s3.Bucket(BUCKET).download_file(str(id), str(id))

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
    os.rename(str(id), filename)
    image = Image.open(filename)

    # code below takes care of all the edits
    if edit == "grayscale":
        newImage = ImageOps.grayscale(image)

    if edit == "left":
        
        newImage = image.rotate(90, expand=True)

    if edit == "right":
        newImage = image.rotate(-90, expand=True)

    if edit == "posterize":
        newImage = ImageOps.posterize(image, 5)

    if edit == "emboss":
        newImage = image.filter(ImageFilter.EMBOSS)

    if edit == "blur":
        newImage = image.filter(ImageFilter.GaussianBlur(radius=4))

    if edit == "color":
        enhance = ImageEnhance.Color(image)
        newImage = enhance.enhance(1.5)

    if edit == "contrast":
        enhance = ImageEnhance.Contrast(image)
        newImage = enhance.enhance(1.5)

    if edit == "brightness":
        enhance = ImageEnhance.Brightness(image)
        newImage = enhance.enhance(1.5)

    newImage.save(os.path.join(filename))
    upload_file_bucket = BUCKET
    upload_file_key = str(id)

    # save the edits and update photo to aws s3 bucket
    client.upload_file(
        filename,
        upload_file_bucket,
        upload_file_key,
        ExtraArgs={'ACL': 'public-read'}
    )

    cache.clear()
    os.remove(filename)

    cache.clear()
    return redirect(f'/images/{id}')
