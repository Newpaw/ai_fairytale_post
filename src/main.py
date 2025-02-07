import os
import base64
import uuid
import requests
from ai_content_generator import generate_unique_animal_content
from wordpress_client import WordpressClient
from logger import logger
from elevenlabs_client import generate_audio
from helper import strip_html_tags, combine_content, cleanup_file, cleanup_directory

def post_ai_article():
    try:
        title, story, image_path = generate_unique_animal_content()
        logger.debug(f"Title: {title}, story (first 100 chars): {story[:100]}, image path: {image_path}")
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return

    client = WordpressClient()

    # 1. Upload the featured image (thumbnail)
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

    # 2. Clean the story text and generate audio
    story_clean = strip_html_tags(story)
    try:
        audio_file_path = generate_audio(story_clean)
        logger.info(f"Audio generated: {audio_file_path}")
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        return

    # 3. Upload the audio file and get its URL for embedding in content
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

    # 5. Create the post with the featured image set
    try:
        data = {
            "title": title,
            "content": combined_content,
            "status": "publish",
            "categories": [17],  # uprav ID kategorie dle potřeby
            "featured_media": image_attachment_id  # nastavení náhledového obrázku
        }
        post_url = f"{client.base_url}/wp-json/wp/v2/posts"
        response = requests.post(post_url, auth=client.auth, json=data)
        if response.status_code == 201:
            logger.info(f"Post published, title: {title}")
        else:
            logger.error(f"Error creating post: {response.status_code}")
            logger.error(response.text)
            return
    except Exception as e:
        logger.error(f"Error publishing post: {e}")
        return

    # 6. Clean up local files (image and audio)
    cleanup_file(image_path)
    cleanup_file(audio_file_path)
    # Optionally remove images directory if empty
    cleanup_directory(os.path.join('.', 'images'))

if __name__ == "__main__":
    post_ai_article()
