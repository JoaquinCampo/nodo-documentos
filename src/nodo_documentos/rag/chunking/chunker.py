import tiktoken
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from loguru import logger

from nodo_documentos.rag.chunking.models import Chunk
from nodo_documentos.rag.parsing.models import ParsedDocument


class PDFChunker:
    """
    Chunks parsed PDF documents into semantically coherent segments.

    Uses a hybrid approach:
    1. MarkdownHeaderTextSplitter: Respects section boundaries
    2. RecursiveCharacterTextSplitter: Manages chunk sizes within sections
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        """
        Initialize the chunker with size parameters.

        Args:
            chunk_size: Target tokens per chunk (default: 500)
            chunk_overlap: Overlap tokens between chunks (default: 50)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize tiktoken encoder for token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Initialize markdown header splitter
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                ("####", "Header 4"),
            ],
            strip_headers=False,
        )

        # Initialize recursive text splitter for size management
        self.text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        logger.debug(
            f"Initialized PDFChunker: chunk_size={chunk_size}, overlap={chunk_overlap}"
        )

    def chunk_document(self, doc: ParsedDocument) -> list[Chunk]:
        """
        Split a parsed document into chunks.

        Args:
            doc: ParsedDocument from the parser module

        Returns:
            List of Chunk objects with metadata

        TODO: Extend this to take into account tables, we should avoid splitting tables
        """
        logger.info(f"Chunking document: {doc.document_name}")

        # Split by markdown headers first
        header_splits: list[Document] = self.header_splitter.split_text(doc.text)
        logger.debug(f"Split into {len(header_splits)} header-based sections")

        chunks: list[Chunk] = []
        cursor = 0
        previous_chunk_text: str | None = None

        for header_doc in header_splits:
            section_title = self._extract_section_title(header_doc.metadata)

            # Split by size if needed (text_splitter handles token limits)
            text_chunks = self.text_splitter.split_text(header_doc.page_content)

            for text_chunk in text_chunks:
                page_num, cursor = self._resolve_chunk_page(
                    doc=doc,
                    chunk_text=text_chunk,
                    cursor=cursor,
                    previous_chunk_text=previous_chunk_text,
                )

                chunk = Chunk(
                    chunk_id=len(chunks),  # Sequential ID
                    document_id=str(doc.id),
                    document_name=doc.document_name,
                    text=text_chunk,
                    section_title=section_title,
                    page_number=page_num,
                    token_count=len(self.tokenizer.encode(text_chunk)),
                )
                chunks.append(chunk)

                previous_chunk_text = text_chunk

        total_tokens = sum(c.token_count for c in chunks)
        logger.success(
            f"Created {len(chunks)} chunks from {doc.document_name} "
            f"({total_tokens:,} tokens total)"
        )

        return chunks

    def _resolve_chunk_page(
        self,
        doc: ParsedDocument,
        chunk_text: str,
        cursor: int,
        previous_chunk_text: str | None,
    ) -> tuple[int | None, int]:
        """
        Return the page number for a chunk and advance the running cursor.

        Args:
            doc: ParsedDocument with page boundary metadata
            chunk_text: Text of the current chunk
            cursor: Current position in the combined document text
            previous_chunk_text: Text from the previous chunk (for overlap detection)

        Returns:
            Tuple containing the page number (or None) and the updated cursor position.
        """
        overlap = self._calculate_overlap(previous_chunk_text, chunk_text)
        chunk_start = max(cursor - overlap, 0)
        page_num = self._get_page_at_position(doc, chunk_start)
        new_cursor = chunk_start + len(chunk_text)
        return page_num, new_cursor

    @staticmethod
    def _calculate_overlap(previous: str | None, current: str) -> int:
        """
        Determine how many characters the current chunk shares with the previous one.
        """
        if previous is None or not previous or not current:
            return 0

        max_possible = min(len(previous), len(current))
        for size in range(max_possible, 0, -1):
            if previous[-size:] == current[:size]:
                return size
        return 0

    def _extract_section_title(self, metadata: dict) -> str | None:
        """
        Extract section title from LangChain metadata.

        Args:
            metadata: Metadata dict from MarkdownHeaderTextSplitter

        Returns:
            Section title or None
        """
        # Return the most specific (deepest) header
        for key in ["Header 4", "Header 3", "Header 2", "Header 1"]:
            if key in metadata and metadata[key]:
                return metadata[key]
        return None

    def _get_page_at_position(self, doc: ParsedDocument, char_pos: int) -> int | None:
        """
        Determine page number for a character position in the document.

        Args:
            doc: ParsedDocument containing page boundary information
            char_pos: Character position in the full text

        Returns:
            1-based page number or None if not found
        """

        for page in doc.page_info:
            if page.char_start <= char_pos < page.char_end:
                return page.page_number

        if doc.page_info and char_pos >= doc.page_info[-1].char_end:
            return doc.page_info[-1].page_number

        return None


def get_chunker() -> PDFChunker:
    """Return a cached chunker instance."""
    return PDFChunker()
