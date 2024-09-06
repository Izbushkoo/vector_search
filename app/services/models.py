from enum import Enum
from typing import Any, Union, Type

from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.pydantic_v1 import BaseModel
from langchain.llms import OpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains.openai_functions import create_structured_output_chain

from app.core.config import settings


class ModelName(str, Enum):
    g3i = "gpt-3.5-turbo-instruct"
    g3ch = "gpt-3.5-turbo"
    g3ch16 = "gpt-3.5-turbo-16k"
    g4 = "gpt-4"
    g4_o = "gpt-4o"
    g4_prev = "gpt-4-1106-preview"
    g4_turbo = "gpt-4-0125-preview"
    g4_turbo_04 = "gpt-4-turbo-2024-04-09"
    embed = "embed"


class ModelSelector:

    def __init__(self, api_key: str):
        self._api_key = api_key

    def __call__(self, model: ModelName, temperature: Union[int, float] = 0, **kwargs):
        if model == ModelName.embed:
            return OpenAIEmbeddings(openai_api_key=self._api_key, **kwargs)
        elif model == ModelName.g3i:
            return OpenAI(openai_api_key=self._api_key, temperature=temperature, **kwargs)
        else:
            return ChatOpenAI(openai_api_key=self._api_key, model_name=model, temperature=temperature, **kwargs)

    def get_structured_chain(self, form_model: Type[BaseModel], model_name: Type[ModelName] = ModelName.g3ch,
                             temperature: Union[float, int] = 0, **kwargs):

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a world class algorithm for extracting information in structured formats."),
            ("human", "Use the given format to extract information from the following text: {input}"),
            ("human", "Tip: Make sure to answer in the correct format and all properties encolsed in double quotes"),
        ])
        model = ChatOpenAI(openai_api_key=self._api_key, model=model_name, temperature=temperature, **kwargs)
        return create_structured_output_chain(form_model, model, prompt)


model_selector = ModelSelector(api_key=settings.OPENAI_API_KEY)
