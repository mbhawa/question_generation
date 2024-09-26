from langchain_core.globals import set_debug

from conf.documents import ParsedData
from langchain_core.documents import Document
from loguru import logger

set_debug(True)
import datetime
import json

# import json
from typing import Dict, List

from conf.constant import constant_config

# import pandas as pd
from conf.documents import ParsedData
from conf.prompts import HUMAN_MESSAGE_TEMPLATE, SYSTEM_MESSAGE
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .utils import get_llm, number_of_questions_per_chunk
from .utils import save_query_and_user_data


def generate_questions(
    user_id: str,
    input_type: str,
    input_name: str,
    query_id: str,

    model_name: str,
    parsed_data: Dict,
    solo_taxonomy: List,
    question_type: str,
    total_questions: int,
    selected_topics: str,
) -> Dict:

    if parsed_data:
        text_for_selected_topics = []

        for topic in parsed_data["topic_paragraph"]:
            if topic in selected_topics:
                text_for_selected_topics.append(parsed_data["topic_paragraph"][topic])
                logger.info(f"{parsed_data['topic_paragraph'][topic][:50]}\n\n")
                logger.info("*"*50)


        topic_list = []
        chunk_list = []



        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=constant_config.get("chunk_size"),
            chunk_overlap=constant_config.get("chunk_overlap"),
        )

        for selected_topic, text in zip(selected_topics, text_for_selected_topics):
            documents = text_splitter.split_text(text)
            for doc in documents:
                topic_list.append(selected_topic)
                chunk_list.append(doc)
                logger.info(f"selected_topic: {selected_topic}")
                logger.info(f"doc: {doc[:50]}")

        logger.info(f"Length of chunk_list = {len(chunk_list)}")
        logger.info(f"topic= {selected_topic}")
        logger.info(f"Length of topic list= {len(topic_list)}")

        questions_per_chunk = number_of_questions_per_chunk(
            chunks=len(chunk_list), total_questions=total_questions
        )

        logger.info(f"questions_per_chunk = {questions_per_chunk}")

        # logger.info(f"documents length : {len(documents)}")

        complete_results_json = []
        for i, (chunk, n_questions) in enumerate(zip(chunk_list, questions_per_chunk)):

            logger.info("#"*50)
            logger.info(f"{i}")
            logger.info("*"*50)
            logger.info(f"n_questions = {n_questions}")

            if n_questions == 0:
                break
            context = chunk
            HUMAN_MESSAGE = HUMAN_MESSAGE_TEMPLATE.format(
                solo_taxonomy=solo_taxonomy,
                question_types=question_type,
                context=context,
                n_questions=n_questions,
            )

            logger.info(f"HUMAN_MESSAGE = {HUMAN_MESSAGE}")
            logger.info(f"SYSTEM_MESSAGE = {SYSTEM_MESSAGE}")

            messages = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": HUMAN_MESSAGE},
            ]
            llm = get_llm(model_name)
            result = llm.invoke(messages=messages)

            logger.info("result.content\n", result)

            # result_json = json.loads(result)
            result_json = result
            result_json["context_window"] = context
            result_json["topic"] = topic_list[i]
            complete_results_json.append(result_json)

        time_of_generation = datetime.datetime.now().isoformat()
        result_json["time_of_generation"] = time_of_generation
        result_json["model_name"] = model_name



        save_query_and_user_data(
                        user_id=user_id,
                        query_id=query_id,
                        model=model_name,
                        input_type=input_type,
                        input_name=input_name,
                        parsed_data=parsed_data,
                        selected_topics=selected_topics,
                        question_type=question_type,
                        solo_taxonomy_types=solo_taxonomy,
                        generated_questions=complete_results_json,
                    )

        # logger.info(f"complete_results_json = {complete_results_json}")

        return complete_results_json

    else:
        return {
            "Error": "Invalid SHA key provided! This data does not exist in the database."
        }
