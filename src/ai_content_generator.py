import os
import json
import requests
import re
import uuid
import random
from typing import Tuple, Optional
from deep_translator import GoogleTranslator
from openai import AzureOpenAI
from config import API_VERSION, AZURE_ENDPOINT, API_KEY, DALLE_API_VERSION
from logger import logger

# Define base directory and file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "animals.json")
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "selected_animals.json")


def load_selected_animals() -> list:
    """
    Loads the list of selected animal identifiers from the history file.
    Returns an empty list if the file does not exist or if there's a JSON decode error.
    """
    if os.path.exists(HISTORY_FILE_PATH):
        try:
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            logger.error("Error reading JSON from history file.")
            return []
    return []


def save_selected_animal(animal_identifier: str) -> None:
    """
    Saves a new animal identifier to the history file.
    """
    selected_animals = load_selected_animals()
    selected_animals.append(animal_identifier)
    with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as file:
        json.dump(selected_animals, file, indent=4)


def is_animal_selected(animal_identifier: str) -> bool:
    """
    Checks if an animal identifier has already been selected.
    """
    selected_animals = load_selected_animals()
    return animal_identifier in selected_animals


def choose_random_animal() -> str:
    """
    Chooses a random animal from the animals JSON file.
    Raises an exception if the file is empty or missing.
    """
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as file:
        animals = json.load(file)
    if not animals:
        raise ValueError("No animals found in the JSON file.")
    return random.choice(animals)


def choose_random_mood() -> str:
    """
    Returns a random mood from a predefined list.
    """
    moods = [
        "šťastný", "smutný", "natěšený", "zvědavý", "ospalý", "nadšený",
        "rozzlobený", "klidný", "roztržitý", "sebejistý", "nervózní",
        "vystrašený", "zklamaný", "pyšný", "frustrovaný", "spokojený",
        "zmatený", "nostalgický", "překvapený", "líný",
    ]
    return random.choice(moods)


def safe_translate(text: str, source_lang: str = "cs", target_lang: str = "en") -> str:
    """
    Safely translates text from source_lang to target_lang.
    If translation fails or returns an empty result, returns the original text.
    """
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        if not translated:
            logger.warning(f"Translation returned empty for text: {text}")
            return text
        return translated
    except Exception as e:
        logger.error(f"Translation error for text '{text}': {e}")
        return text


def generate_image(animal_name: str, mood: str, title: str) -> Optional[str]:
    """
    Generates an image using DALL-E 3 with a prompt containing the animal name,
    its mood, and the story title. Returns the absolute path to the saved image.
    """
    client = AzureOpenAI(
        api_version=DALLE_API_VERSION, azure_endpoint=AZURE_ENDPOINT, api_key=API_KEY
    )
    en_animal_name = safe_translate(animal_name)
    en_mood = safe_translate(mood)
    en_title = safe_translate(title)

    prompt = (
        f"Create an enchanting and detailed illustration in a plush, heartwarming style that clearly reflects a unique Czech fairy tale. "
        f"Focus on a {en_animal_name} that radiates a distinct air of {en_mood}. "
        f"Infuse the illustration with the narrative spirit and atmosphere of the fairy tale titled '{en_title}'. "
        "Focus on specific, visually representable elements. "
        "Describe actions and scenarios rather than abstract concepts. "
        "Avoid ambiguous language that could be interpreted as including text. "
        "The animal should have soft, rounded features, expressive eyes, and a cuddly, huggable appearance. "
        "The background should enhance the overall mood with dreamy pastel hues and subtle magical elements. "
        f"Ensure that the animal's characteristics, its mood ({en_mood}), and the story's title are all clearly represented in the composition. "
        "The final image must not include any text, letters, numbers, or symbols anywhere in the composition!"
    )
    logger.info(
        f"Generating image with animal name: {animal_name} / {en_animal_name}, mood: {mood} / {en_mood}, title: {title} / {en_title}"
    )

    try:
        result = client.images.generate(model="dalle-e-3", prompt=prompt, n=1)
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None

    logger.debug(f"Result from image generation: {result}")

    try:
        if hasattr(result, "model_dump_json"):
            result_json = json.loads(result.model_dump_json())
        elif isinstance(result, dict):
            result_json = result
        else:
            raise ValueError("Unexpected result format from image generation.")
        logger.debug(f"Parsed JSON response: {result_json}")
        image_url = result_json["data"][0]["url"]
        logger.info(f"Extracted image URL: {image_url}")
    except Exception as e:
        logger.error(f"Error parsing image generation response: {e}")
        return None

    image_dir = os.path.join(BASE_DIR, "images")
    os.makedirs(image_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}.png"
    image_path = os.path.join(image_dir, unique_filename)

    try:
        response = requests.get(image_url)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None

    with open(image_path, "wb") as image_file:
        image_file.write(response.content)
    logger.info(f"Image saved to {image_path}")
    return image_path


