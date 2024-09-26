import io
import math
import os
import pdb
import re
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator, List, Union

import ffmpeg
import requests
from bs4 import BeautifulSoup as soup
from conf.constant import constant_config
from conf.secrets import OPENAI_API_KEY, ORG_ID
from fake_useragent import FakeUserAgent
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_community.document_loaders.blob_loaders import Blob
from langchain_community.document_loaders.parsers.pdf import PyMuPDFParser
from langchain_community.document_loaders.parsers.txt import TextParser
from langchain_core.documents import Document
from loguru import logger
from openai import OpenAI


class BytesIOPyMuPDFLoader(PyMuPDFLoader):
    """Load `PDF` files using `PyMuPDF` from a BytesIO stream."""

    def __init__(
        self,
        pdf_stream: BytesIO,
        *,
        extract_images: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize with a BytesIO stream."""
        try:
            import fitz  # noqa:F401
        except ImportError:
            raise ImportError(
                "`PyMuPDF` package not found, please install it with "
                "`pip install pymupdf`"
            )
        # We don't call the super().__init__ here because we don't have a file_path.
        self.pdf_stream = pdf_stream
        self.extract_images = extract_images
        self.text_kwargs = kwargs

    def load(self, **kwargs: Any) -> List[Document]:
        """Load file."""
        if kwargs:
            logger.warning(
                f"Received runtime arguments {kwargs}. Passing runtime args to `load`"
                f" is deprecated. Please pass arguments during initialization instead."
            )

        text_kwargs = {**self.text_kwargs, **kwargs}

        # Use 'stream' as a placeholder for file_path since we're working with a stream.
        blob = Blob.from_data(self.pdf_stream, path="stream")

        parser = PyMuPDFParser(
            text_kwargs=text_kwargs, extract_images=self.extract_images
        )

        return parser.parse(blob)


class CustomTextLoader(BaseLoader):
    """
    It will load the string data directly
    """

    def __init__(
        self,
        text: str,
    ):
        """
        Need to create proper docstring
        """
        self.text = text

    def remove_extra_line_changes(self, text):
        # Define the regex pattern to match multiple consecutive newline characters
        pattern = r"\n+"

        # Use re.sub() to replace all occurrences of the pattern with a single newline
        return re.sub(pattern, "\n", text)

    def lazy_load(self) -> Iterator[Document]:
        """A lazy loader for Documents."""

        cleaned_text = self.remove_extra_line_changes(self.text)

        yield Document(page_content=cleaned_text, metadata={"source": "raw text"})


# add celery
# add this whisper task to celery task
# experiment with concurency
# we will get job id , this for loop will get completed with in milliseconds , need to add these job ids to mongo , pre run
# celery signals use , return job_id + Document as josn format + topic , post run
# topic extractor

# client UI , while loop status job id  , then show result as soon as mongo get updated


class CustomMediaLoader(BaseLoader):
    """
    It will load the Media directly
    and will generate text from it
    """

    def __init__(self, media_stream: io.BufferedReader, file_name: str):
        """
        Need to create proper docstring
        """
        self.whisper = OpenAI(api_key=OPENAI_API_KEY, organization=ORG_ID)
        self.media_stream = media_stream
        self.file_name = file_name

    def extract_audio_from_video(self, video_file_path, temp_audio_file_path):
        try:
            ffmpeg.input(video_file_path).output(temp_audio_file_path).run(
                capture_stderr=True, overwrite_output=True
            )
            print("audio extracted successfully!")
            return None
        except ffmpeg.Error as e:
            print(e.stderr.decode(), file=sys.stderr)
            return None

    def split_audio(
        self,
        input_audio_file_path: str,
        output_dir: str,
        max_size_mb: int = 20,
        audio_buffer_mb: int = 1,
    ):
        # Get input file duration
        audio_info = ffmpeg.probe(input_audio_file_path)
        duration = float(audio_info["streams"][0]["duration"])
        split_file_list = []
        # Calculate max duration per segment based on max_size_mb, this will give us the number of seconds of audio in each segment
        max_duration_per_segment = (max_size_mb * 1024 * 1024) / (
            int(audio_info["streams"][0]["bit_rate"]) / 8
        )
        buffer_seconds = (audio_buffer_mb * 1024 * 1024) / (
            int(audio_info["streams"][0]["bit_rate"]) / 8
        )
        # Calculate number of segments
        num_segments = int(math.ceil(duration / max_duration_per_segment))

        # Create output directory if not exists
        os.makedirs(output_dir, exist_ok=True)

        # Split audio into segments
        for i in range(num_segments):
            if i == 0:
                start_time = i * max_duration_per_segment
                max_duration_per_segment_with_buffer = (
                    max_duration_per_segment + buffer_seconds
                )

            elif i == (num_segments - 1):
                start_time = (i * max_duration_per_segment) - buffer_seconds
                max_duration_per_segment_with_buffer = max_duration_per_segment

            else:
                start_time = (i * max_duration_per_segment) - buffer_seconds
                max_duration_per_segment_with_buffer = (
                    max_duration_per_segment + buffer_seconds
                )

            # create numbering convention for file sorting
            digit_value = len(str(num_segments))
            file_no = str(i)
            if len(str(i)) < digit_value:
                for zero in range(digit_value - len(str(i))):
                    file_no = "0" + file_no

            output_file = os.path.join(output_dir, f"segment_{file_no}.mp3")
            split_file_list.append(output_file)
            ## TODO: Add overlap, add regex check to remove any binary strings
            ffmpeg.input(input_audio_file_path, ss=start_time).output(
                output_file, acodec="copy", t=max_duration_per_segment_with_buffer
            ).run(overwrite_output=True)

        return split_file_list

    def detect_media_type(self, file_name):
        if Path(file_name).suffix.lower() in constant_config.get("audio_formats"):
            return "audio"
        elif Path(file_name).suffix.lower() in constant_config.get("video_formats"):
            return "video"
        else:
            return "unknown"

    def extract_and_split_audio(self):

        suffix = Path(self.file_name).suffix.lower()

        with tempfile.NamedTemporaryFile(suffix=suffix) as fp:
            fp.write(self.media_stream.read())

            temp_file_name = Path(fp.name).stem  # file name without extension
            output_dir = f"/tmp/{temp_file_name}"
            os.mkdir(output_dir)

            if self.detect_media_type(self.file_name) == "video":
                full_audio_path = output_dir + "/saved_media.mp3"
                self.extract_audio_from_video(fp.name, full_audio_path)
            elif self.detect_media_type(self.file_name) == "audio":
                full_audio_path = output_dir + f"/{Path(fp.name).name}"
                os.system(f"cp {fp.name} {full_audio_path}")

            audio_file_list = self.split_audio(
                full_audio_path,
                output_dir,
                max_size_mb=constant_config.get("audio_split_size"),
                audio_buffer_mb=constant_config.get("audio_buffer_size"),
            )

            print(audio_file_list)

            io_buffer_reader_list = []
            for audio_file in audio_file_list:
                io_buffer_reader_list.append(open(audio_file, "rb"))

            # shutil.rmtree(output_dir)

        return io_buffer_reader_list

    def lazy_load(self):

        io_buffer_reader_list = self.extract_and_split_audio()

        for io_buffer_reader in io_buffer_reader_list:

            transcription = self.whisper.audio.transcriptions.create(
                model="whisper-1", file=io_buffer_reader, language="en"
            )
            logger.info(f"Transcription: {transcription.text}")
            yield Document(
                page_content=transcription.text, metadata={"source": "Media"}
            )


class CustomURLLoader(BaseLoader):
    """
    It will load the string data directly
    """

    def __init__(
        self,
        url: str,
    ):
        """
        Need to create proper docstring
        """
        self.url = url
        self.ua = FakeUserAgent()

    def remove_extra_line_changes(self, text):
        # Define the regex pattern to match multiple consecutive newline characters
        pattern = r"\n+"

        # Use re.sub() to replace all occurrences of the pattern with a single newline
        return re.sub(pattern, "\n", text)

    def lazy_load(self) -> Iterator[Document]:
        """A lazy loader for Documents."""
        # ssl._create_default_https_context = ssl._create_unverified_context
        headers = {"UserAgent": self.ua.random}
        r = requests.get(
            url=self.url,
            headers=headers,
            # verify=False
        )

        text = soup(r.text, "html.parser").get_text()
        cleaned_text = self.remove_extra_line_changes(text)

        yield Document(
            page_content=cleaned_text,
            metadata={"imput_type": "url", "source": self.url},
        )


class BytesIOPyMuDocumentLoader(BaseLoader):
    """Load `PDF` files using `PyMuPDF` from a io.BufferedReader stream."""

    def __init__(self, doc_stream: io.BufferedReader, filename: str = None) -> None:
        """Initialize with a io.BufferedReader stream."""
        self.doc_stream = doc_stream
        self.filename = filename

    def lazy_load(self, **kwargs: Any) -> List[Document]:
        """Load file."""
        if Path(self.filename).suffix.lower().strip() == ".txt":
            print("Inside .txt parser")
            try:

                data = [
                    Document(
                        page_content=self.doc_stream.read(),
                        metadata={"source": "Document"},
                    )
                ]

                return data
            except:
                Exception(f"Unable to parse file {self.filename}")

        elif Path(self.filename).suffix.lower().strip() == ".docx":
            print("Inside .docx parser")
            try:
                with tempfile.NamedTemporaryFile(suffix=".docx") as temp:
                    temp.write(self.doc_stream.read())
                    temp_path = temp.name
                    doc2text_converter = Docx2txtLoader(temp_path)
                    data = doc2text_converter.load()
                return data
            except:
                Exception(f"Unable to parse file {self.filename}")

        elif Path(self.filename).suffix.lower().strip() == ".doc":
            print("Inside .doc parser")
            try:
                with tempfile.NamedTemporaryFile(suffix=".doc") as temp_doc:
                    temp_doc.write(self.doc_stream.read())
                    temp_path = temp_doc.name

                    process = subprocess.Popen(
                        ["antiword", temp_path], stdout=subprocess.PIPE
                    )
                    data, error = process.communicate()

                    # data = [
                    #     Document(
                    #         page_content=output.decode("utf-8"),
                    #         metadata={"source": temp_path},
                    #     )
                    # ]
                    print(f"doc_data = {data}")
                return [
                    Document(
                        page_content=data.decode("utf-8"),
                        metadata={"imput_type": "document", "source": self.filename},
                    )
                ]
            except:
                Exception(f"Unable to parse file {self.filename}")
        else:
            logger.error("Please upload .txt/ .doc/ .docx type files only")
