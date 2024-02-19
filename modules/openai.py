import logging
from typing import Dict, List
from domain.gpt_chat_response import GPTChatResponse, gpt_chat_response_from_dict
from domain.response import Response, response_from_dict
from configparser import ConfigParser
import openai
import os

from utils.async_tools import asAsync
from utils.logger import AppLogger


class OpenAiHandler:
    def __init__(self, key: str) -> None:
        self._key = key
        self.logger = AppLogger().logger
        config = ConfigParser()
        config.read("config.ini")
        self.model = config["SETTINGS"]["open_ai_model"]

    @asAsync
    def query(self, prompt: str) -> Response:
        self.logger.log(logging.INFO, f"Using ChatGPT, querying: {prompt}")
        openai.api_key = self._key
        response = openai.Completion.create(
            model="text-davinci-003", prompt=prompt, temperature=0.8, max_tokens=1000
        )
        return response_from_dict(response)

    @asAsync
    def chat(self, current_messages: List[Dict[str, str]]) -> GPTChatResponse:
        self.logger.info(f"Current Messages: {len(current_messages)}")
        system_role = {
            "role": "system",
            "content": 'Você agora é conhecido como: EVA 01, uma unidade Mecha de combate descrita no Anime Evangelion. A Unidade Eva 01 foi produzido em 2004 pelo Terceiro Anexo de Laboratórios de Evolução Artificial da antiga Gehirn, em Hakone, como um modelo "Evangelion Test Type".',
        }
        openai.api_key = self._key
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                system_role,
                *current_messages,
            ],
        )
        return gpt_chat_response_from_dict(response)
