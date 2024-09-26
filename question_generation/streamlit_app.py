import json
import time
import traceback
import uuid
from io import BytesIO

import datetime
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import streamlit as st
from stqdm import stqdm
from conf.constant import constant_config
from conf.prompts import prompts_config
from conf.secrets import SLACK_BOT_TOKEN , PRIVATE_CHANNEL_ID
from loguru import logger
from streamlit_utils.utils import (
    dataframe_with_selections,
    get_uploader_and_endpoint,
    hit_feedback_api,
    hit_generator_api,
    hit_parser_api,
    initialize_state,
    input_user_id,
    get_task_status,
    get_questions_df,
    question_gen_parallel_task,
    send_slack_notification,
    keyword_counts,
    send_slack_feedback_notification
)

import tempfile
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# from conf.documents import ParsedData

# from generator.utils.utils import save_query_and_user_data


# Main function to run the app
def main():
    initialize_state()
    # Title of the app
    st.title("Question Generator App")
    user_id = input_user_id()

    # Dropdown menu to select input type
    input_type = st.selectbox(
        "Select Input Type", ["PDF Upload", "URL", "Text", "Media", "Document"]
    )

    # Input handling based on selection
    uploader, parser_end_point = get_uploader_and_endpoint(input_type=input_type)
    input_data = uploader()
    st.session_state.parser_button = st.button("Parse", disabled=False)

    if st.session_state.parser_button:

        if user_id == "":
            st.error("Please enter your name")
           

        if (input_type == "Text"):
            min_char = constant_config.get("min_text_length")
            max_char = constant_config.get("max_text_length")
            if len(input_data.text) <= min_char:
                error_message = f"Text size is less than {min_char} characters, Try again with more characters"
                st.error(error_message)
                raise(error_message)
            
            elif len(input_data.text) >= max_char:
                error_message = f"Text size is more than {max_char} characters, Try again with less characters"
                st.error(error_message)
                raise(error_message)
            

        with st.spinner("Parsing Document..."):
            try:

                st.session_state.parsed_output = hit_parser_api(
                    user_id, parser_end_point, input_type, input_data
                )

                logger.info(f"st.session_state.parsed_output {st.session_state.parsed_output}")



                # counter of all topics values stored in dict {'topic1':3, 'topic2':2}
                topic_count_dict, topic_list = keyword_counts(st.session_state.parsed_output['para_dict'])
                # cleaning of topics - it is still in dict form
                topic_count_dict = {key.strip(): value for key, value in topic_count_dict.items() if key.strip()}
                # getting all keys in a list
                topic_count_dict_get_keys = list(topic_count_dict.keys())
                # getting number to divide topic list in 50%
                fifty_perc = len(topic_count_dict_get_keys)//2
                topic_for_ui = topic_count_dict_get_keys[:fifty_perc]
                st.session_state.fifty_perc_topics = topic_for_ui


                # st.write(f"Parser response: {st.session_state.parsed_output}")
                st.session_state["df"] = pd.DataFrame(
                    {
                        "topic": list(
                            st.session_state.parsed_output["para_dict"].keys()
                        ),
                        "paragraph": list(
                            st.session_state.parsed_output["para_dict"].values()
                        ),
                    }
                )

            except Exception as e:
                logger.error(
                    "".join(
                        traceback.format_exception(type(e), value=e, tb=e.__traceback__)
                    )
                )
                e = RuntimeError("RuntimeError while parsing input data")
                st.exception(e)

    selection = dataframe_with_selections(st.session_state["df"])

    if len(selection) != 0:
        st.write("Your selection:")
        st.write(selection["topic"].to_list())

        model_name = st.selectbox(
            "Select model",
            constant_config.get("models").get("gpt"),
        )


        difficulty_selectbox = st.selectbox(
            "Select Difficulty",
            tuple(prompts_config.get("difficulty")),
            # label_visibility="collapsed",
        )

        if difficulty_selectbox == "custom":
            # Multiselect box for question types
            question_types = st.multiselect(
                "Select Question Types",
                prompts_config.get("question_types"),
                ["Fill in the Blanks"],
            )
            # Dropdown for SOLO taxonomy levels
            solo_levels = st.multiselect(
                "Please select atleast 1 SOLO Taxonomy Level for selecting question",
                prompts_config.get("solo_taxonomy"),
                ["Multistructural"],
            )

        elif difficulty_selectbox == "easy":
            # Multiselect box for question types
            question_types = st.multiselect(
                "Select Question Types",
                prompts_config.get("question_types"),
                [
                    "True or False",
                    "Fill in the Blanks",
                    "Match the columns",
                    "Sentence Completion",
                ],
            )
            # Dropdown for SOLO taxonomy levels
            solo_levels = st.multiselect(
                "Please select atleast 1 SOLO Taxonomy Level for selecting question",
                prompts_config.get("solo_taxonomy"),
                ["Prestructural","Unistructural"],
            )


        elif difficulty_selectbox == "medium":
            # Multiselect box for question types
            question_types = st.multiselect(
                "Select Question Types",
                prompts_config.get("question_types"),
                [
                    "True or False",
                    "Fill in the Blanks",
                    "Assertion-Reasoning",
                    "Sequence Questions",
                    "Analogy Completion",
                    "Pattern Recognition",
                    "Cause and Effect",
                ],
            )
            # Dropdown for SOLO taxonomy levels
            solo_levels = st.multiselect(
                "Please select atleast 1 SOLO Taxonomy Level for selecting question",
                prompts_config.get("solo_taxonomy"),
                ["Multistructural"],
            )



        elif difficulty_selectbox == "hard":
            # Multiselect box for question types
            question_types = st.multiselect(
                "Select Question Types",
                prompts_config.get("question_types"),
                [
                    "Assertion-Reasoning",
                    "Error Identification",
                    "Analogy Completion",
                    "Critical Thinking",
                    "Pattern Recognition",
                    "Cause and Effect",
                    "Scenario-Based Questions"
                ],
            )
            # Dropdown for SOLO taxonomy levels
            solo_levels = st.multiselect(
                "Please select atleast 1 SOLO Taxonomy Level for selecting question",
                prompts_config.get("solo_taxonomy"),
                ["Relational","Extended Abstract"],
            )




        total_questions = st.number_input(
            label="Number of questions", min_value=len(question_types)
        )

        if len(question_types) > 0:
            total_questions_per_question_type = int(
                np.ceil(total_questions / len(question_types))
            )
        else:
            total_questions_per_question_type = 0

        if total_questions <= 0:
            generate_button = st.button("Generate", disabled=True)
        else:
            generate_button = st.button("Generate", disabled=False)

        if generate_button:
            st.session_state.df_questions = pd.DataFrame(columns=[
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
                                                              ]
                                                    )
            try:
                generated_questions_list = []
                if len(question_types) == 0:
                    question_types = prompts_config.get("question_types")[:1]
                if len(solo_levels) == 0:
                    solo_levels = prompts_config.get("solo_taxonomy")[:1]

                st.write(
                    f"""We are generating questions for
                        solo_levels = {solo_levels} and
                        question_types = {question_types}"""
                )

                with st.spinner("Generating questions"):

                    st.session_state.query_id = uuid.uuid4()
                    # st.write(f"Your query ID is: {st.session_state.query_id}")

                    start = time.time()

                    # Creating a ThreadPoolExecutor with maximum of 1 workers try process pool
                    with ThreadPoolExecutor(max_workers=8) as executor:

                        # Submitting tasks
                        futures = []
                        
                        for question_type in question_types:
                            futures.append(executor.submit(question_gen_parallel_task,
                                                            user_id,
                                                            input_type,
                                                            input_data.name,
                                                            st.session_state.query_id,
                                                            st.session_state.parsed_output["sha_key"],
                                                            model_name,
                                                            solo_levels,
                                                            question_type,
                                                            total_questions_per_question_type,
                                                            selection["topic"].to_list(),
                                                            
                                                            )
                                            )

                        for future in stqdm(futures,desc="Question generation progress"):
                            # generated_questions = future.result()
                            # st.write(future.result())
                            logger.info("#"*50)
                            logger.info(future.result())
                            logger.info("$"*50)

                            generated_questions_list.append(future.result())

                            if isinstance(future.result(), list) :
                                for questions_dict in future.result():

                                    cost_per_question = questions_dict["cost_per_question"]

                                    st.session_state.df_questions = pd.concat([
                                                                                st.session_state.df_questions,
                                                                                get_questions_df(questions_dict["questions"],cost_per_question)
                                                                                ],
                                                                                ignore_index=True, 
                                                                                sort=False
                                                                            )
                            else:
                                st.error(f"Could not generate question for {future.result()}",icon="🚨")


                    end = time.time()

                    # Calculate the total execution time
                    execution_time = end - start

                    # Format the execution time to 2 decimal places
                    formatted_execution_time = f"{execution_time:.2f}"

                    st.markdown(f"### total execution time = {formatted_execution_time}")



                st.write(st.session_state.df_questions)
                st.success("Question generation successfull!")
                st.balloons()

                send_slack_notification(user_id,input_type,input_data,model_name,solo_levels,question_types,total_questions_per_question_type,selection)


                st.session_state.feedback_disabled = False
                # st.write(
                #     f"Query Id after hitting generator api: {st.session_state.query_id}"
                # )
                hit_feedback_api(
                    query_id=str(st.session_state.query_id),
                    user_feedback=0,
                )

                bytes_data = BytesIO(json.dumps(generated_questions_list).encode())



                st.download_button(
                    "Download JSON",
                    bytes_data,
                    "generated_questions.json",
                    "application/json",
                )

            except Exception as e:
                logger.error(
                    "".join(
                        traceback.format_exception(type(e), value=e, tb=e.__traceback__)
                    )
                )
                e = RuntimeError("RuntimeError while generating question")
                st.exception(e)
        if not st.session_state.feedback_disabled:

            st.markdown("# Please rate the generated questions:")

            if st.button(":thumbsup:|Upvote",use_container_width=True):
                feedback = 1
                hit_feedback_api(
                    query_id=str(st.session_state.query_id),
                    user_feedback=feedback,
                )
                send_slack_feedback_notification(user_id,st.session_state.query_id,feedback)
                # st.write(f"Feedback: {feedback}")
            
            st.markdown(f"<span style='color:green; font-weight:bold;'>Upvote</span>", unsafe_allow_html=True)



            if st.button(":thumbsdown:|Downvote",use_container_width=True):
                feedback = -1
                hit_feedback_api(
                    query_id=str(st.session_state.query_id),
                    user_feedback=feedback,
                )
                send_slack_feedback_notification(user_id,st.session_state.query_id,feedback)
                # st.write(f"Feedback: {feedback}")
            st.markdown(f"<span style='color:red; font-weight:bold;'>Downvote</span>", unsafe_allow_html=True)
            


if __name__ == "__main__":
    main()
