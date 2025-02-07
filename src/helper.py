import re
import os
from logger import logger

def strip_html_tags(text: str) -> str:
    """
    Remove all HTML tags from the given text.
    
    :param text: The text possibly containing HTML tags.
    :return: Clean text without HTML tags.
    """
    return re.sub(r'<[^>]*>', '', text)

def combine_content(story: str, audio_html: str) -> str:
    """
    Combine the story text with the audio player HTML.
    
    :param story: The story text.
    :param audio_html: The HTML snippet for the audio player.
    :return: The combined content.
    """
    return audio_html + "\n" +  story 

def cleanup_file(file_path: str):
    """
    Attempt to delete a file and log the result.
    
    :param file_path: Path to the file to be removed.
    """
    try:
        os.remove(file_path)
        logger.info(f"Deleted file: {file_path}")
    except OSError as e:
        logger.warning(f"Could not delete file {file_path}: {e}")

def cleanup_directory(directory_path: str):
    """
    Delete the directory if it exists and is empty.
    
    :param directory_path: Path to the directory.
    """
    if os.path.isdir(directory_path) and not os.listdir(directory_path):
        try:
            os.rmdir(directory_path)
            logger.info(f"Deleted empty directory: {directory_path}")
        except OSError as e:
            logger.warning(f"Could not delete directory {directory_path}: {e}")
