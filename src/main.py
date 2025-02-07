import re
import os
import base64
import uuid
from ai_content_generator import generate_unique_animal_content
from wordpress_client import WordpressClient
from logger import logger

def post_ai_article():

    try:
        title, story, image_path = generate_unique_animal_content()
        logger.debug(f"Title: {title}, Story first 100 characters: {story[:100]}, Image Path: {image_path}")
    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

    client = WordpressClient()

   
    try:
        with open(image_path, 'rb') as image_file:
            base64_bytes = base64.b64encode(image_file.read())
            
            # Generate a unique file name for the image
            image_name = uuid.uuid4().hex + ".png"
            
            
            client.create_post_with_image(title, story, base64_bytes, image_name)
            
            # Optionally check `response` for success or error
            logger.info(f"Post published with title: {title}")
    
    except Exception as e:
        logger.error(f"Error while publishing the post: {e}")
        return
    
    # (5) Clean up local image file
    try:
        os.remove(image_path)
    except OSError as remove_err:
        logger.warning(f"Could not remove file {image_path}: {remove_err}")
    # Remove images directory if it's empty
    images_dir = os.path.join('.', 'images')
    if os.path.isdir(images_dir) and not os.listdir(images_dir):
        try:
            os.rmdir(images_dir)
        except OSError as e:
            logger.warning(f"Could not remove directory {images_dir}: {e}")

if __name__ == "__main__":
    post_ai_article()
