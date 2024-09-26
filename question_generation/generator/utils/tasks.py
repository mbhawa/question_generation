# question_generation/generator/utils/tasks.py

from celery import shared_task
from .generate import generate_questions
# from .utils import save_query_and_user_data



@shared_task
def generate_questions_task(user_id,
                            input_type,
                            input_name,
                            query_id,
                            model_name,
                            parsed_data,
                            solo_taxonomy,
                            question_type,
                            total_questions,
                            selected_topics):



    generated_questions = generate_questions(user_id=user_id,
                                            input_type=input_type,
                                            input_name=input_name,
                                            query_id=query_id,
                                            model_name=model_name,
                                            parsed_data=parsed_data,
                                            solo_taxonomy=solo_taxonomy,
                                            question_type=question_type,
                                            total_questions=total_questions,
                                            selected_topics=selected_topics
                                        )

    # save_query_and_user_data(
    #                 user_id=user_id,
    #                 query_id=query_id,
    #                 model=model_name,
    #                 input_type=input_type,
    #                 input_name=input_name,
    #                 parsed_data=parsed_data,
    #                 selected_topics=selected_topics,
    #                 question_type=question_type,
    #                 solo_taxonomy_types=solo_taxonomy,
    #                 generated_questions=generated_questions,
    #             )

    return generated_questions