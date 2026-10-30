import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.rag.chunking import clean_text_preserving_music, chunk_document_pages, chunk_text

def test_clean_text_preserving_music():
    sample = "The progression  ii-V-I  resolves with  V7  to  I6/4  using  PAC."
    cleaned = clean_text_preserving_music(sample)
    assert "ii-V-I" in cleaned
    assert "V7" in cleaned
    assert "I6/4" in cleaned
    assert "PAC" in cleaned

def test_chunk_document_pages_page_preservation():
    pages = [
        {"page_number": 1, "text": "Page one text on Major Triads: C - E - G.", "section": "Chapter 1"},
        {"page_number": 2, "text": "Page two text on Minor Triads: A - C - E.", "section": "Chapter 2"}
    ]
    chunks = chunk_document_pages(
        pages=pages,
        document_id="test_doc",
        document_title="Test Treatise",
        author="Test Theorist",
        chunk_size=500
    )
    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].document_title == "Test Treatise"
    assert chunks[1].page_number == 2
    assert "Minor Triads" in chunks[1].content

def test_chunk_text():
    raw_text = "Diatonic harmony is based on scale degrees.\n\nSecondary dominants enrich harmonic syntax."
    chunks = chunk_text(
        text=raw_text,
        document_id="doc_single",
        document_title="Single Page Document"
    )
    assert len(chunks) >= 1
    assert chunks[0].chunk_id.startswith("doc_single_")
    assert chunks[0].page_number == 1
