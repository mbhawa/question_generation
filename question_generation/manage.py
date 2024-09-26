#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from conf.settings import connect_to_mongo, create_database
from loguru import logger


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "question_generation.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    if sys.argv[1] == "runserver":
        connect_to_mongo()
        logger.info("*********************Connected to mongo db ****************")

        create_database()

        logger.info("*********************Collections created ******************")
    
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
