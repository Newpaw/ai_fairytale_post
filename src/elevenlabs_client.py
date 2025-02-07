import os
import uuid
import random
from elevenlabs.client import ElevenLabs
from config import ELEVENLABS_API_KEY
from logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)


def generate_audio(text: str, model_id: str = "eleven_flash_v2_5") -> str:
    """
    Vygeneruje audio z textu pomocí ElevenLabs API, uloží ho s náhodným názvem (UUID)
    a vrátí absolutní cestu k souboru.
    """
    voice_dict = {"Klára": "5dDTFgDe7eMVxZHZObuz", "Jan": "Eqzdg80VS88UO6BmC97d"}

    selected_name, voice_id = random.choice(list(voice_dict.items()))
    logger.info(f"Vybrán: {selected_name} s voice ID: {voice_id}")
    audio_generator = client.text_to_speech.convert(
        voice_id=voice_id,
        output_format="mp3_44100_128",
        text=text,
        model_id=model_id,
    )

    # Uložíme audio do složky "audio_files" ve stejném adresáři jako tento skript
    audio_dir = os.path.join(BASE_DIR, "audio_files")
    os.makedirs(audio_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(audio_dir, filename)

    with open(file_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)
    return file_path


if __name__ == "__main__":
    sample_text = "Ahoj, jak se máš?"
    audio_path = generate_audio(sample_text)
    print(f"Audio file saved at: {audio_path}")
