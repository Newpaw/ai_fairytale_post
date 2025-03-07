import os
import base64
import uuid
import requests

from ai_content_generator import generate_unique_animal_content
from wordpress_client import WordpressClient
from logger import logger
from elevenlabs_client import generate_audio
from helper import strip_html_tags, combine_content, cleanup_file, cleanup_directory

# Import functions from the YouTube uploader module
from youtube_uploader import create_video_from_image_and_audio, upload_video_to_youtube

def post_ai_article():
    try:
        title, story, image_path = generate_unique_animal_content()
        logger.debug(f"Title: {title}, story (first 100 chars): {story[:100]}, image path: {image_path}")
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return

    client = WordpressClient()

    # 1. Upload the featured image (thumbnail) to WordPress
    try:
        with open(image_path, 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read())
            image_name = uuid.uuid4().hex + ".png"
            image_attachment_id = client.upload_image(base64_image, image_name)
            image_url = client.get_media_url(image_attachment_id)
            logger.info(f"Image uploaded, URL: {image_url}")
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return

    # 2. Clean the story text and generate audio from it
    story_clean = strip_html_tags(story)
    try:
        audio_file_path = generate_audio(story_clean)
        logger.info(f"Audio generated: {audio_file_path}")
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        return

    # 3. Upload the audio file and get its URL for embedding in the WordPress post
    try:
        with open(audio_file_path, 'rb') as audio_file:
            base64_audio = base64.b64encode(audio_file.read())
            audio_filename = uuid.uuid4().hex + ".mp3"
            audio_attachment_id = client.upload_audio(base64_audio, audio_filename)
            audio_url = client.get_media_url(audio_attachment_id)
            audio_html = f'[audio src="{audio_url}"]'
            logger.info(f"Audio uploaded, URL: {audio_url}")
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        audio_html = ""

    # 4. Combine story and audio player HTML to form the post content
    combined_content = combine_content(story, audio_html)

    # 5. Create the post on WordPress with the featured image set
    try:
        data = {
            "title": title,
            "content": combined_content,
            "status": "publish",
            "categories": [17],  # adjust category ID as needed
            "featured_media": image_attachment_id
        }
        post_url = f"{client.base_url}/wp-json/wp/v2/posts"
        response = requests.post(post_url, auth=client.auth, json=data)
        if response.status_code == 201:
            logger.info(f"Post published on WordPress, title: {title}")
        else:
            logger.error(f"Error creating WordPress post: {response.status_code}")
            logger.error(response.text)
            return
    except Exception as e:
        logger.error(f"Error publishing WordPress post: {e}")
        return

    # 6. Create a video from the image and audio for YouTube upload
    video_dir = os.path.join(os.getcwd(), "videos")
    os.makedirs(video_dir, exist_ok=True)
    video_path = os.path.join(video_dir, f"{uuid.uuid4().hex}.mp4")
    try:
        create_video_from_image_and_audio(image_path, audio_file_path, video_path)
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        video_path = None

    # 7. Upload the video to YouTube (if the video was successfully created)
    if video_path:
        try:
            youtube_video_id = upload_video_to_youtube(
                video_path,
                title=title,
                description=strip_html_tags(story),
                tags=["AI", "FairyTale", "Animal"]
            )
            logger.info(f"Video uploaded to YouTube with video ID: {youtube_video_id}")
        except Exception as e:
            logger.error(f"Error uploading video to YouTube: {e}")
    else:
        logger.error("No video file available for YouTube upload.")

    # 8. Clean up local files (image, audio, and video)
    cleanup_file(image_path)
    cleanup_file(audio_file_path)
    if video_path:
        cleanup_file(video_path)
    cleanup_directory(os.path.join('.', 'images'))
    cleanup_directory(os.path.join('.', 'videos'))

if __name__ == "__main__":
    post_ai_article()
