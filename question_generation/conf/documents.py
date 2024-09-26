import os
from datetime import datetime

from dotenv import load_dotenv
from mongoengine import DoesNotExist, QuerySet, document, fields

load_dotenv()


MONGODB_ALIAS = os.getenv("MONGODB_ALIAS")


class CustomQuerySet(QuerySet):
    def safe_get(self, *args, **kwargs):
        try:
            return self.get(*args, **kwargs)
        except DoesNotExist:
            return None


class TimestampedDocument(document.Document):
    created_at = fields.DateTimeField(default=datetime.now)
    updated_at = fields.DateTimeField()

    meta = {
        "abstract": True,
        "indexes": ["-created_at", "-updated_at"],
        "queryset_class": CustomQuerySet,
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super(TimestampedDocument, self).save(*args, **kwargs)


class ParsedData(TimestampedDocument):
    SHA_id = fields.StringField(primary_key=True)
    metadata = fields.DictField()
    topic_paragraph = fields.DictField()

    meta = {
        "db_alias": MONGODB_ALIAS,
        "collection": "parsed_data",
    }


    def to_dict(self):
        return {
            "SHA_id": self.SHA_id,
            "metadata": self.metadata,
            "topic_paragraph": self.topic_paragraph,

            # Add all relevant fields
        }


class QueryData(TimestampedDocument):
    query_id = fields.StringField(primary_key=True)
    model = fields.StringField()
    input_type = fields.StringField()
    input_name = fields.StringField()
    SHA_id = fields.ReferenceField(ParsedData)
    selected_topics = fields.ListField(fields.StringField())
    question_types = fields.ListField(fields.StringField())
    solo_taxonomy_types = fields.ListField(fields.StringField())
    generated_questions = fields.ListField(fields.DictField())
    user_feedback = fields.IntField(default=0)

    meta = {
        "db_alias": MONGODB_ALIAS,
        "collection": "query_data",
    }


class UserData(TimestampedDocument):
    user_id = fields.StringField(primary_key=True)
    query_ids = fields.ListField(fields.ReferenceField(QueryData))

    meta = {
        "db_alias": MONGODB_ALIAS,
        "collection": "user_data",
    }


# class FeedbackData(TimestampedDocument):
#     query_id = fields.StringField(primary_key=True)
#     user_feedback = fields.IntField()

#     meta = {
#         "db_alias": MONGODB_ALIAS,
#         "collection": "feedback_data",
#     }
