import tempfile
from pathlib import Path

from loguru import logger

from nodo_documentos.db.models import Document
from nodo_documentos.rag.chunking.chunker import PDFChunker
from nodo_documentos.rag.encoding.encoder import EmbeddingEncoder
from nodo_documentos.rag.parsing.parser import PDFParser
from nodo_documentos.rag.vector_db.db import VectorDB
from nodo_documentos.services.models import ClinicalDocumentChunk
from nodo_documentos.utils.s3_utils import download_from_s3


class RAGService:
    def __init__(
        self,
        vector_db: VectorDB,
        pdf_parser: PDFParser,
        pdf_chunker: PDFChunker,
        encoder: EmbeddingEncoder,
    ) -> None:
        self._vector_db = vector_db
        self._pdf_parser = pdf_parser
        self._pdf_chunker = pdf_chunker
        self._encoder = encoder

    async def index_document(self, document: Document) -> None:
        """
        Index a clinical document into the vector database.

        Downloads PDF from S3, parses it, chunks it, generates embeddings,
        and stores everything in the vector database with ownership metadata.

        Args:
            document: SQL Document model containing S3 URL and ownership info

        """
        logger.info(f"Starting RAG indexing for document {document.doc_id}")

        temp_file_path = None
        try:
            logger.debug(f"Downloading PDF from {document.s3_url}")
            pdf_bytes = download_from_s3(document.s3_url)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(pdf_bytes)
                temp_file_path = Path(temp_file.name)

            logger.debug("Parsing PDF document")
            parsed_doc = self._pdf_parser.parse_pdf(temp_file_path)

            logger.debug("Chunking parsed document")
            base_chunks = self._pdf_chunker.chunk_document(parsed_doc)

            clinical_chunks = []
            for chunk in base_chunks:
                # Update document_id to match the SQL Document ID
                chunk_dict = chunk.model_dump()
                chunk_dict["document_id"] = str(document.doc_id)
                clinical_chunk = ClinicalDocumentChunk(
                    **chunk_dict,
                    health_user_ci=document.health_user_ci,
                    clinic_name=document.clinic_name,
                    created_by=document.created_by,
                )
                clinical_chunks.append(clinical_chunk)

            logger.debug(f"Generating embeddings for {len(clinical_chunks)} chunks")
            texts = [chunk.text for chunk in clinical_chunks]
            embeddings = self._encoder.embed_many(texts)

            logger.debug("Storing chunks and embeddings in vector database")
            self._vector_db.index_document(parsed_doc, clinical_chunks, embeddings)

            logger.success(
                f"Successfully indexed document {document.doc_id}: "
                f"{len(clinical_chunks)} chunks stored"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Failed to index document {document.doc_id}: {error_msg}",
                exc_info=True,
            )
            # Don't raise - indexing failures shouldn't break document creation

        finally:
            if temp_file_path and temp_file_path.exists():
                temp_file_path.unlink()
