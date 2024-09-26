import hashlib
import io
import re
from pathlib import Path
from typing import List

import numpy as np
from conf.constant import constant_config
from conf.documents import ParsedData
from data_loader.models import UploadedFile
from django.http import JsonResponse
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from .parser import (
    BytesIOPyMuDocumentLoader,
    BytesIOPyMuPDFLoader,
    CustomMediaLoader,
    CustomTextLoader,
    CustomURLLoader,
)
from .topic_extractor import TopicExtractor


def generate_sha_key(data: bytes) -> str:
    """
    Generate a SHA hash for a file.

    Args:
        data (bytes): pass bytes data.

    Returns:
        str: The SHA_512 hash value as a hexadecimal string.
    """

    sha512_hash = hashlib.sha512()
    sha512_hash.update(data)
    return sha512_hash.hexdigest()


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


def is_url(text: str) -> bool:
    """
    Args:
        text = text to be checked

    Return:
        True:  if it is valid URL
        False: if it is not valid URL
    """
    # Regular expression pattern for URL matching
    url_pattern = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https:// or ftp://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"  # ...or ipv4
        r"\[?[A-F0-9]*:[A-F0-9:]+\]?)"  # ...or ipv6
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    return bool(re.match(url_pattern, text))


def get_loader(data, filename=None):
    """
    It will provide you required data loader
    """
    if isinstance(data, bytes) and Path(filename).suffix.lower() == ".pdf":
        return BytesIOPyMuPDFLoader(data)

    elif isinstance(data, io.BufferedReader) and Path(
        filename
    ).suffix.lower() in constant_config.get("document_formats"):
        return BytesIOPyMuDocumentLoader(data, filename)

    elif isinstance(data, io.BufferedReader) and (
        Path(filename).suffix.lower() in constant_config.get("supported_media_format")
    ):
        return CustomMediaLoader(data, file_name=filename)

    elif isinstance(data, str) and is_url(data):
        return CustomURLLoader(data)

    elif isinstance(data, str) and (not is_url(data)):
        return CustomTextLoader(data)

    else:

        print(f"data = {data}")
        print(f"type(data) = {type(data)}")
        print(f"Path(filename).suffix.lower() = {Path(filename).suffix.lower()}")

        raise NotImplementedError("asked loader class yet to be implemented")


def process_url(url: str, user_id: str):

    doc_text = {
        "content": [],
        "topic": [],
        "paragraph": [],
        "url": url,
        "user_id": user_id,
    }

    topic_extractor = TopicExtractor()
    loader = get_loader(url)
    docs = loader.load()

    SHA_key = generate_sha_key(docs[0].page_content.encode("utf-8"))

    # Get the ParsedData object from MongoDB
    parsed_data = ParsedData.objects.safe_get(SHA_id=SHA_key)

    # Check SHA key in mongo, if exists then bypass below steps, vice versa
    if parsed_data is not None:
        topic_paragraph = parsed_data.topic_paragraph
        return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})

    doc_text["content"].append(docs[0].page_content)
    logger.info(f"docs = {docs}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=constant_config.get("paragraph_size"),
        chunk_overlap=constant_config.get("paragraph_overlap"),
    )

    logger.info(f"doc_text['content'] = {doc_text['content']}")

    # Creating the list of paragraphs in Document format
    documents = text_splitter.split_documents(
        [
            Document(
                page_content=doc_text["content"][0],
                metadata={"input_type": "url"},
            )
        ]
    )

    logger.info(f"documents = {documents}")

    # Send documents to topic extractor
    for doc in documents:
        doc_text["paragraph"].append(doc.page_content)
        topic_extracted = topic_extractor.extract_keywords(doc.page_content)
        doc_text["topic"].append(topic_extracted)

    metadata = {
        "name": url,
        "input_type": "URL",
    }

    topic_paragraph = dict(zip(doc_text["topic"], doc_text["paragraph"]))

    ParsedData(
        SHA_id=SHA_key, metadata=metadata, topic_paragraph=topic_paragraph
    ).save()

    return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})


def process_pdf(uploaded_file: UploadedFile, user_id: str):

    doc_text = {"paragraph": [], "topic": [], "user_id": user_id}
    topic_extractor = TopicExtractor()
    file_content_bytes = uploaded_file.file.read()

    # Extract SHA key
    SHA_key = generate_sha_key(file_content_bytes)

    # Get the ParsedData object from MongoDB
    parsed_data = ParsedData.objects.safe_get(SHA_id=SHA_key)

    # Check SHA key in mongo, if exists then bypass below steps, vice versa
    if parsed_data is not None:
        topic_paragraph = parsed_data.topic_paragraph
        return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})

    file_name = Path(uploaded_file.file.name).name
    if Path(file_name).suffix.lower() != ".pdf":
        raise Exception(
            f"Unsupported file format uploaded. Expected .pdf, uploaded {file_name}"
        )

    # PUT THIS IN TASKS.PY
    loader = get_loader(file_content_bytes, file_name)

    docs = loader.load()
    for doc in docs:
        doc_text["paragraph"].append(doc.page_content)
        topic_extracted = topic_extractor.extract_keywords(doc.page_content)
        doc_text["topic"].append(topic_extracted)

    metadata = {"name": file_name, "input_type": "PDF"}
    topic_paragraph = dict(zip(doc_text["topic"], doc_text["paragraph"]))

    ParsedData(
        SHA_id=SHA_key, metadata=metadata, topic_paragraph=topic_paragraph
    ).save()

    return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})


