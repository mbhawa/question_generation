import traceback
from http import HTTPStatus

import openai
from conf.documents import ParsedData
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from loguru import logger

from .forms import FeedbackInputForm, GeneratorInputForm
from .utils.generate import generate_questions
from .utils.tasks import generate_questions_task
from .utils.utils import save_feedback, save_query_and_user_data
from celery.result import AsyncResult


@csrf_exempt
def generator_input_view(request):
    if request.method == "POST":
        form = GeneratorInputForm(request.POST)
        if form.is_valid():
            logger.info("Form Validated!!")
            user_id = form.cleaned_data["user_id"]
            input_type = form.cleaned_data["input_type"]
            input_name = form.cleaned_data["input_name"]
            model_name = form.cleaned_data["model_name"]
            solo_taxonomy = form.cleaned_data["solo_taxonomy"]
            question_type = form.cleaned_data["question_types"]
            data_sha_key = form.cleaned_data["data_sha_key"]
            number_of_questions = form.cleaned_data["number_of_questions"]
            query_id = form.cleaned_data["query_id"]
            selected_topics = form.cleaned_data["selected_topics"].split("#$%")
            logger.info(
                f"Received question type: {question_type} of type {type(question_type)}"
            )
            parsed_data = ParsedData.objects.safe_get(SHA_id=data_sha_key)
            if not parsed_data:
                return JsonResponse(
                    {
                        "Error": "Invalid SHA key provided! This data does not exist in the database."
                    }
                )
            try:
                # logger.info(f"parsed_data = {parsed_data.to_dict()}")
                # logger.info(type(parsed_data.to_dict()))
                # logger.info(dir(parsed_data.to_dict()))




                task = generate_questions_task.delay(
                    user_id=user_id,
                    input_type=input_type,
                    input_name=input_name,
                    query_id=query_id,
                    model_name=model_name,
                    parsed_data=parsed_data.to_dict(),
                    solo_taxonomy=solo_taxonomy,
                    question_type=question_type,
                    total_questions=number_of_questions,
                    selected_topics=selected_topics,
                )

                logger.info(f"Task ID: {task.id}")
                return JsonResponse({"task_id": task.id})


                # logger.info(f"Generated Questions: {generated_questions}")
                # logger.info(f"Type of Generated Questions: {type(generated_questions)}")
                # logger.info(
                #     f"Length of Generated Questions: {len(generated_questions)}"
                # )
                # logger.info(
                #     f"Length of Generated Questions [0]: {type(generated_questions[0])}"
                # )
            except Exception as e:
                # if isinstance(e, openai.APITimeoutError):
                #     return JsonResponse(
                #         {
                #             "Error": "Your request has been timed out. Please try again",
                #             "status_code": HTTPStatus.REQUEST_TIMEOUT,
                #         }
                #     )

                return JsonResponse(
                    {
                        "Error": f"Could not generate questions due to: {traceback.format_exc()}"
                    }
                )

            # if generated_questions:
            #     save_query_and_user_data(
            #         user_id=user_id,
            #         query_id=query_id,
            #         model=model_name,
            #         input_type=input_type,
            #         input_name=input_name,
            #         parsed_data=parsed_data,
            #         selected_topics=selected_topics,
            #         question_type=question_type,
            #         solo_taxonomy_types=solo_taxonomy,
            #         generated_questions=generated_questions,
            #     )

            #     return JsonResponse({"generated_questions": generated_questions})
            # else:
            #     return JsonResponse(
            #         {"Error": "Failed to generate questions. Please try again."}
            #     )
        else:
            logger.info("Received a Bad Request")
            return HttpResponseBadRequest("Invalid form data")

    else:
        form = GeneratorInputForm()

    return render(request, "generator_input_form.html", {"form": form})


@csrf_exempt
def feedback_view(request):
    if request.method == "POST":
        form = FeedbackInputForm(request.POST)
        if form.is_valid():
            logger.info("Form Validated")
            query_id = form.cleaned_data["query_id"]
            user_feedback = form.cleaned_data["user_feedback"]
            save_feedback(query_id=query_id, user_feedback=user_feedback)
            return JsonResponse({"Query ID": query_id, "Feedback": user_feedback})
    else:
        logger.info("Received a Bad Request")
        form = FeedbackInputForm()

    return render(request, "feedback_form.html", {"form": form})



@csrf_exempt
def task_status_view(request, task_id):
    task_result = AsyncResult(task_id)
    if task_result.state == 'PENDING':
        response = {
            'state': task_result.state,
            'status': 'Pending...'
        }
    elif task_result.state != 'FAILURE':
        response = {
            'state': task_result.state,
            'result': task_result.result
        }
        # if task_result.state == 'SUCCESS':
        #     # Save the generated questions if needed
        #     generated_questions = task_result.result

        #     logger.info(f"generated_questions = {generated_questions}")

        #     # save_query_and_user_data(
        #     #     user_id=generated_questions['user_id'],
        #     #     query_id=generated_questions['query_id'],
        #     #     model=generated_questions['model_name'],
        #     #     input_type=generated_questions['input_type'],
        #     #     input_name=generated_questions['input_name'],
        #     #     parsed_data=generated_questions['parsed_data'],
        #     #     selected_topics=generated_questions['selected_topics'],
        #     #     question_type=generated_questions['question_type'],
        #     #     solo_taxonomy_types=generated_questions['solo_taxonomy'],
        #     #     generated_questions=generated_questions,
        #     # )


    else:
        response = {
            'state': task_result.state,
            'status': str(task_result.info),  # this is the exception raised
        }

    return JsonResponse(response)