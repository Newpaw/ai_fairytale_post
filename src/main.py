import re
import os
import base64
import uuid
from ai_content_generator import generate_ai_content
from wordpress_client import WordpressClient
from logger import logger

def post_ai_article():
    # (1) Get AI-generated HTML text
    ai_text_html = generate_ai_content()
    if not ai_text_html:
        logger.info("No AI-generated text found.")
        return
    
    # (2) Parse <h2> as post title
    match = re.search(r"<h2>(.*?)</h2>", ai_text_html, re.IGNORECASE)
    if match:
        post_title = match.group(1)
        # Remove the first occurrence of <h2>...</h2> from the HTML
        ai_text_html = re.sub(r"<h2>.*?</h2>", "", ai_text_html, count=1, flags=re.IGNORECASE)
    else:
        post_title = "AI Generated Post"

    # (3) Instantiate the WordPress
    client = WordpressClient()

    # (4) Attempt to publish the post with an image
    image_path = os.path.join('.', 'images', 'generated_image.png')
    
    # Check if the file exists to avoid FileNotFoundError
    if not os.path.exists(image_path):
        logger.error(f"Image file not found at {image_path}.")
        return
    
    try:
        with open(image_path, 'rb') as image_file:
            base64_bytes = base64.b64encode(image_file.read())
            
            # Generate a unique file name for the image
            image_name = uuid.uuid4().hex + ".png"
            
            # Publish post and attach the image
            response = client.create_post_with_image(post_title, ai_text_html, base64_bytes, image_name)
            
            # Optionally check `response` for success or error
            logger.info(f"Post published with title: {post_title}")
    
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
