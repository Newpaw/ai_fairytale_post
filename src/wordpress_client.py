import base64
import requests
from requests.auth import HTTPBasicAuth
from config import WORDPRESS_BASE_URL, WORDPRESS_USERNAME, WORDPRESS_APPLICATION_PASSWORD
from logger import logger

class WordpressClient:
    """Class for synchronous interaction with WordPress via REST API."""

    def __init__(self):
        self.base_url = WORDPRESS_BASE_URL
        self.auth = HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APPLICATION_PASSWORD)

    def upload_image(self, base64_image: str, filename: str) -> int:
        """
        Uploads an image to the WordPress media library and returns the attachment ID.
        :param base64_image: Base64-encoded image data.
        :param filename: Desired filename for the uploaded media on WordPress.
        :return: The ID of the uploaded media (attachment).
        """
        url = f"{self.base_url}/wp-json/wp/v2/media"

        # Decode the base64 string to raw binary data
        image_data = base64.b64decode(base64_image)

        # Prepare headers
        headers = {
            'Content-Disposition': f'attachment; filename={filename}',
            # Adjust the Content-Type according to your image type
            'Content-Type': 'image/jpeg'
        }

        # Perform the request
        response = requests.post(url, auth=self.auth, headers=headers, data=image_data)

        if response.status_code == 201:
            # Extract the attachment ID from the JSON response
            attachment_id = response.json().get('id')
            logger.info(f"Image uploaded successfully, ID: {attachment_id}")
            return attachment_id
        else:
            logger.error(f"Failed to upload image: {response.status_code}")
            logger.error(response.text)
            raise RuntimeError(f"Image upload failed with status code: {response.status_code}")

    def create_post(self, title: str, content: str):
        """
        Creates a new post on the WordPress site.
        :param title: Title of the post.
        :param content: Body content of the post (HTML allowed).
        """
        url = f"{self.base_url}/wp-json/wp/v2/posts"

        aigenerated_category_id = 6  # Example category ID

        data = {
            "title": title,
            "content": content,
            "status": "publish",
            "categories": [aigenerated_category_id]
        }

        response = requests.post(url, auth=self.auth, json=data)

        if response.status_code == 201:
            logger.info("Post created successfully.")
            return response.json()
        else:
            logger.error(f"Error while creating post: {response.status_code}")
            logger.error(response.json())
            raise RuntimeError(f"Post creation failed with status code: {response.status_code}")

    def create_post_with_image(self, title: str, content: str, base64_image: str, filename: str):
        """
        Creates a new post with a featured image on the WordPress site.
        :param title: Title of the post.
        :param content: Body content of the post.
        :param base64_image: Base64-encoded image data to be uploaded and set as featured image.
        :param filename: Filename for the uploaded image in WordPress.
        """
        # 1) Upload the image
        attachment_id = self.upload_image(base64_image, filename)

        # 2) Create the post with the attached image as featured_media
        url = f"{self.base_url}/wp-json/wp/v2/posts"
        aigenerated_category_id = 6

        data = {
            "title": title,
            "content": content,
            "status": "publish",
            "categories": [aigenerated_category_id],
            "featured_media": attachment_id  # Attach the uploaded image here
        }

        response = requests.post(url, auth=self.auth, json=data)
        if response.status_code == 201:
            logger.info("Post with featured image created successfully.")
            return response.json()
        else:
            logger.error(f"Error while creating post with image: {response.status_code}")
            logger.error(response.json())
            raise RuntimeError(f"Post creation with image failed with status code: {response.status_code}")

