from abc import ABC, abstractmethod
from typing import List

from conf.secrets import OPENAI_API_KEY, ORG_ID
from conf.constant import constant_config
from openai import OpenAI
import json


class LLM(ABC):
    @abstractmethod
    def __init__(self, model_name: str):
        pass

    @abstractmethod
    def invoke(self, messages: List):
        pass


class OpenAILLM(LLM):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.llm = OpenAI(
            api_key=OPENAI_API_KEY,
            organization=ORG_ID,
            timeout=300,
            max_retries=3,
        )

    def invoke(self, messages: List) -> str:

        result = self.llm.chat.completions.create(
            model=self.model_name,
            response_format={"type": "json_object"},
            temperature=0,
            messages=messages,
        )

        result_json = json.loads(result.to_dict()["choices"][0]["message"]["content"])

        input_token  = result.usage.prompt_tokens
        output_token = result.usage.completion_tokens

        input_cost  = (constant_config.get("pricing").get("input").get(self.model_name) * input_token)/1000000
        output_cost = (constant_config.get("pricing").get("output").get(self.model_name) * output_token)/1000000

        total_cost        = input_cost + output_cost
        cost_per_question = total_cost/float(result_json["total_questions"])


        result_json["input_token"]  = input_token
        result_json["output_token"] = output_token

        result_json["input_cost"]  = input_cost
        result_json["output_cost"] = output_cost

        result_json["total_cost"]        = total_cost
        result_json["cost_per_question"] = cost_per_question

        return result_json
