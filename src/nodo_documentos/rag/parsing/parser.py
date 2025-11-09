import base64
from functools import lru_cache
from pathlib import Path

from loguru import logger
from mistralai import Mistral
from pydantic import ValidationError

from nodo_documentos.rag.parsing.models import OCRResponse, ParsedDocument
from nodo_documentos.rag.parsing.settings import settings


class ParsingError(Exception):
    """Base exception for parsing errors."""


class OCRError(ParsingError):
    """Error during OCR processing."""


class PDFParser:
    """
    PDF parser using Mistral OCR API.

    Handles document processing from PDF to structured ParsedDocument.
    """

    def __init__(self):
        self._settings = settings
        self.model = self._settings.ocr_model
        self.client = Mistral(api_key=self._settings.mistral_api_key)

        logger.debug(f"Initialized PDFParser with model: {self.model}")

    def parse_pdf(
        self,
        file_path: Path,
        include_images: bool = False,
    ) -> ParsedDocument:
        """
        Parse a PDF file into a structured ParsedDocument.

        This is the main entry point for the parsing pipeline.

        Args:
            file_path: Path to the PDF file
            include_images: Whether to include images in the OCR response. Defaults
                to the value configured in settings when omitted.

        Returns:
            ParsedDocument with extracted text, sections, and metadata

        Raises:
            ParsingError: If file doesn't exist or parsing fails
            OCRError: If OCR processing fails

        Example:
            >>> parser = PDFParser()
            >>> doc = parser.parse_pdf("document.pdf")
            >>> print(doc.document_name, len(doc.sections))
            document 29
        """
        # Validate file exists
        if not file_path.exists():
            raise ParsingError(f"File not found: {file_path}")

        if not file_path.suffix.lower() == ".pdf":
            raise ParsingError(f"Not a PDF file: {file_path}")

        logger.info(f"Parsing PDF: {file_path.name}")

        try:
            # Encode PDF to base64
            logger.debug("Encoding PDF to base64...")
            base64_pdf = self._encode_pdf(file_path=file_path)

            # Call Mistral OCR
            logger.debug(f"Calling Mistral OCR API (model: {self.model})...")
            ocr_response = self._call_ocr_api(base64_pdf, include_images=include_images)

            # Create ParsedDocument (handles page combining and section extraction)
            logger.debug("Creating ParsedDocument...")
            doc = ParsedDocument.from_ocr_response(
                file_path=file_path,
                ocr_response=ocr_response,
            )

            logger.success(
                f"Successfully parsed {file_path.name}: "
                f"{len(doc.sections)} sections, "
                f"{len(doc.text):,} characters, "
                f"{ocr_response.usage_info.pages_processed} pages"
            )

            return doc

        except OCRError:
            raise
        except ValidationError as e:
            raise OCRError(f"Invalid OCR response format: {e}")
        except Exception as e:
            raise ParsingError(f"Failed to parse PDF: {e}")

    def _encode_pdf(
        self,
        file_path: Path,
    ) -> str:
        """
        Encode PDF file to base64 string.

        Args:
            file_path: Path to PDF file

        Returns:
            Base64-encoded string

        Raises:
            ParsingError: If file cannot be read
        """
        try:
            with open(file_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode("utf-8")
        except Exception as e:
            raise ParsingError(f"Failed to read PDF file: {e}")

    def _call_ocr_api(
        self,
        base64_pdf: str,
        include_images: bool = False,
    ) -> OCRResponse:
        """
        Call Mistral OCR API with base64-encoded PDF.

        Args:
            base64_pdf: Base64-encoded PDF string
            include_images: Whether to include images in the OCR response

        Returns:
            Validated OCRResponse object

        Raises:
            OCRError: If API call fails
        """
        try:
            response = self.client.ocr.process(
                model=self.model,
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{base64_pdf}",
                },
                include_image_base64=include_images,
            )

            # Validate and parse response
            return OCRResponse.model_validate(
                {
                    "pages": [
                        {
                            "index": p.index,
                            "markdown": p.markdown,
                            "images": [
                                {
                                    "id": img.id,
                                    "top_left_x": img.top_left_x,
                                    "top_left_y": img.top_left_y,
                                    "bottom_right_x": img.bottom_right_x,
                                    "bottom_right_y": img.bottom_right_y,
                                    "image_base64": img.image_base64,
                                    "image_annotation": img.image_annotation,
                                }
                                for img in p.images
                            ],
                            "dimensions": {
                                "dpi": p.dimensions.dpi if p.dimensions else None,
                                "height": p.dimensions.height if p.dimensions else None,
                                "width": p.dimensions.width if p.dimensions else None,
                            },
                        }
                        for p in response.pages
                    ],
                    "model": response.model,
                    "usage_info": {
                        "pages_processed": response.usage_info.pages_processed,
                        "doc_size_bytes": response.usage_info.doc_size_bytes,
                    },
                }
            )

        except Exception as e:
            raise OCRError(f"OCR API call failed: {e}")


@lru_cache
def get_parser() -> PDFParser:
    """Return a cached parser instance."""
    return PDFParser()
