import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Union
from conf.constant import constant_config

import datetime
import time
import pandas as pd
import numpy as np
import requests
import streamlit as st
from loguru import logger
from collections import Counter



import tempfile
from conf.secrets import SLACK_BOT_TOKEN , PRIVATE_CHANNEL_ID

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def initialize_state():
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()

    if "df_questions" not in st.session_state:
        st.session_state.df_questions = pd.DataFrame(columns=[
                                                              "question",
                                                              "option_a", 
                                                              "option_b", 
                                                              "option_c", 
                                                              "option_d", 
                                                              "correct_option", 
                                                              "correct_option_explanation", 
                                                              "solo_category", 
                                                              "question_type"
                                                              ]
                                                    )

    if "parsed_output" not in st.session_state:
        st.session_state.parsed_output = {"Error": "Document not parsed yet"}

    if "feedback_disabled" not in st.session_state:
        st.session_state.feedback_disabled = True

    if "query_id" not in st.session_state:
        st.session_state.query_id = None

    if "slack_client" not in st.session_state:
        st.session_state.slack_client = WebClient(token=SLACK_BOT_TOKEN)


    if "parser_button" not in st.session_state:
        st.session_state.parser_button = None
    if "fifty_perc_topics" not in st.session_state:
        st.session_state.fifty_perc_topics = {"Error": "max_frequency_topics not calculated yet"}
    if "selected_rows" not in st.session_state:
        st.session_state.selected_rows = {"Error": "row not selected yet"}
    if "selection" not in st.session_state:
        st.session_state.selection = {"Error": "empty selected rows"}
    if "topic_selection" not in st.session_state:
        st.session_state.topic_selection = None
    if "sub_topic" not in st.session_state:
        st.session_state.sub_topic = None
    if "unselected_rows" not in st.session_state:
        st.session_state.unselected_rows = {"Error": "row not selected yet"}

# DAtaframe with selection
def dataframe_with_selections(df):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop("Select", axis=1)



def dataframe_with_selection_options(selected_df, unselected_df):
    df_with_selections = selected_df.copy()
    df_without_selections = unselected_df.copy()
    df_with_selections.insert(0, "Select", True)
    df_without_selections.insert(0, "Select", False)
    df_join= pd.concat([df_with_selections, df_without_selections], axis=0)
    edited_df = st.data_editor(
        df_join,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)}
        
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop("Select", axis=1)


# Function to handle pdf upload
def upload_pdf():
    uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"])

    if uploaded_file is not None:

        return uploaded_file


# Function to handle pdf upload
def upload_media():
    uploaded_file = st.file_uploader("Upload Media file")

    class UplodedFile:
        def __init__(self, name):
            self.name = name

    if uploaded_file is not None:

        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getvalue())

        return UplodedFile(uploaded_file.name)


# Function to handle URL input
def input_url():
    url = st.text_input(
        "Enter URL",
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
    )

    class URLText:
        def __init__(self, url):
            self.name = url
            self.text = url

    return URLText(url)


# Function to get user id input
def input_user_id():
    user_id = st.text_input(
        "Enter User Name",
        "",
    )
    return user_id


# Function to handle text input
def input_text():
    text = st.text_area(
        "Enter Text",
        """Title: The Taj Mahal: A Testament to Love and Architectural Splendor
Introduction:
The Taj Mahal stands as a shimmering jewel in the crown of India’s architectural heritage, a testament to timeless love and exquisite craftsmanship. Situated in the city of Agra, on the banks of the Yamuna River, this mausoleum captivates millions of visitors from around the globe each year. Built by the Mughal Emperor Shah Jahan in memory of his beloved wife Mumtaz Mahal, the Taj Mahal represents the pinnacle of Mughal architecture and stands as a symbol of eternal love and devotion.""",
    )

    min_char = constant_config.get("min_text_length")
    max_char = constant_config.get("max_text_length")

    if len(text) <= min_char:
        st.write(f"Please Enter text more than {min_char} characters")
    elif len(text) >= max_char:
        st.write(f"Please Enter text less than {max_char} characters")


    class PlainText:
        def __init__(self, name, text):
            self.name = name
            self.text = text

    return PlainText(" ".join(text.split(" ")[:5]), text)


# Function to handle pdf upload
def upload_document():
    uploaded_file = st.file_uploader("Upload Doc file")

    if uploaded_file is not None:

        return uploaded_file


