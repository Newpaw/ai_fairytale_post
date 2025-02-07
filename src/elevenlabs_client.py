import os
import uuid
from elevenlabs.client import ElevenLabs
from config import ELEVENLABS_API_KEY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

def generate_audio(text: str) -> str:
    """
    Vygeneruje audio z textu pomocí ElevenLabs API, uloží ho s náhodným názvem (UUID)
    a vrátí absolutní cestu k souboru.
    """
    audio_generator = client.text_to_speech.convert(
        voice_id="Eqzdg80VS88UO6BmC97d",
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_flash_v2_5",
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
