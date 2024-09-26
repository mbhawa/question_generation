from conf.prompts import prompts_config
from django import forms

QUESTION_CHOICES = [
    (option, option.replace("_", " ").title())
    for option in prompts_config.get("question_types")
]

SOLO_LEVEL_CHOICES = [
    (option, option.replace("_", " ").title())
    for option in prompts_config.get("solo_taxonomy")
]

# FEEDBACK_CHOICES = (
#     (1, "Positive"),
#     (-1, "Negative"),
# )


class GeneratorInputForm(forms.Form):
    user_id = forms.CharField(label="User ID", max_length=100)
    input_type = forms.CharField(label="Input Type")
    input_name = forms.CharField(label="Input Name")
    query_id = forms.CharField(label="Query ID")
    data_sha_key = forms.CharField(label="Data SHA Key")
    model_name = forms.CharField(label="Model Name", max_length=100)
    solo_taxonomy = forms.MultipleChoiceField(
        choices=SOLO_LEVEL_CHOICES, widget=forms.CheckboxSelectMultiple()
    )
    question_types = forms.CharField(label="Question type")
    number_of_questions = forms.IntegerField(
        widget=forms.NumberInput(attrs={"min": 1}), label="Number of Questions"
    )
    selected_topics = forms.CharField(label="List of selected topics")


class FeedbackInputForm(forms.Form):
    query_id = forms.CharField(label="Query ID")
    user_feedback = forms.IntegerField(min_value=-1, max_value=1)