def hit_parser_api(
    user_id: str, end_point: str, input_type: str, input_data: Union[str, bytes]
):

    # django_parser_url = "http://localhost:8070"  # os.getenv("DJANGO_API_URL", default="http://localhost:8070")
    django_parser_url = "https://questiongeneration-7z5edbs8b6mndukev8lwny.streamlit.app"

    base_url = django_parser_url
    url = base_url + end_point

    if input_type == "PDF Upload":
        # Define the data to be sents
        data = {
            "user_id": user_id,  # Replace with actual user_id
        }
        # Define the file to be sent
        files = {"file": io.BufferedReader(input_data)}
        response = requests.post(url, data=data, files=files)

    elif input_type == "Text":
        data = {
            "user_id": user_id,
            "text": input_data.text,
        }  # Replace with actual user_id
        response = requests.post(url, data=data)

    elif input_type == "URL":
        data = {
            "user_id": user_id,
            "url": input_data.text,
        }  # Replace with actual user_id
        response = requests.post(url, data=data)

    elif input_type == "Media":
        data = {
            "user_id": user_id,  # Replace with actual user_id
        }
        with open(input_data.name, "rb") as f:
            files = {"file": f}
            response = requests.post(url, data=data, files=files)
        os.remove(input_data.name)

    elif input_type == "Document":
        data = {
            "user_id": user_id,
        }
        files = {"file": io.BufferedReader(input_data)}
        response = requests.post(url, data=data, files=files)

    else:
        logger.error("input_type not provided")
    # st.write(response.text)

    return json.loads(response.text)


def hit_generator_api(
    user_id: str,
    input_type: str,
    input_name: str,
    query_id: str,
    sha_key: str,
    model_name: str,
    solo_taxonomy: List,
    question_type: str,
    number_of_questions: int,
    selected_topics: List,
):

    url = "https://questiongeneration-7z5edbs8b6mndukev8lwny.streamlit.app/api/v1/generator/"

    # if input_type == "PDF Upload":
    #     # Define the data to be sent
    data = {
        "user_id": user_id,  # Replace with actual user_id
        "input_type": input_type,
        "input_name": input_name,
        "query_id": str(query_id),
        "data_sha_key": sha_key,
        "model_name": model_name,
        "solo_taxonomy": solo_taxonomy,
        "question_types": question_type,
        "number_of_questions": number_of_questions,
        "selected_topics": "#$%".join(selected_topics),
    }
    response = requests.post(url, data=data)

    return json.loads(response.text)






def get_uploader_and_endpoint(input_type: str):

    if input_type == "PDF Upload":
        input_data = upload_pdf
        parser_end_point = "/api/v1/data_loader/pdf/"
    elif input_type == "URL":
        input_data = input_url
        parser_end_point = "/api/v1/data_loader/url/"
    elif input_type == "Text":
        input_data = input_text
        parser_end_point = "/api/v1/data_loader/text/"
    elif input_type == "Media":
        input_data = upload_media
        parser_end_point = "/api/v1/data_loader/media/"
    elif input_type == "Document":
        input_data = upload_document
        parser_end_point = "/api/v1/data_loader/doc/"

    return input_data, parser_end_point


def hit_feedback_api(query_id: str, user_feedback: int):

    url = "https://questiongeneration-7z5edbs8b6mndukev8lwny.streamlit.app/api/v1/generator/feedback/"

    data = {
        "query_id": str(query_id),
        "user_feedback": user_feedback,
    }
    response = requests.post(url, data=data)
    print(response)
    return json.loads(response.text)


def get_task_status(task_id: str):
    url = "https://questiongeneration-7z5edbs8b6mndukev8lwny.streamlit.app/api/v1/generator/task-status/"

    response = requests.post(url + task_id + "/")
    # print(response)
    return json.loads(response.text)


def get_questions_df(questions_list: List, cost_per_question: float):
    # Convert the questions list into a DataFrame
    df_questions = pd.DataFrame(questions_list)
    df_questions["cost"] = cost_per_question
    # logger.info(f"cost_per_question type = {type(cost_per_question)}")
    # # Split the options into separate columns
    # df_questions = df_questions.join(df_questions['options'].apply(pd.Series))

    # # Drop the original options column
    # df_questions.drop(columns=['options'], inplace=True)

    # # Take only the maximum number of columns
    # max_cols = max([len(x) for x in df_questions.columns])
    # df_questions = df_questions.iloc[:, :max_cols]


    # Extract options into separate columns
    options_cols = ["option_a", "option_b", "option_c", "option_d"]
    logger.info(f"options :  {df_questions['options'][0]}")
    for i, option in enumerate(options_cols):
        df_questions[option] = df_questions["options"].apply(lambda x: x.get(option,np.nan))

    # Drop the "options" column
    df_questions.drop("options", axis=1, inplace=True)



    # Reorder the columns
    df_questions = df_questions[[
                                "question",
                                "option_a", 
                                "option_b", 
                                "option_c", 
                                "option_d", 
                                "correct_option", 
                                "correct_option_explanation", 
                                "solo_category", 
                                "question_type",
                                "cost"
                                ]]

    # Print the DataFrame
    # df_questions

    return df_questions



