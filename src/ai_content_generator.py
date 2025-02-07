import os
import json
import requests
import re
import uuid
from openai import AzureOpenAI
from config import API_VERSION, AZURE_ENDPOINT, API_KEY, DALLE_API_VERSION
from logger import logger
import random
from typing import Tuple, Optional
from deep_translator import GoogleTranslator

# Use any translator you like, in this example GoogleTranslator


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "animals.json")
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "selected_animals.json")


def load_selected_animals() -> list:
    if os.path.exists(HISTORY_FILE_PATH):
        with open(HISTORY_FILE_PATH, "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                logger.error("Chyba při čtení JSON ze souboru historie.")
                return []
    return []


def save_selected_animal(animal_identifier: str) -> None:
    selected_animals = load_selected_animals()
    selected_animals.append(animal_identifier)
    with open(HISTORY_FILE_PATH, "w") as file:
        json.dump(selected_animals, file, indent=4)


def is_animal_selected(animal_identifier: str) -> bool:
    selected_animals = load_selected_animals()
    return animal_identifier in selected_animals


def choose_random_animal() -> str:
    with open(JSON_FILE_PATH, "r") as file:
        animals = json.load(file)
    return random.choice(animals)


def choose_random_mood() -> str:
    moods = [
        "šťastný",
        "smutný",
        "natěšený",
        "zvědavý",
        "ospalý",
        "nadšený",
        "rozzlobený",
        "klidný",
        "roztržitý",
        "sebejistý",
        "nervózní",
        "vystrašený",
        "zklamaný",
        "pyšný",
        "frustrovaný",
        "spokojený",
        "zmatený",
        "nostalgický",
        "překvapený",
        "líný",
    ]
    return random.choice(moods)


def generate_image(animal_name: str, mood: str, title: str) -> Optional[str]:
    """
    Vygeneruje obrázek pomocí DALL-E 3 s promptem, který obsahuje jméno zvířete,
    jeho náladu a název příběhu. Vrátí absolutní cestu k uloženému obrázku.
    """
    client = AzureOpenAI(
        api_version=DALLE_API_VERSION, azure_endpoint=AZURE_ENDPOINT, api_key=API_KEY
    )
    en_animal_name = GoogleTranslator(source="cs", target="en").translate(animal_name)
    en_mood = GoogleTranslator(source="cs", target="en").translate(mood)
    en_title = GoogleTranslator(source="cs", target="en").translate(title)

    prompt = (
        f"Create an enchanting and detailed illustration in a plush, heartwarming style that clearly reflects a unique Czech fairy tale. "
        f"Focus on a {en_animal_name} that radiates a distinct air of {en_mood}. "
        f"Infuse the illustration with the narrative spirit and atmosphere of the fairy tale titled '{en_title}'."
        "Focus on specific, visually representable elements"
        "Describe actions and scenarios rather than abstract concepts."
        "Avoid ambiguous language that could be interpreted as including text."
        "The animal should have soft, rounded features, expressive eyes, and a cuddly, huggable appearance. "
        "The background should enhance the overall mood with dreamy pastel hues and subtle magical elements. "
        f"Ensure that the animal's characteristics, its mood ({en_mood}), and the story's title are all clearly represented in the composition."
        "The final image must not include any text, letters, numbers, or symbols anywhere in the composition!"
    )
    logger.info(
        f"Generating image with animal name: {animal_name or ''}/{en_animal_name or ''}, mood: {mood or ''}/{en_mood or ''}, title: {title or ''}/{en_title or ''}"
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
        else:
            result_json = result
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
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None

    if response.status_code == 200:
        with open(image_path, "wb") as image_file:
            image_file.write(response.content)
        logger.info(f"Image saved to {image_path}")
        return image_path
    else:
        logger.error(f"Failed to download image. Status code: {response.status_code}")
        return None


def generate_post_title_and_story(
    animal_name: str, mood: str
) -> Optional[Tuple[str, str]]:
    client = AzureOpenAI(
        api_version=API_VERSION, azure_endpoint=AZURE_ENDPOINT, api_key=API_KEY
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Jsi úžasný český spisovatel pohádek pro děti. Tvé příběhy jsou jednoduché, kouzelné a snadno pochopitelné pro malé čtenáře. "
                "Píšeš přátelským a hravým jazykem, který vytváří jasný a živý obraz pohádkového světa. "
                "Tvůj styl je srozumitelný, melodický a přímý – každé slovo nese radost a dobrodružství. "
                "Dostaneš jednoduchý úkol: na základě názvu zvířátka vytvoříš originální českou pohádku, která bude mít jasnou strukturu s úvodem, zápletkou, dobrodružstvím, vyvrcholením a jednoduchým ponaučením. "
                "Dbáš na to, aby byl děj poutavý a jazyk přístupný i pro ty nejmenší."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Zvolené zvířátko: {animal_name} a jeho nálada je: {mood}.\n\n"
                "Napiš jednoduchou a kouzelnou českou pohádku, která bude mít:\n"
                "Výstup musí být ve formátu HTML (pouze nadpis h2 a odstavce)!\n"
                "1) Krásný a lákavý název\n"
                "2) Úvod, který představí hrdinu a jeho kouzelný svět\n"
                "3) Zápletku s kouzlem, dobrodružstvím nebo překážkou\n"
                "4) Vyvrcholení, kde se ukáže, jak hrdina překoná obtíže\n"
                "5) Jednoduché a srozumitelné ponaučení, které si děti snadno zapamatují\n\n"
                "Používej jednoduchý, ale živý jazyk, krátké věty a přímou řeč, aby byl příběh poutavý a snadno čitelný pro malé děti."
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
        answer_text = "\n".join(
            line
            for line in answer_text.splitlines()
            if line.strip() not in ("```", "```html")
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
                logger.error("Generování příběhu selhalo, zkouším další zvíře...")
                attempts += 1
                continue
            title, story = result
            # Odstraníme první <h2> (název) z příběhu, aby se neopakoval
            story = re.sub(
                r"<h2>.*?</h2>\s*", "", story, count=1, flags=re.IGNORECASE | re.DOTALL
            )
            image_path = generate_image(animal, mood, title)
            if not image_path:
                logger.error("Generování obrázku selhalo, zkouším další zvíře...")
                attempts += 1
                continue
            save_selected_animal(identifier)
            return title, story, image_path
        else:
            logger.warning(
                f"Zvíře '{animal}' s náladou '{mood}' už bylo vybráno. Zkouším další..."
            )
            attempts += 1

    raise Exception("Po několika pokusech se nepodařilo vygenerovat unikátní obsah.")


def main() -> None:
    try:
        title, story, image_path = generate_unique_animal_content()
        logger.info(
            f"Title: {title}, prvních 100 znaků příběhu: {story[:100]}, Image Path: {image_path}"
        )
    except Exception as e:
        logger.error(f"Nastala chyba: {e}")


if __name__ == "__main__":
    main()
