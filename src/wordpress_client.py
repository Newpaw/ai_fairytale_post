import base64
import requests
import time
from requests.auth import HTTPBasicAuth
from config import WORDPRESS_BASE_URL, WORDPRESS_USERNAME, WORDPRESS_APPLICATION_PASSWORD
from logger import logger

def retry_request(request_func, retries=3, delay=2, **kwargs):
    """
    Generic retry function for HTTP requests.
    
    Tries to execute 'request_func' with the given keyword arguments.
    Accepts response status codes 200 and 201 as success, jinak čeká 'delay' sekund a opakuje.
    """
    for attempt in range(1, retries + 1):
        response = request_func(**kwargs)
        if response.status_code in (200, 201):
            return response
        logger.error(f"Attempt {attempt}: Request failed with status code: {response.status_code}")
        time.sleep(delay)
    raise RuntimeError(f"Operation failed after {retries} retries.")

class WordpressClient:
    """Synchronní komunikace s WordPress pomocí REST API."""

    def __init__(self):
        self.base_url = WORDPRESS_BASE_URL
        self.auth = HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_APPLICATION_PASSWORD)

    def upload_image(self, base64_image: str, filename: str) -> int:
        """
        Nahraje obrázek do WordPress media library a vrátí attachment ID.
        """
        url = f"{self.base_url}/wp-json/wp/v2/media"
        image_data = base64.b64decode(base64_image)
        headers = {
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'image/jpeg'
        }
        response = retry_request(
            requests.post,
            retries=3,
            delay=2,
            url=url,
            auth=self.auth,
            headers=headers,
            data=image_data
        )
        if response.status_code == 201:
            attachment_id = response.json().get('id')
            logger.info(f"Obrázek nahrán, ID: {attachment_id}")
            return attachment_id
        else:
            logger.error(f"Nahrání obrázku selhalo: {response.status_code}")
            logger.error(response.text)
            raise RuntimeError(f"Image upload failed with status code: {response.status_code}")

    def upload_audio(self, base64_audio: str, filename: str) -> int:
        """
        Nahraje audio soubor do WordPress media library a vrátí attachment ID.
        """
        url = f"{self.base_url}/wp-json/wp/v2/media"
        audio_data = base64.b64decode(base64_audio)
        headers = {
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'audio/mpeg'
        }
        response = retry_request(
            requests.post,
            retries=3,
            delay=2,
            url=url,
            auth=self.auth,
            headers=headers,
            data=audio_data
        )
        if response.status_code == 201:
            attachment_id = response.json().get('id')
            logger.info(f"Audio nahráno, ID: {attachment_id}")
            return attachment_id
        else:
            logger.error(f"Nahrání audia selhalo: {response.status_code}")
            logger.error(response.text)
            raise RuntimeError(f"Audio upload failed with status code: {response.status_code}")

    def get_media_url(self, attachment_id: int, retries: int = 3, delay: int = 2) -> str:
        """
        Attempts to retrieve the media URL with a simple retry mechanism.
        """
        url = f"{self.base_url}/wp-json/wp/v2/media/{attachment_id}"
        for attempt in range(1, retries + 1):
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                media_url = response.json().get('source_url')
                if media_url:
                    return media_url
            else:
                logger.error(
                    f"Attempt {attempt}: Failed to retrieve media URL for attachment {attachment_id}: {response.status_code}"
                )
            time.sleep(delay)
        raise RuntimeError(f"Failed to retrieve media URL for attachment {attachment_id} after {retries} attempts")

    def create_post(self, title: str, content: str):
        """
        Vytvoří nový příspěvek na WordPressu.
        """
        url = f"{self.base_url}/wp-json/wp/v2/posts"
        aigenerated_category_id = 17  # Nastav si podle svých potřeb
        data = {
            "title": title,
            "content": content,
            "status": "publish",
            "categories": [aigenerated_category_id]
        }
        response = retry_request(
            requests.post,
            retries=3,
            delay=2,
            url=url,
            auth=self.auth,
            json=data
        )
        if response.status_code == 201:
            logger.info("Příspěvek vytvořen.")
            return response.json()
        else:
            logger.error(f"Chyba při vytváření příspěvku: {response.status_code}")
            logger.error(response.json())
            raise RuntimeError(f"Post creation failed with status code: {response.status_code}")

    def create_post_with_image(self, title: str, content: str, base64_image: str, filename: str):
        """
        Vytvoří příspěvek s obrázkem – nejprve nahraje obrázek a poté ho připojí.
        """
        attachment_id = self.upload_image(base64_image, filename)
        url = f"{self.base_url}/wp-json/wp/v2/posts"
        aigenerated_category_id = 17
        data = {
            "title": title,
            "content": content,
            "status": "publish",
            "categories": [aigenerated_category_id],
            "featured_media": attachment_id
        }
        response = retry_request(
            requests.post,
            retries=3,
            delay=2,
            url=url,
            auth=self.auth,
            json=data
        )
        if response.status_code == 201:
            logger.info("Příspěvek s obrázkem vytvořen.")
            return response.json()
        else:
            logger.error(f"Chyba při vytváření příspěvku s obrázkem: {response.status_code}")
            logger.error(response.json())
            raise RuntimeError(f"Post creation with image failed with status code: {response.status_code}")

    def create_post_with_audio(self, title: str, content: str, base64_audio: str, filename: str):
        """
        Vytvoří příspěvek s audio přehrávačem – audio se nejprve nahraje, pak se jeho URL vloží do HTML.
        """
        # Nahraj audio
        attachment_id = self.upload_audio(base64_audio, filename)
        # Získej URL nahraného audia
        media_url = self.get_media_url(attachment_id)
        # Vytvoř HTML audio přehrávač
        audio_html = f'<audio controls src="{media_url}"></audio>'
        # Připoj audio přehrávač k obsahu
        new_content = content + "\n" + audio_html
        url = f"{self.base_url}/wp-json/wp/v2/posts"
        aigenerated_category_id = 17
        data = {
            "title": title,
            "content": new_content,
            "status": "publish",
            "categories": [aigenerated_category_id]
        }
        response = retry_request(
            requests.post,
            retries=3,
            delay=2,
            url=url,
            auth=self.auth,
            json=data
        )
        if response.status_code == 201:
            logger.info("Příspěvek s audiem vytvořen.")
            return response.json()
        else:
            logger.error(f"Chyba při vytváření příspěvku s audiem: {response.status_code}")
            logger.error(response.json())
            raise RuntimeError(f"Post creation with audio failed with status code: {response.status_code}")
