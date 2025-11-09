from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """
    Represents a text chunk from a parsed document.

    Chunks are created by splitting a document's text into semantically
    coherent segments suitable for embedding and vector search.
    """

    chunk_id: int = Field(
        ge=0, description="Sequential chunk number within the paper (0-indexed)"
    )
    paper_id: str = Field(description="String UUID of the parent document")
    paper_name: str = Field(
        description="Human-readable paper identifier (filename stem)"
    )
    text: str = Field(description="The actual chunk text content")
    section_title: str | None = Field(
        default=None, description="Section title this chunk belongs to (if available)"
    )
    page_number: int | None = Field(
        default=None, ge=1, description="Page number where chunk appears (1-indexed)"
    )
    token_count: int = Field(ge=0, description="Number of tokens in this chunk")