def process_text(text: str, user_id: str):
    doc_text = {"content": [], "topic": [], "paragraph": [], "user_id": user_id}
    topic_extractor = TopicExtractor()

    SHA_key = generate_sha_key(text.encode("utf-8"))

    # Get the ParsedData object from MongoDB
    parsed_data = ParsedData.objects.safe_get(SHA_id=SHA_key)

    # Check SHA key in mongo, if exists then bypass below steps, vice versa
    if parsed_data is not None:
        topic_paragraph = parsed_data.topic_paragraph
        return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})

    loader = get_loader(text)
    docs = loader.load()
    doc_text["content"].append(docs[0].page_content)
    logger.info(f"docs = {docs}")
    for doc in docs:
        doc_text["paragraph"].append(doc.page_content)
        topic_extracted = topic_extractor.extract_keywords(doc.page_content)
        doc_text["topic"].append(topic_extracted)

    metadata = {
        "name": " ".join(doc_text["content"][0].split(" ")[:5]),
        "input_type": "raw_text",
    }
    topic_paragraph = dict(zip(doc_text["topic"], doc_text["paragraph"]))
    logger.info(f"topic_paragraph: {topic_paragraph}")

    ParsedData(
        SHA_id=SHA_key, metadata=metadata, topic_paragraph=topic_paragraph
    ).save()

    return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})


def process_media(uploaded_file: UploadedFile, user_id: str):
    doc_text = {"content": [], "paragraph": [], "topic": [], "user_id": user_id}
    topic_extractor = TopicExtractor()
    print("topic_extractor=-=-=-=-", topic_extractor)
    file_content_buffer_reader = io.BufferedReader(uploaded_file.file.open())
    print("fle_ciontenet=-=-=-=-=", file_content_buffer_reader)
    # Extract SHA key
    SHA_key = generate_sha_key(file_content_buffer_reader.read())
    print("sha key=-=-=-=-", SHA_key)
    file_content_buffer_reader.seek(0)

    # Get the ParsedData object from MongoDB
    parsed_data = ParsedData.objects.safe_get(SHA_id=SHA_key)
    print("pased=======================", parsed_data)
    # Check SHA key in mongo, if exists then bypass below steps, vice versa
    if parsed_data is not None:
        topic_paragraph = parsed_data.topic_paragraph
        return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})

    # logger.info(f"uploaded file path = {uploaded_file.name}")
    file_name = Path(uploaded_file.file.name).name
    logger.info(f"File name: {file_name}")
    logger.info(
        f"Type of file_content_buffer_reader: {type(file_content_buffer_reader)}"
    )

    # PUT THIS IN TASKS.PY
    loader = get_loader(file_content_buffer_reader, file_name)
    docs = loader.load()
    logger.info(f"doc length before texty splitter = {len(docs)}")

    for doc in docs:
        doc_text["content"].append(doc.page_content)

    doc_text["content"] = " ".join(doc_text["content"])
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=constant_config.get("paragraph_size"),
        chunk_overlap=constant_config.get("paragraph_overlap"),
    )
    # Creating the list of paragraphs in Document format
    documents = text_splitter.split_documents(
        [
            Document(
                page_content=doc_text["content"],
                metadata={"input_type": "media"},
            )
        ]
    )
    # Send documents to topic extractor
    for doc in documents:
        doc_text["paragraph"].append(doc.page_content)
        topic_extracted = topic_extractor.extract_keywords(doc.page_content)
        doc_text["topic"].append(topic_extracted)

    metadata = {"name": file_name, "input_type": "Media"}
    topic_paragraph = dict(zip(doc_text["topic"], doc_text["paragraph"]))

    ParsedData(
        SHA_id=SHA_key, metadata=metadata, topic_paragraph=topic_paragraph
    ).save()

    return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})


def process_document(uploaded_file: UploadedFile, user_id: str):

    doc_text = {"content": [], "paragraph": [], "topic": [], "user_id": user_id}
    topic_extractor = TopicExtractor()
    file_content_buffer_reader = io.BufferedReader(uploaded_file.file.open())
    file_name = Path(uploaded_file.file.name).name

    # PUT THIS IN TASKS.PY
    loader = get_loader(file_content_buffer_reader, file_name)
    print(f"loader = {loader}")
    docs = loader.load()
    print(f"loaded_docs = {len(docs)}")

    SHA_key = generate_sha_key(docs[0].page_content.encode("utf-8"))

    # Get the ParsedData object from MongoDB
    parsed_data = ParsedData.objects.safe_get(SHA_id=SHA_key)

    # Check SHA key in mongo, if exists then bypass below steps, vice versa
    if parsed_data is not None:
        topic_paragraph = parsed_data.topic_paragraph
        return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})

    doc_text["content"].append(docs[0].page_content)
    logger.info(f"docs = {docs}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=constant_config.get("paragraph_size"),
        chunk_overlap=constant_config.get("paragraph_overlap"),
    )

    # Creating the list of paragraphs in Document format
    documents = text_splitter.split_documents(
        [
            Document(
                page_content=doc_text["content"][0],
                metadata={"input_type": "doc"},
            )
        ]
    )

    logger.info(f"documents after splitter = {documents}")

    # Send documents to topic extractor
    for doc in documents:
        doc_text["paragraph"].append(doc.page_content)
        topic_extracted = topic_extractor.extract_keywords(doc.page_content)
        doc_text["topic"].append(topic_extracted)

    metadata = {
        "name": file_name,
        "input_type": "URL",
    }

    topic_paragraph = dict(zip(doc_text["topic"], doc_text["paragraph"]))

    ParsedData(
        SHA_id=SHA_key, metadata=metadata, topic_paragraph=topic_paragraph
    ).save()

    return JsonResponse({"para_dict": topic_paragraph, "sha_key": SHA_key})
