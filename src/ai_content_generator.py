import os
import json
import requests
import re
import uuid  # Importing uuid for unique image naming
from openai import AzureOpenAI
from config import API_VERSION, AZURE_ENDPOINT, API_KEY, DALLE_API_VERSION
from logger import logger
import random
from typing import Tuple, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "animals.json")
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "selected_animals.json")

def load_selected_animals() -> list:
    if os.path.exists(HISTORY_FILE_PATH):
        with open(HISTORY_FILE_PATH, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                logger.error("Error decoding JSON from history file.")
                return []
    return []

def save_selected_animal(animal_identifier: str) -> None:
    selected_animals = load_selected_animals()
    selected_animals.append(animal_identifier)
    with open(HISTORY_FILE_PATH, 'w') as file:
        json.dump(selected_animals, file, indent=4)

def is_animal_selected(animal_identifier: str) -> bool:
    selected_animals = load_selected_animals()
    return animal_identifier in selected_animals

def choose_random_animal() -> str:
    with open(JSON_FILE_PATH, 'r') as file:
        animals = json.load(file)
    return random.choice(animals)

def choose_random_mood() -> str:
    moods = [
        "šťastný", "smutný", "natěšený", "zvědavý", "ospalý",
        "nadšený", "rozzlobený", "klidný", "roztržitý", "sebejistý",
        "nervózní", "vystrašený", "zklamaný", "pyšný", "frustrovaný",
        "spokojený", "zmatený", "nostalgický", "překvapený", "líný"
    ]
    return random.choice(moods)

def generate_image(animal_name: str, mood: str, title: str) -> Optional[str]:
    """
    Generates an image using DALL-E 3 with a prompt that clearly incorporates the animal name,
    its mood, and the story title. The prompt is in English to ensure best results.
    """
    client = AzureOpenAI(
        api_version=DALLE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
        api_key=API_KEY
    )
    try:
        prompt = (
            f"Create an enchanting and detailed illustration in a plush, heartwarming style that clearly reflects a unique Czech fairy tale. "
            f"Focus on a {animal_name} that radiates a distinct air of {mood}. "
            f"Infuse the illustration with the narrative spirit and atmosphere of the fairy tale titled '{title}'. "
            "The animal should have soft, rounded features, expressive eyes, and a cuddly, huggable appearance. "
            "The background should enhance the overall mood with dreamy pastel hues and subtle magical elements. "
            "Ensure that the animal's characteristics, its mood, and the story's title are all clearly represented in the composition. "
            "Do not include any text, letters, or numbers in the image!"
        )
        result = client.images.generate(
            model="dalle-e-3",  # Name of your DALL-E 3 deployment
            prompt=prompt,
            n=1
        )
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None

    try:
        json_response = json.loads(result.model_dump_json())
        image_url = json_response["data"][0]["url"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing image generation response: {e}")
        return None

    # Create the images directory safely
    image_dir = os.path.join(os.curdir, 'images')
    os.makedirs(image_dir, exist_ok=True)
    
    # Generate a unique filename using uuid
    unique_filename = f"{uuid.uuid4()}.png"
    image_path = os.path.join(image_dir, unique_filename)

    response = requests.get(image_url)
    if response.status_code == 200:
        with open(image_path, "wb") as image_file:
            image_file.write(response.content)
        logger.info(f"Image saved to {image_path}")
        return image_path
    else:
        logger.error(f"Failed to download image. Status code: {response.status_code}")
        return None

def generate_post_title_and_story(animal_name: str, mood: str) -> Optional[Tuple[str, str]]:
    client = AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
        api_key=API_KEY
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Jsi výborný český spisovatel pohádek, jehož příběhy znají děti po celém kraji. "
                "Tvůj styl je laskavý, hravý a plný poetiky, přičemž se inspiruješ klasikou, jako jsou pohádky Karla Jaromíra Erbena či Boženy Němcové. "
                "Máš dar vykreslit pohádkové světy tak, aby si je čtenář dokázal živě představit, a zároveň do příběhů vkládáš moudré ponaučení. "
                "Piš vždy krásnou, bohatou češtinou a dbej na melodii vět. "
                "Každý tvůj úkol bude znít jednoduše – dostaneš název zvířátka a na jeho základě složíš originální českou pohádku. "
                "Tvé pohádky by měly být klasické, avšak s moderním přesahem, který osloví i dnešní čtenáře. "
                "Používej klasickou pohádkovou strukturu: úvod (kdo, kde, proč), zápletku, dobrodružství, zkoušku a ponaučení. "
                "Pohádka by měla mít hřejivý tón, ale občas může obsahovat jemný humor či nečekaný obrat. "
            )
        },
        {
            "role": "user",
            "content": (
                f"Zvolené zvířátko: {animal_name} a pocit zvířátka je: {mood}.\n\n"
                "Napiš krásnou českou pohádku, která bude mít:\n"
                "Výstup musí být ve formátu HTML (pouze nadpis h2 a paragrafy)!\n"
                "1) Název, který je poetický a lákavý\n"
                "2) Úvod s představením hrdiny a jeho světa\n"
                "3) Zajímavou zápletku, která obsahuje kouzlo, moudrost nebo překážku\n"
                "4) Vyvrcholení, kde se ukáže síla charakteru hrdiny\n"
                "5) Poučení, které děti odnese do života\n\n"
                "Používej nádhernou obrazotvornost, bohatý jazyk a přímou řeč postav, aby byl příběh živý a poutavý."
            )
        }
    ]
    try:
        completion = client.chat.completions.create(
            model="gpt-4",  # or 'gpt-35-turbo'
            messages=messages,
            temperature=0.7,
            max_tokens=4000
        )
    except Exception as e:
        logger.error(f"Error generating story: {e}")
        return None

    if completion and completion.choices:
        answer_text = completion.choices[0].message.content
        # Clean up the response by removing markdown code fences
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
        # Use a separator to create a unique identifier
        identifier = f"{animal}|{mood}"
        if not is_animal_selected(identifier):
            result = generate_post_title_and_story(animal, mood)
            if not result:
                logger.error("Story generation failed, trying another animal...")
                attempts += 1
                continue
            title, story = result

            # Remove the first <h2> element from the story so it's not returned twice.
            story = re.sub(r"<h2>.*?</h2>\s*", "", story, count=1, flags=re.IGNORECASE | re.DOTALL)
            
            image_path = generate_image(animal, mood, title)
            if not image_path:
                logger.error("Image generation failed, trying another animal...")
                attempts += 1
                continue

            save_selected_animal(identifier)
            
            return title, story, image_path
        else:
            logger.warning(f"The animal '{animal}' with mood '{mood}' has already been selected. Trying again...")
            attempts += 1

    raise Exception("No unique animal content could be generated after multiple attempts.")

def main() -> None:
    try:
        title, story, image_path = generate_unique_animal_content()
        logger.info(f"Title: {title}, Story first 100 characters: {story[:100]}, Image Path: {image_path}")
    except Exception as e:
        logger.error(f"An error occurred in main: {e}")

if __name__ == "__main__":
    main()
