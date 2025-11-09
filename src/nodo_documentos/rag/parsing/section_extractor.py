import re

from nodo_documentos.rag.parsing.models import Section


def extract_sections(markdown_text: str) -> list[Section]:
    """
    Extract section information from markdown headers.

    Identifies sections by parsing markdown headers (# ## ### etc.) and
    calculates their positions in the full text.

    Args:
        markdown_text: Full document text in markdown format

    Returns:
        List of Section objects with title, indices, and level

    Example:
        >>> text = "# Introduction\\n\\nSome text...\\n\\n## Methods\\n\\nMore text..."
        >>> sections = extract_sections(text)
        >>> len(sections)
        2
        >>> sections[0].title
        'Introduction'
        >>> sections[0].level
        1
    """
    sections: list[Section] = []

    # Match markdown headers: # Title, ## Subtitle, etc.
    # Captures: (#{1,6}) for level, (.+) for title
    header_pattern = r"^(#{1,6})\s+(.+)$"

    for match in re.finditer(header_pattern, markdown_text, re.MULTILINE):
        hashes = match.group(1)
        title = match.group(2).strip()
        level = len(hashes)
        start_index = match.start()

        sections.append(
            Section(
                title=title,
                start_index=start_index,
                end_index=0,  # Will be calculated below
                level=level,
            )
        )

    # Calculate end_index for each section
    # End is either the start of next section or EOF
    for i, section in enumerate(sections):
        if i < len(sections) - 1:
            section.end_index = sections[i + 1].start_index
        else:
            section.end_index = len(markdown_text)

    return sections
