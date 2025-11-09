from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

# ============================================================================
# Mistral OCR Response Models
# ============================================================================


class OCRImageObject(BaseModel):
    """Represents an image detected on a page."""

    id: str = Field(description="Image identifier (e.g., 'img-0.jpeg')")
    top_left_x: int = Field(description="X coordinate of top-left corner")
    top_left_y: int = Field(description="Y coordinate of top-left corner")
    bottom_right_x: int = Field(description="X coordinate of bottom-right corner")
    bottom_right_y: int = Field(description="Y coordinate of bottom-right corner")
    image_base64: str | None = Field(
        default=None, description="Base64-encoded image data (if requested)"
    )
    image_annotation: str | None = Field(
        default=None, description="Optional image annotation"
    )


class PageDimensions(BaseModel):
    """Page dimensions from OCR."""

    dpi: int = Field(description="Dots per inch")
    height: int = Field(description="Page height in pixels")
    width: int = Field(description="Page width in pixels")


class OCRPage(BaseModel):
    """Represents a single page in Mistral OCR response."""

    index: int = Field(description="0-based page number")
    markdown: str = Field(description="Extracted markdown content")
    images: list[OCRImageObject] = Field(
        default_factory=list, description="List of images detected on this page"
    )
    dimensions: PageDimensions = Field(description="Page dimensions")


class OCRUsageInfo(BaseModel):
    """Usage information from OCR processing."""

    pages_processed: int
    doc_size_bytes: int | None = None


class OCRResponse(BaseModel):
    """Complete Mistral OCR API response."""

    pages: list[OCRPage]
    model: str
    usage_info: OCRUsageInfo


# ============================================================================
# Domain Models
# ============================================================================


class Section(BaseModel):
    """
    Represents a detected section within a document.

    Extracted from markdown headers in the OCR output.
    """

    title: str = Field(description="Section heading (e.g., 'Abstract', '3. Methods')")
    start_index: int = Field(
        ge=0, description="Character position where section starts (0-indexed)"
    )
    end_index: int = Field(
        ge=0, description="Character position where section ends (0-indexed)"
    )
    level: int = Field(
        ge=1, le=6, description="Header level from markdown (1 for #, 2 for ##, etc.)"
    )


class PageInfo(BaseModel):
    """
    Page boundary information for character position to page number mapping.

    Used to efficiently determine which page a chunk belongs to.
    """

    page_number: int = Field(ge=1, description="1-based page number")
    char_start: int = Field(
        ge=0, description="Character index where page starts in full text"
    )
    char_end: int = Field(
        ge=0, description="Character index where page ends in full text"
    )


class DocumentMetadata(BaseModel):
    """
    Metadata about the parsed document.

    Contains file information and OCR processing details.
    """

    indexed_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when document was indexed"
    )
    pages_processed: int = Field(ge=1, description="Number of pages processed by OCR")
    ocr_model: str = Field(
        default="mistral-ocr-latest", description="OCR model used for processing"
    )


class ParsedDocument(BaseModel):
    """
    Complete representation of a parsed PDF document.

    This is the primary output of the parser module.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier (auto-generated UUID)",
    )
    document_name: str = Field(
        description="Human-readable identifier from filename (without extension)"
    )
    file_path: Path = Field(description="Absolute path to the PDF file")
    text: str = Field(
        description="Full extracted text content (all pages concatenated)"
    )
    sections: list[Section] = Field(
        default_factory=list, description="Identified sections within the document"
    )
    page_info: list[PageInfo] = Field(
        default_factory=list,
        description="Page boundary information for page number lookup",
    )
    metadata: DocumentMetadata = Field(description="Document metadata")

    @classmethod
    def from_ocr_response(
        cls,
        file_path: Path,
        ocr_response: OCRResponse,
    ) -> "ParsedDocument":
        """
        Create a ParsedDocument from Mistral OCR response.

        Args:
            file_path: Path to the PDF file
            ocr_response: Mistral OCR API response

        Returns:
            ParsedDocument instance
        """
        from nodo_documentos.rag.parsing.section_extractor import extract_sections

        document_name = file_path.stem

        # Combine all page markdown into single text
        pages_text = [page.markdown for page in ocr_response.pages]
        full_text = "\n".join(pages_text)

        # Build page boundary information
        page_info = []
        char_pos = 0
        for i, page_text in enumerate(pages_text):
            page_len = len(page_text)
            page_info.append(
                PageInfo(
                    page_number=i + 1,  # 1-based
                    char_start=char_pos,
                    char_end=char_pos + page_len,
                )
            )
            char_pos += page_len + 1

        # Extract sections from the combined text
        sections = extract_sections(markdown_text=full_text)

        metadata = DocumentMetadata(
            pages_processed=ocr_response.usage_info.pages_processed,
            ocr_model=ocr_response.model,
        )

        return cls(
            document_name=document_name,
            file_path=file_path.absolute(),
            text=full_text,
            sections=sections,
            page_info=page_info,
            metadata=metadata,
        )
