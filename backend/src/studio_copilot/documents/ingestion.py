"""Bounded multipart parsing, after route authentication, without request.form()."""

import hashlib
import tempfile
from dataclasses import dataclass

from fastapi import Request
from python_multipart import MultipartParser
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import parse_options_header
from starlette.requests import ClientDisconnect

from studio_copilot.administration.service import AdministrationError

MAX_BYTES = 10_000_000
MAX_REQUEST_BYTES = MAX_BYTES + 65_536
INLINE_BYTES = 1_000_000


def invalid(message="The upload is not a valid document.", status=422, code="invalid_document"):
    raise AdministrationError(status, code, message)


def validate_text(content: str):
    if "\x00" in content or not content.replace("\ufeff", "").strip():
        invalid("Document text cannot be blank or contain NUL.")


@dataclass(frozen=True)
class Upload:
    filename: str
    content: str
    byte_size: int
    sha256: str
    fields: dict[str, str]


class UploadParser:
    """A single temporary file and small, bounded metadata buffers."""

    def __init__(self, stream):
        self.stream = stream
        self.fields = {}
        self.filename = None
        self.size = 0
        self.digest = hashlib.sha256()
        self.ended = False
        self.parts = 0

    def on_part_begin(self):
        self.parts += 1
        if self.parts > 5:
            invalid("Upload one file and its document metadata only.")
        self.headers = {}
        self.header_name = bytearray()
        self.header_value = bytearray()
        self.header_bytes = 0
        self.data = bytearray()
        self.is_file = False

    def on_header_field(self, data, start, end):
        self.header_bytes += end - start
        if self.header_bytes > 8192:
            invalid("Upload headers are too large.", 413)
        self.header_name.extend(data[start:end])

    def on_header_value(self, data, start, end):
        self.header_bytes += end - start
        if self.header_bytes > 8192:
            invalid("Upload headers are too large.", 413)
        self.header_value.extend(data[start:end])

    def on_header_end(self):
        name = bytes(self.header_name).lower()
        if name in self.headers:
            invalid("Repeated multipart headers are not supported.")
        self.headers[name] = bytes(self.header_value)
        self.header_name.clear()
        self.header_value.clear()

    def on_headers_finished(self):
        disposition, options = parse_options_header(self.headers.get(b"content-disposition", b""))
        if disposition != b"form-data" or b"name" not in options:
            invalid("Invalid multipart disposition.")
        self.name = options[b"name"].decode("utf-8")
        if b"filename" in options:
            if self.name != "file" or self.filename is not None:
                invalid("Upload exactly one file using the file field.")
            self.filename = options[b"filename"].decode("utf-8")
            self.is_file = True
        elif self.name not in {"title", "effective_from", "effective_to", "expected_revision"}:
            invalid("Unknown upload metadata field.")
        elif self.name in self.fields:
            invalid("Repeated upload metadata is not supported.")
        if b"content-transfer-encoding" in self.headers:
            invalid("Encoded multipart parts are not supported.")

    def on_part_data(self, data, start, end):
        if self.is_file:
            self.size += end - start
            if self.size > MAX_BYTES:
                invalid("Documents must be at most 10 MB.", 413, "document_too_large")
            fragment = memoryview(data)[start:end]
            self.digest.update(fragment)
            self.stream.write(fragment)
        else:
            if len(self.data) + end - start > 1024:
                invalid("Upload metadata is too large.", 413)
            self.data.extend(data[start:end])

    def on_part_end(self):
        if not self.is_file:
            self.fields[self.name] = self.data.decode("utf-8")

    def on_end(self):
        self.ended = True


async def receive_upload(request: Request) -> Upload:
    # Routes have Request (not File/Form) arguments: FastAPI executes authentication
    # dependencies before this function starts reading or allocating a temporary file.
    length = request.headers.get("content-length")
    if length is not None:
        try:
            size = int(length)
        except ValueError:
            invalid("Invalid Content-Length.", 400)
        if size < 0:
            invalid("Invalid Content-Length.", 400)
        if size > MAX_REQUEST_BYTES:
            invalid("Upload request is too large.", 413, "document_too_large")
    content_type, options = parse_options_header(request.headers.get("content-type", ""))
    boundary = options.get(b"boundary", b"")
    if content_type != b"multipart/form-data" or not 1 <= len(boundary) <= 200:
        invalid("Use multipart/form-data with a valid boundary.", 400)
    try:
        with tempfile.TemporaryFile(mode="w+b") as stream:
            target = UploadParser(stream)
            callbacks = {
                name: getattr(target, name)
                for name in (
                    "on_part_begin",
                    "on_header_field",
                    "on_header_value",
                    "on_header_end",
                    "on_headers_finished",
                    "on_part_data",
                    "on_part_end",
                    "on_end",
                )
            }
            parser = MultipartParser(boundary, callbacks, max_header_count=8, max_header_size=8192)
            received = 0
            async for chunk in request.stream():
                received += len(chunk)
                if received > MAX_REQUEST_BYTES:
                    invalid("Upload request is too large.", 413, "document_too_large")
                # Bound the work passed into the parser even if a transport yields a large chunk.
                for offset in range(0, len(chunk), 65_536):
                    parser.write(chunk[offset : offset + 65_536])
            parser.finalize()
            if length is not None and received != int(length):
                invalid("The upload was incomplete or its length was incorrect.", 400)
            if not target.ended or target.filename is None:
                invalid("The multipart upload is incomplete or has no file.", 400)
            stream.seek(0)
            content = stream.read().decode("utf-8")
            validate_text(content)
            return Upload(
                target.filename, content, target.size, target.digest.hexdigest(), target.fields
            )
    except (UnicodeDecodeError, MultipartParseError, ClientDisconnect) as error:
        raise AdministrationError(
            422, "invalid_document", "The upload is incomplete or is not valid UTF-8 text."
        ) from error
