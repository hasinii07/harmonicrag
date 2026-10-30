import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.rag.ingestion import ingestion_manager

def main():
    docs_dir = settings.documents_dir
    print(f"Scanning canonical documents directory: {docs_dir}")

    files = list(docs_dir.glob("*.pdf")) + list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.txt"))
    if not files:
        print("No documents found in documents directory.")
        return

    print(f"Found {len(files)} document(s) to process.\n")
    for file_path in files:
        print(f"Ingesting: {file_path.name}...")
        try:
            author = "Unknown"
            title = file_path.stem.replace('_', ' ').title()
            name_lower = file_path.name.lower()

            if "carnatic" in name_lower:
                author = "Purandara Dasa & Classical Indian Musicology"
                title = "Carnatic Music Theory and History"
            elif "fundamentals" in name_lower:
                author = "Music Theory Educational Reference"
                title = "Western Music Theory Fundamentals"
            elif "rhythm" in name_lower and "form" in name_lower:
                author = "Rhythm and Formal Analysis Guide"
                title = "Rhythm, Meter, and Musical Form"
            elif "harmony_and_voice_leading_study" in name_lower:
                author = "Voice Leading Reference Guide"
                title = "Harmony and Voice Leading Study Notes"
            elif "questions_and_analysis" in name_lower:
                author = "Music Theory Examination & Comparative Analysis"
                title = "Music Theory Questions and Analysis"
            elif "richter" in name_lower:
                author = "Ernst Friedrich Richter"
                title = "A Manual of Harmony"
            elif "macpherson" in name_lower and "rudiments" in name_lower:
                author = "Stewart Macpherson"
                title = "The Rudiments of Music"
            elif "aldwell" in name_lower:
                author = "Edward Aldwell & Carl Schachter"
                title = "Harmony and Voice Leading"
            elif "form" in name_lower:
                author = "Stewart Macpherson"
                title = "Form in Music"
            elif "prout" in name_lower:
                author = "Ebenezer Prout"
                title = "Harmony: Its Theory and Practice"

            meta = ingestion_manager.ingest_file(
                file_path=file_path,
                title=title,
                author=author
            )
            print(f"  -> SUCCESS: doc_id={meta.id}, pages={meta.page_count}, chunks={meta.chunk_count}, type={meta.file_type}")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    print("\nIngestion completed!")
    print(f"Total documents registered: {len(ingestion_manager.documents)}")

if __name__ == "__main__":
    main()
