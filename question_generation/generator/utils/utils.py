from typing import Dict, List

import numpy as np
from conf.documents import ParsedData, QueryData, UserData
from loguru import logger

from .llm import LLM, OpenAILLM


def get_llm(model_name: str) -> LLM:

    if model_name.startswith("gpt"):
        return OpenAILLM(model_name)
    else:
        raise ValueError(f"Invalid model name {model_name}")


def save_query_and_user_data(
    user_id: str,
    query_id: str,
    model: str,
    input_type: str,
    input_name: str,
    parsed_data: ParsedData,
    selected_topics: List,
    question_type: str,
    solo_taxonomy_types: List,
    generated_questions: Dict,
):
    query = QueryData.objects.safe_get(query_id=query_id)

    if query:
        query.question_types.append(question_type)
        for question in generated_questions:
            query.generated_questions.append(question)
        query.save()
    else:
        query = QueryData(
            query_id=query_id,
            model=model,
            input_type=input_type,
            input_name=input_name,
            SHA_id=parsed_data,
            selected_topics=selected_topics,
            question_types=[question_type],
            solo_taxonomy_types=solo_taxonomy_types,
            generated_questions=generated_questions,
        )
        query.save()

    user = UserData.objects.safe_get(user_id=user_id)

    if user:
        if query not in user.query_ids:
            user.query_ids.append(query)
            user.save()
    else:
        user = UserData(user_id=user_id, query_ids=[query])
        user.save()


def number_of_questions_per_chunk(chunks: int, total_questions: int) -> List[int]:
    """
    Args:
        chunks = total number of chunks (int)
        total_questions = total question to be generated (int)

    Return:
    it retuns list of integers that corresponds to
    the number of quesions to be generated from each chunk

    """
    questions_per_chunk = []
    if total_questions <= chunks:
        for chunk in range(chunks):
            if np.sum(questions_per_chunk) >= total_questions:
                questions_per_chunk.append(0)
            else:
                questions_per_chunk.append(1)

        return questions_per_chunk

    elif total_questions > chunks:
        append_value = int(total_questions / chunks)
        for chunk in range(chunks):
            questions_per_chunk.append(append_value)

        for chunk in range(chunks):
            if np.sum(questions_per_chunk) == total_questions:
                break
            questions_per_chunk[chunk] = questions_per_chunk[chunk] + 1

        return questions_per_chunk


def save_feedback(query_id: str, user_feedback: int):
    # feedback = FeedbackData.objects.safe_get(query_id=query_id)

    query = QueryData.objects.safe_get(query_id=query_id)

    if query:
        query.user_feedback = user_feedback
        query.save()


    # if feedback:
    #     feedback.user_feedback = user_feedback
    #     feedback.save()

    # else:
    #     feedback = FeedbackData(query_id=query_id, user_feedback=user_feedback)
    #     feedback.save()
