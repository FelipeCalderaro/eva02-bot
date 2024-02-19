import random
from google.cloud import texttospeech
from utils.async_tools import asAsync
import whisper

from utils.logger import AppLogger


class SpeechHandler:
    """
    Utils class with functions to handle speech-to-text and text-to-speech
    """

    _PROJECT_ID = "diesel-patrol-375922"
    _GOOGLE_APPLICATION_CREDENTIALS = "text-to-speech-key.json"

    _LANGUAGE_CODE = "ja-JP"
    _VOICES = ["ja-JP-Neural2-B", "ja-JP-Neural2-C", "ja-JP-Neural2-D"]

    def __init__(self) -> None:
        self.logger = AppLogger().logger

        self._registerENV()

        self._client = texttospeech.TextToSpeechClient()
        self._voice = texttospeech.VoiceSelectionParams(
            language_code=self._LANGUAGE_CODE,
            name=self._VOICES[random.randint(0, len(self._VOICES) - 1)],
        )
        self._audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            effects_profile_id=["headphone-class-device"],
        )

    def _registerENV(self):
        from os import environ

        self.logger.info("Registering credential keys")
        environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._GOOGLE_APPLICATION_CREDENTIALS
        environ["PROJECT_ID"] = self._PROJECT_ID
        self.logger.info("Credentials registered")

    @asAsync
    def convertTextToSpeech(self, text: str) -> None:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=self._voice,
            audio_config=self._audio_config,
        )
        with open("tts.mp3", "wb") as file:
            file.write(response.audio_content)
