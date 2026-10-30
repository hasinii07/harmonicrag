import re
from typing import List, Optional
from app.models.schemas import Chunk

def clean_text_preserving_music(text: str) -> str:
    """
    Cleans general whitespace while preserving critical music theory notation
    such as Roman numerals, figured bass (6/4, 7), accidentals (b, #, ♯, ♭),
    scale degrees (^3), chord symbols (ii-V-I, V7), and quality markers (°, ø, +).
    """
    if not text:
        return ""
    # Replace non-breaking spaces and odd line terminators
    text = text.replace('\xa0', ' ').replace('\r\n', '\n').replace('\r', '\n')
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip trailing spaces on lines
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()

def detect_section_heading(text: str) -> Optional[str]:
    """Extracts chapter, section, or markdown heading from chunk start."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return None
    first_line = lines[0]
    # Markdown heading: # Heading or ## Heading
    if first_line.startswith('#'):
        return re.sub(r'^#+\s*', '', first_line).strip()
    # Chapter or Section patterns
    match = re.match(r'^(Chapter|Section|Part|Lesson|Rule)\s+([IVXLCDM\d]+[:.\-\s]+[^\n]+)', first_line, re.IGNORECASE)
    if match:
        return first_line[:80].strip()
    return None

def chunk_document_pages(
    pages: List[dict],
    document_id: str,
    document_title: str,
    author: Optional[str] = None,
    chunk_size: int = 1400,
    chunk_overlap: int = 250
) -> List[Chunk]:
    """
    Splits page-associated texts into overlapping chunks while strictly
    preserving page number provenance for citations.
    
    Each item in `pages` should be: {"page_number": int, "text": str, "section": Optional[str]}
    """
    chunks: List[Chunk] = []
    chunk_index = 0

    for page in pages:
        page_num = page.get("page_number")
        page_text = clean_text_preserving_music(page.get("text", ""))
        page_section = page.get("section")

        if not page_text:
            continue

        # Split page text into natural paragraphs
        paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [page_text]

        current_chunk_text = ""
        current_section = page_section

        for p in paragraphs:
            # Check if paragraph has heading
            h = detect_section_heading(p)
            if h:
                current_section = h

            if len(current_chunk_text) + len(p) + 2 <= chunk_size:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + p
                else:
                    current_chunk_text = p
            else:
                # Flush current chunk
                if current_chunk_text:
                    chunk_id = f"{document_id}_p{page_num or 1}_c{chunk_index}"
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        document_title=document_title,
                        author=author,
                        page_number=page_num,
                        section=current_section,
                        content=current_chunk_text,
                        chunk_index=chunk_index,
                        char_count=len(current_chunk_text)
                    ))
                    chunk_index += 1

                # If current paragraph itself exceeds chunk_size, split by sentences
                if len(p) > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', p)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) + 1 <= chunk_size:
                            sub_chunk = (sub_chunk + " " + s).strip()
                        else:
                            if sub_chunk:
                                chunk_id = f"{document_id}_p{page_num or 1}_c{chunk_index}"
                                chunks.append(Chunk(
                                    chunk_id=chunk_id,
                                    document_id=document_id,
                                    document_title=document_title,
                                    author=author,
                                    page_number=page_num,
                                    section=current_section,
                                    content=sub_chunk,
                                    chunk_index=chunk_index,
                                    char_count=len(sub_chunk)
                                ))
                                chunk_index += 1
                                # Overlap from end of previous sub_chunk
                                overlap_text = sub_chunk[-chunk_overlap:] if len(sub_chunk) > chunk_overlap else ""
                                sub_chunk = (overlap_text + " " + s).strip()
                            else:
                                sub_chunk = s
                    current_chunk_text = sub_chunk
                else:
                    # Start next chunk with overlap if possible
                    if current_chunk_text and chunk_overlap > 0:
                        overlap = current_chunk_text[-chunk_overlap:]
                        current_chunk_text = overlap + "\n\n" + p
                    else:
                        current_chunk_text = p

        # Flush remaining text of page
        if current_chunk_text:
            chunk_id = f"{document_id}_p{page_num or 1}_c{chunk_index}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                document_title=document_title,
                author=author,
                page_number=page_num,
                section=current_section,
                content=current_chunk_text,
                chunk_index=chunk_index,
                char_count=len(current_chunk_text)
            ))
            chunk_index += 1

    return chunks

def chunk_text(
    text: str,
    document_id: str,
    document_title: str,
    author: Optional[str] = None,
    chunk_size: int = 1400,
    chunk_overlap: int = 250
) -> List[Chunk]:
    """Helper for single-page or unpaginated text inputs."""
    pages = [{"page_number": 1, "text": text, "section": None}]
    return chunk_document_pages(
        pages,
        document_id=document_id,
        document_title=document_title,
        author=author,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