def generate_post_title_and_story(animal_name: str, mood: str) -> Optional[Tuple[str, str]]:
    """
    Generates a post title and story using a chat completion API.
    The story is expected to be in HTML format with an <h2> title and paragraphs.
    Returns a tuple of (title, story) if successful.
    """
    client = AzureOpenAI(
        api_version=API_VERSION, azure_endpoint=AZURE_ENDPOINT, api_key=API_KEY
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are an amazing Czech children's fairy tale writer. Your stories are simple, magical, and easy to understand for young readers. "
                "You write in a friendly and playful language that creates a clear and vivid picture of a fairy tale world. "
                "Your style is comprehensible, melodic, and straightforward – every word carries joy and adventure. "
                "Your task: based on the name of the animal, create an original Czech fairy tale with a clear structure including an introduction, conflict, adventure, climax, and a simple moral. "
                "Ensure that the plot is engaging and the language accessible even for the youngest."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Chosen animal: {animal_name} with mood: {mood}.\n\n"
                "Write a simple and magical Czech fairy tale in HTML format (only an <h2> title and paragraphs) that includes:\n"
                "1) A beautiful and enticing title\n"
                "2) An introduction presenting the hero and their magical world\n"
                "3) A conflict involving magic, adventure, or an obstacle\n"
                "4) A climax where the hero overcomes the difficulties\n"
                "5) A simple and understandable moral that children can easily remember\n\n"
                "Use simple yet lively language, short sentences, and direct speech to ensure the story is engaging and easy to read for small children."
            ),
        },
    ]

    try:
        completion = client.chat.completions.create(
            model="gpt-4", messages=messages, temperature=0.7, max_tokens=4000
        )
    except Exception as e:
        logger.error(f"Error generating story: {e}")
        return None

    if completion and completion.choices:
        answer_text = completion.choices[0].message.content
        # Remove code block markers if present
        answer_text = "\n".join(
            line for line in answer_text.splitlines() if line.strip() not in ("```", "```html")
        )
        title_match = re.search(r"<h2>(.*?)</h2>", answer_text, re.IGNORECASE)
        title = title_match.group(1) if title_match else "Untitled"
        return title, answer_text
    else:
        logger.error("No completion received from the story generation API.")
        return None


def generate_unique_animal_content(max_attempts: int = 10) -> Tuple[str, str, str]:
    attempts = 0
    while attempts < max_attempts:
        animal = choose_random_animal()
        mood = choose_random_mood()
        identifier = f"{animal}|{mood}"
        if not is_animal_selected(identifier):
            result = generate_post_title_and_story(animal, mood)
            if not result:
                logger.error("Story generation failed, trying another animal...")
                attempts += 1
                continue
            title, story = result
            # Remove the first <h2> title from the story to avoid duplication
            story = re.sub(r"<h2>.*?</h2>\s*", "", story, count=1, flags=re.IGNORECASE | re.DOTALL)
            
            # NEW STEP: Validate and correct the story using the LLM quality control
            story = validate_and_correct_output(story)
            
            image_path = generate_image(animal, mood, title)
            if not image_path:
                logger.error("Image generation failed, trying another animal...")
                attempts += 1
                continue
            save_selected_animal(identifier)
            return title, story, image_path
        else:
            logger.warning(f"Animal '{animal}' with mood '{mood}' has already been selected. Trying another...")
            attempts += 1

    raise Exception("Failed to generate unique content after several attempts.")


def validate_and_correct_output(text: str) -> str:
    """
    Uses an LLM to validate and correct the given text for quality, clarity, grammar,
    narrative coherence, adherence to the concept, entertainment value, and smooth flow.
    If the correction fails, the original text is returned.
    """
    client = AzureOpenAI(api_version=API_VERSION, azure_endpoint=AZURE_ENDPOINT, api_key=API_KEY)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a master editor and storyteller with a keen eye for detail and narrative integrity. "
                "Your task is to review the provided text and ensure it is error-free, stylistically polished, and logically coherent from beginning to end. "
                "Make sure the text strictly adheres to the intended concept, is engaging and entertaining, and flows smoothly. "
                "Revise the text accordingly and return only the corrected version in Czech."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Please review the following story and correct any issues related to grammar, style, narrative coherence, "
                f"concept adherence, entertainment value, and smooth flow:\n\n{text}"
            ),
        },
    ]
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4", messages=messages, temperature=0.3, max_tokens=4000
        )
        if completion and completion.choices:
            corrected_text = completion.choices[0].message.content.strip()
            return corrected_text if corrected_text else text
        else:
            logger.warning("No correction received; returning original text.")
            return text
    except Exception as e:
        logger.error(f"Error during output validation: {e}")
        return text




def main() -> None:
    """
    Main function to generate the unique animal content and log the results.
    """
    try:
        title, story, image_path = generate_unique_animal_content()
        logger.info(f"Title: {title}, first 100 characters of story: {story[:100]}, Image Path: {image_path}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
