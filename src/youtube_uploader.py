import os
import logging
import subprocess
import pickle

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

def create_video_from_image_and_audio(image_path: str, audio_path: str, output_video_path: str) -> None:
    """
    Creates a video by combining a static image with an audio file using ffmpeg.
    
    The image will be displayed throughout the video while the audio plays in the background.
    """
    command = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_video_path
    ]
    try:
        subprocess.run(command, check=True)
        logger.info(f"Video successfully created at {output_video_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating video: {e}")
        raise

def upload_video_to_youtube(
    video_path: str, 
    title: str, 
    description: str, 
    tags: list, 
    category_id: str = "22", 
    privacy_status: str = "public"
) -> str:
    """
    Uploads a video to YouTube using the YouTube Data API.
    
    Requires proper OAuth2 credentials. The function returns the uploaded video's ID.
    """
    # Determine the directory of the current script to ensure correct file paths when running from cron.
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # OAuth2 configuration with absolute paths
    CLIENT_SECRETS_FILE = os.path.join(base_dir, "client_secrets.json")
    CREDENTIALS_PICKLE_FILE = os.path.join(base_dir, "youtube_credentials.pickle")
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    creds = None
    if os.path.exists(CREDENTIALS_PICKLE_FILE):
        with open(CREDENTIALS_PICKLE_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(CREDENTIALS_PICKLE_FILE, "wb") as token:
            pickle.dump(creds, token)

    youtube = build("youtube", "v3", credentials=creds)

    body = dict(
        snippet=dict(
            title=title,
            description=description,
            tags=tags,
            categoryId=category_id
        ),
        status=dict(
            privacyStatus=privacy_status
        )
    )

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"Uploading video: {int(status.progress() * 100)}% complete")
    logger.info("Video upload complete!")
    return response.get("id")
