import os
import json
import requests
import re
from openai import AzureOpenAI
from config import API_VERSION, AZURE_ENDPOINT, API_KEY, DALLE_API_VERSION, DALLE_ENDPOINT
from logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "last_json.json")


def generate_image(text_promt:str):
    client = AzureOpenAI(
        api_version=DALLE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT, 
        api_key=API_KEY
    )
    result = client.images.generate(
    model="dalle-e-3", # the name of your DALL-E 3 deployment
    prompt= f"""Create a stunning and highly detailed image that best represents the following article title: {text_promt}! 
    The image should be visually rich, vibrant, and immersive, capturing the essence of the topic with artistic depth. Use striking colors, dynamic composition, 
    and a sense of atmosphere to convey emotion and meaning. 
    Avoid using any text, letters, or numbers in the image – let the visuals speak for themselves.""",
    n=1)

    json_response = json.loads(result.model_dump_json())

    # Set the directory for the stored image
    image_dir = os.path.join(os.curdir, 'images')

    # If the directory doesn't exist, create it
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    # Initialize the image path (note the filetype should be png)
    image_path = os.path.join(image_dir, 'generated_image.png')

    # Retrieve the generated image
    image_url = json_response["data"][0]["url"]  # extract image URL from response
    generated_image = requests.get(image_url).content  # download the image
    with open(image_path, "wb") as image_file:
        image_file.write(generated_image)
    logger.info(f"Image saved to {image_path}")




def generate_ai_content():
    """
    Generates AI content based on the latest article from a specific URL.
    Returns the AI-generated text (answer_text) as a string.
    Returns None if no new article text is found or if the model doesn't respond.
    """
    client = AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=AZURE_ENDPOINT, 
        api_key=API_KEY
    )
    # Step 1) Prepare URL and JSON file
    url = "https://www.youreverydayai.com/episodes/"
    json_file = JSON_FILE_PATH

    # Fetch new article text
    new_article_text:str = orchestrate_flow(url, json_file=json_file)
    
    # If no new article text is found, return None
    if not new_article_text:
        return None

    # Build messages for the Azure OpenAI prompt
    messages = [
    {
        "role": "system",
        "content": (
            "Jsi zkušený a velmi vtipný český spisovatel s ostrým humorem a lehce satirickým stylem. "
            "Piš jako kombinace Karla Čapka a Douglase Adamse – chytře, svižně, s nadhledem. "
            "Potřebuji, abys odpovídal v čistém HTML formátu (používej např. <h2>, <p>, <ul>, <li>, ...). "
            "Nezapomeň, že si čtenáři mají z článku něco odnést – piš s přidanou hodnotou, používej analogie a příklady z reálného světa. "
            "Dostaneš vždy článek, který prostuduj a na jeho základě napiš, co se ve světě AI k dnešnímu dni asi děje. "
            "Buď originální a vyhýbej se generickým nadpisům jako 'Co se děje ve světě AI'. "
            "Místo toho piš názvy, které okamžitě zaujmou a jsou relevantní k obsahu článku a jsou krátké (maximálně 3 slova)."
        )
    },
    {
        "role": "user",
        "content": (
            f"Máš tady obsah nového článku ze stránky https://www.youreverydayai.com/ :\n\n"
            f"{new_article_text}\n\n"
            "Na základě tohoto článku napiš vtipný a zároveň informačně hodnotný text v češtině. "
            "Výstup musí být přesně v tomto HTML formátu:\n\n"
            "1) <h2> Nadpis shrnující hlavní myšlenku článku </h2>\n"
            "2) <p> Krátký úvod (max 3 věty) </p>\n"
            "3) <ul> 3-5 klíčových bodů o tom, co článek řeší, každý max 20 slov </ul>\n"
            "4) <p> Hlavní text článku (max 6 odstavců) </p>\n"
            "5) <p><i> Poznámka na závěr: Tento článek vytvořila AI a jedná se o humoristický obsah pouze pro studijní účely. </i></p>\n\n"
            "Humor by měl být lehce ironický, ale ne zlomyslný. "
            "Vyhýbej se frázím jako 'Umělá inteligence je fascinující' nebo 'Jak všichni víme'. "
            "Piš pro chytrého čtenáře, který se chce nejen pobavit, ale i něco se dozvědět."
        )
    }
]

    # Request completion from Azure OpenAI
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # For example, 'gpt-4' or 'gpt-35-turbo'
        messages=messages,
        temperature=0.7,
        max_tokens=4000
    )

    # Extract the AI-generated content (answer_text) if available
    if completion and completion.choices:
        answer_text = completion.choices[0].message.content
        # Split the text into lines, filter out lines containing only ``` or ```html, and join them back together
        answer_text = "\n".join(line for line in answer_text.splitlines() if line.strip() not in ("```", "```html"))
        title_match = re.search(r"<h2>(.*?)</h2>", answer_text, re.IGNORECASE)
        if title_match:
            generate_image(title_match.group(1))
        return answer_text
    else:
        return None





def main():
    """
    A main function that demonstrates usage of generate_ai_content().
    It loggs the AI-generated text to stdout for quick testing.
    """
    answer = generate_ai_content()
    
    if answer:
        logger.info("\n===== AI-Generated HTML Article =====\n")
        logger.debug(answer)
    else:
        logger.info("No AI content generated or no new article available.")




if __name__ == "__main__":
    main()