def question_gen_parallel_task(
                                user_id,
                                input_type,
                                input_name,
                                query_id,
                                sha_key,
                                model_name,
                                solo_taxonomy,
                                question_type,
                                number_of_questions,
                                selected_topics,
                                
                                ):

    st.write(f"submitted {question_type}")

    generated_questions_task_id = hit_generator_api(
        user_id=user_id,
        input_type=input_type,
        input_name=input_name,
        query_id=query_id,
        sha_key=sha_key,
        model_name=model_name,
        solo_taxonomy=solo_taxonomy,
        question_type=question_type,
        number_of_questions=number_of_questions,
        selected_topics=selected_topics,
    )

    # st.write(generated_questions_task_id)
    task_id = generated_questions_task_id["task_id"]
    # switch to celery signals
    while get_task_status(task_id)["state"] not in ["FAILURE","SUCCESS"]: # RETRY can be added
        time.sleep(1)
    # st.write(get_task_status(task_id))

    task_status = get_task_status(task_id)


    if task_status["state"] == "SUCCESS":
        # st.write(task_status["result"])
        # generated_questions_list.append(task_status["result"])

            
        return task_status["result"]

    else:
        return {
                "solo_taxonomy":solo_taxonomy,
                "question_type":question_type,
                "task_id":task_id
                }



def send_slack_notification(user_id,input_type,input_data,model_name,solo_levels,question_types,total_questions_per_question_type,selection):

    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            # Save the DataFrame to the CSV file
            st.session_state.df_questions.to_csv(tmp.name, index=False)
            current_time = datetime.datetime.now() + datetime.timedelta(hours=5,minutes=30)
            # Upload the file to Slack
            response = st.session_state.slack_client.files_upload_v2(
                channels=PRIVATE_CHANNEL_ID,
                file=tmp.name,
                title="Generated Questions",
                initial_comment=f"Here is the CSV file for generated questions at {current_time}"
            )
            assert response["ok"]
            file_url = response['file']['permalink']
            print("File uploaded successfully")


            # Send a message with a text block and attach the file URL
            message_response = st.session_state.slack_client.chat_postMessage(
                channel=PRIVATE_CHANNEL_ID,
                blocks=[

                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":speech_balloon:Question Generated",
                            "emoji": True
                        }
                    },

                    {
                        "type": "divider"
                    },

                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*User Id:*\n{user_id}"},
                            {"type": "mrkdwn", "text": f"*Input type:*\n{input_type}"},
                            {"type": "mrkdwn", "text": f"*Input data name:*\n{input_data.name}"},
                            {"type": "mrkdwn", "text": f"*Query id:*\n{st.session_state.query_id}"},
                            {"type": "mrkdwn", "text": f"*Document Id:*\n{st.session_state.parsed_output['sha_key']}"},
                            {"type": "mrkdwn", "text": f"*Model name:*\n{model_name}"},
                            {"type": "mrkdwn", "text": f"*Solo levels:*\n{solo_levels}"},
                            {"type": "mrkdwn", "text": f"*Question type:*\n{question_types}"},
                            {"type": "mrkdwn", "text": f"*Number of questions per question type:*\n{total_questions_per_question_type}"},
                            {"type": "mrkdwn", "text": f"*Selected topics:*\n{selection['topic'].to_list()}"},

                        ]
                    },


                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Here is the DataFrame as a CSV file: <{file_url}|Download CSV>"
                        }
                    }
                ]
            )
            assert message_response["ok"]
            print("Message with file attachment sent successfully")



    except SlackApiError as e:
        print(f"Error uploading file: {e.response['error']}")




def send_slack_feedback_notification(user_id,query_id,feedback):

    try:

        # current_time = datetime.datetime.now() + datetime.timedelta(hours=5,minutes=30)

        # Send a message with a text block and attach the file URL

        if feedback == 1:

            message_response = st.session_state.slack_client.chat_postMessage(
                channel=PRIVATE_CHANNEL_ID,
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":thumbsup:Feedback",
                            "emoji": True
                        }
                    },

                    {
                        "type": "divider"
                    },

                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*User Id:*\n{user_id}"},
                            {"type": "mrkdwn", "text": f"*Query Id:*\n{query_id}"},
                            {"type": "mrkdwn", "text": f"*Feedback:*\n{feedback}"},

                        ]
                    },

                ]
            )
            assert message_response["ok"]
            logger.info("Feedback sent sucessfully")


        else:

            message_response = st.session_state.slack_client.chat_postMessage(
                channel=PRIVATE_CHANNEL_ID,
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f":thumbsdown:Feedback",
                            "emoji": True
                        }
                    },

                    {
                        "type": "divider"
                    },

                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*User Id:*\n{user_id}"},
                            {"type": "mrkdwn", "text": f"*Query Id:*\n{query_id}"},
                            {"type": "mrkdwn", "text": f"*Feedback:*\n{feedback}"},

                        ]
                    },

                ]
            )
            assert message_response["ok"]
            logger.info("Feedback sent sucessfully")

    except SlackApiError as e:
        print(f"Error sending feedback: {e.response['error']}")
    


def keyword_counts(dict : dict):
    """
    takes idctionary and return count of keywords in dictionary
    input = dict

    output = dict and list
    """
    # getting all topics in a list
    topic_list  = list(dict.keys())
    # making list of all elements because it was list of list
    all_elements =[j for i in topic_list for j in i.split(',')]
    topic_count_dict = Counter(all_elements)
    return (topic_count_dict,topic_list)
