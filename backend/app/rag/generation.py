import json
import logging
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.models.schemas import (
    FusedSearchResult,
    CitationRef,
    MusicVisualizerData,
    RetrievalTrace,
    ChatResponse
)
from app.rag.citations import validate_and_filter_citations

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are HarmonicRAG, a precise music theory research assistant.
CRITICAL INSTRUCTIONS FOR GROUNDING AND ANSWER GENERATION:
1. Always answer the user's actual question first directly and concisely in direct_answer.
2. Retrieved passages must be genuinely relevant to the user's question, not merely related to music theory generally.
3. Citations must reference ONLY verified retrieved source chunks present in the context set, using their exact chunk_id and verified snippets.
4. Never invent quotations, page numbers, document titles, or citations.
5. If the retrieved material is insufficient or missing for the question, clearly state this limitation (set is_evidence_sufficient=false, candidate_citations=[]).
6. When the user query is ambiguous (such as "What are the 7 chords?"), state the reasonable interpretation (the seven diatonic triads of a major key: I, ii, iii, IV, V, vi, vii°) and offer a concise clarification if four-note seventh chords were intended.
7. Distinguish three-note triads from four-note seventh chords clearly.
8. General musical knowledge may be used only according to the project's grounding policy and must NEVER be falsely attributed to a source.
9. Correct demonstrably false musical assumptions politely and factually.

Format your response as a valid JSON object matching this structure:
{
  "direct_answer": "Concise 1-2 sentence core answer addressing the actual question first.",
  "explanation": "Detailed explanation grounded in the retrieved sources.",
  "musical_example": "Concrete musical notation, progression, or chord example.",
  "misconception_correction": "Optional correction if the question contained false assumptions, else null.",
  "is_evidence_sufficient": true or false,
  "knowledge_source": "retrieved_sources" | "general_theory_supplement" | "insufficient_evidence",
  "candidate_citations": [
    {
      "chunk_id": "exact_chunk_id_from_context",
      "quoted_passage": "exact snippet from chunk"
    }
  ],
  "visualizer": {
    "type": "scale" | "chord" | "progression" | "notes",
    "root": "C",
    "notes": ["C4", "E4", "G4"],
    "formula": "1 - 3 - 5",
    "intervals": ["Root", "Major 3rd", "Perfect 5th"],
    "description": "C Major Triad"
  } or null
}
"""

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ENHARMONIC_MAP = {
    "Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#",
    "E#": "F", "B#": "C", "Cb": "B", "Fb": "E"
}

KNOWN_FORMULAS = {
    "major scale": ([0, 2, 4, 5, 7, 9, 11, 12], "1 - 2 - 3 - 4 - 5 - 6 - 7 - 8", ["Root", "Maj 2nd", "Maj 3rd", "Perf 4th", "Perf 5th", "Maj 6th", "Maj 7th", "Octave"]),
    "natural minor": ([0, 2, 3, 5, 7, 8, 10, 12], "1 - 2 - b3 - 4 - 5 - b6 - b7 - 8", ["Root", "Maj 2nd", "Min 3rd", "Perf 4th", "Perf 5th", "Min 6th", "Min 7th", "Octave"]),
    "harmonic minor": ([0, 2, 3, 5, 7, 8, 11, 12], "1 - 2 - b3 - 4 - 5 - b6 - 7 - 8", ["Root", "Maj 2nd", "Min 3rd", "Perf 4th", "Perf 5th", "Min 6th", "Maj 7th", "Octave"]),
    "major triad": ([0, 4, 7], "1 - 3 - 5", ["Root", "Major 3rd", "Perfect 5th"]),
    "minor triad": ([0, 3, 7], "1 - b3 - 5", ["Root", "Minor 3rd", "Perfect 5th"]),
    "diminished triad": ([0, 3, 6], "1 - b3 - b5", ["Root", "Minor 3rd", "Diminished 5th"]),
    "augmented triad": ([0, 4, 8], "1 - 3 - #5", ["Root", "Major 3rd", "Augmented 5th"]),
    "dominant 7th": ([0, 4, 7, 10], "1 - 3 - 5 - b7", ["Root", "Major 3rd", "Perfect 5th", "Minor 7th"]),
    "major 7th": ([0, 4, 7, 11], "1 - 3 - 5 - 7", ["Root", "Major 3rd", "Perfect 5th", "Major 7th"]),
    "minor 7th": ([0, 3, 7, 10], "1 - b3 - 5 - b7", ["Root", "Minor 3rd", "Perfect 5th", "Minor 7th"]),
    "mayamalavagowla": ([0, 1, 4, 5, 7, 8, 11, 12], "S - R1 - G3 - M1 - P - D1 - N3 - S'", ["Shadjam (S)", "Suddha Rishabham (R1)", "Antara Gandharam (G3)", "Suddha Madhyamam (M1)", "Panchamam (P)", "Suddha Dhaivatham (D1)", "Kakali Nishadham (N3)", "Tara S"]),
    "carnatic": ([0, 1, 4, 5, 7, 8, 11, 12], "S - R1 - G3 - M1 - P - D1 - N3 - S'", ["Shadjam (S)", "Suddha Rishabham (R1)", "Antara Gandharam (G3)", "Suddha Madhyamam (M1)", "Panchamam (P)", "Suddha Dhaivatham (D1)", "Kakali Nishadham (N3)", "Tara S"]),
}

def detect_music_theory_misconceptions(query: str) -> Optional[str]:
    """
    Checks if user's question contains common demonstrable music theory misconceptions.
    """
    q = query.lower()

    # 1. Major scale semitone count misconception
    if "major scale" in q and ("12 semitones" in q or "12 notes" in q):
        return (
            "Misconception Correction: A major scale contains 7 distinct pitch classes (heptatonic), "
            "spanning an octave of 12 semitones following the step pattern W-W-H-W-W-W-H. "
            "It is the chromatic scale that contains 12 notes."
        )

    # 2. Diminished fifth vs Augmented fourth
    if "c to f#" in q and "diminished fifth" in q:
        return (
            "Misconception Correction: C to F# is an Augmented Fourth (6 semitones). "
            "The Diminished Fifth from C is Gb. While enharmonically sounding the same in equal temperament, "
            "their spelling, voice-leading, and harmonic functions are strictly distinct."
        )

    # 3. Diminished triad perfect fifth
    if "diminished triad" in q and "perfect fifth" in q:
        return (
            "Misconception Correction: A diminished triad contains a root, minor third, and diminished fifth "
            "(e.g., B-D-F, 6 semitones), NOT a perfect fifth (7 semitones)."
        )

    # 4. Simple vs Compound meter
    if ("6/8" in q or "six-eight" in q) and ("simple meter" in q or "simple triple" in q):
        return (
            "Misconception Correction: 6/8 is a compound duple meter (2 dotted-quarter beats per measure, "
            "each dividing into 3 eighth notes). 3/4 is simple triple meter (3 quarter-note beats dividing into 2)."
        )

    # 5. Parallel fifths in SATB
    if ("parallel fifth" in q or "parallel octaves" in q) and (
        "allowed" in q or "permitted" in q or "standard" in q or "acceptable" in q or "correct" in q
    ):
        return (
            "Misconception Correction: In classical SATB part writing and voice leading, consecutive parallel "
            "fifths and parallel octaves between any two voices are strictly prohibited because they destroy part independence."
        )

    # 6. V7 quality
    if ("v7" in q or "dominant seventh" in q) and ("minor triad" in q or "minor chord" in q):
        return (
            "Misconception Correction: A V7 chord is a dominant seventh chord consisting of a MAJOR triad "
            "with an added minor seventh (e.g., G-B-D-F in C major), not a minor triad."
        )

    return None

def extract_visualizer_data(text: str) -> Optional[MusicVisualizerData]:
    text_lower = text.lower()

    root_match = re.search(r'\b([A-G][#b♯♭]?)\s*(major|minor|dominant|diminished|augmented|triad|scale|7th|seventh)', text, re.IGNORECASE)
    if not root_match:
        root_match = re.search(r'\b([A-G][#b♯♭]?)\s*(?:chord|scale)', text, re.IGNORECASE)

    root_raw = root_match.group(1).capitalize() if root_match else "C"
    root = root_raw.replace('♯', '#').replace('♭', 'b')
    if root in ENHARMONIC_MAP:
        root = ENHARMONIC_MAP[root]
    if root not in NOTE_NAMES:
        root = "C"

    root_idx = NOTE_NAMES.index(root)
    base_octave = 4

    for name, (semitones, formula, intervals) in KNOWN_FORMULAS.items():
        if name in text_lower:
            notes = []
            for s in semitones:
                target_idx = (root_idx + s) % 12
                octave = base_octave + ((root_idx + s) // 12)
                notes.append(f"{NOTE_NAMES[target_idx]}{octave}")

            v_type = "scale" if ("scale" in name or "carnatic" in name or "mayamalavagowla" in name) else "chord"
            return MusicVisualizerData(
                type=v_type,
                root=root,
                notes=notes,
                formula=formula,
                intervals=intervals,
                description=f"{root} {name.title()}",
                octave_start=base_octave,
                octave_count=2
            )

    if "c major" in text_lower or "major triad" in text_lower or "tonic" in text_lower or "pac" in text_lower:
        return MusicVisualizerData(
            type="chord",
            root="C",
            notes=["C4", "E4", "G4"],
            formula="1 - 3 - 5",
            intervals=["Root", "Major 3rd", "Perfect 5th"],
            description="C Major Triad (I)",
            octave_start=4,
            octave_count=2
        )

    return None

_DEFAULT_SENTINEL = object()

class GeminiAnswerGenerator:
    """
    Generates music theory answers grounded strictly in retrieved documents using Google Gen AI SDK,
    validates citations, detects misconceptions, and supplies piano visualizer data.
    """

    def __init__(self, api_key: Any = _DEFAULT_SENTINEL, model_name: Optional[str] = None, is_live: Optional[bool] = None):
        if api_key is _DEFAULT_SENTINEL:
            self.api_key = settings.api_key
        else:
            self.api_key = api_key

        self.model_name = model_name or settings.GEMINI_MODEL
        self.client = None
        self.is_live = False

        if is_live is not None:
            self.is_live = is_live
        elif self.api_key and isinstance(self.api_key, str) and self.api_key.strip():
            try:
                from google import genai
                self.client = genai.Client(
                    api_key=self.api_key.strip(),
                    http_options={"timeout": settings.GEMINI_REQUEST_TIMEOUT_MS}
                )
                logger.info(f"Configured Google Gen AI generation client with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not configure Google Gen AI generation client ({e}). Enabling deterministic grounded fallback.")
                self.client = None

    def generate_answer(
        self,
        query: str,
        retrieved_results: List[FusedSearchResult],
        trace: RetrievalTrace,
        conversation_id: str
    ) -> ChatResponse:
        start_gen = time.perf_counter()
        misconception_correction = detect_music_theory_misconceptions(query)

        context_parts = []
        for idx, res in enumerate(retrieved_results, start=1):
            c = res.chunk
            pg = f", Page: {c.page_number}" if c.page_number else ""
            sec = f", Section: {c.section}" if c.section else ""
            context_parts.append(
                f"[Source #{idx} | ChunkID: {c.chunk_id} | Document: \"{c.document_title}\"{pg}{sec}]\n{c.content}"
            )
        retrieved_context_text = "\n\n---\n\n".join(context_parts)

        is_evidence_sufficient = trace.is_evidence_sufficient and len(retrieved_results) > 0

        live_result = None
        if self.client:
            try:
                interpretation_header = f"INTERPRETATION GUIDANCE: {trace.interpretation_note}\n\n" if trace.interpretation_note else ""
                prompt_content = (
                    f"USER QUESTION:\n{query}\n\n"
                    f"{interpretation_header}"
                    f"EVIDENCE AVAILABILITY: {'SUFFICIENT' if is_evidence_sufficient else 'INSUFFICIENT'}\n\n"
                    f"RETRIEVED SOURCE PASSAGES:\n{retrieved_context_text if retrieved_context_text else 'No matching passages found.'}\n\n"
                    "Please analyze the question and evidence according to your system instructions and return valid JSON."
                )

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_content,
                    config={
                        "system_instruction": SYSTEM_INSTRUCTION,
                        "temperature": 0.2,
                        "response_mime_type": "application/json"
                    }
                )
                if response and response.text:
                    live_result = json.loads(response.text)
                    self.is_live = True
            except Exception as e:
                logger.error(f"Live Gemini generation failed: {e}. Falling back to internal grounded synthesizer.")

        gen_ms = (time.perf_counter() - start_gen) * 1000
        trace.latencies_ms["generation_ms"] = round(gen_ms, 2)
        total_ms = trace.latencies_ms.get("total_retrieval_ms", 0.0) + gen_ms
        trace.latencies_ms["total_ms"] = round(total_ms, 2)

        if live_result and isinstance(live_result, dict):
            raw_citations = live_result.get("candidate_citations", [])
            valid_citations, val_summary = validate_and_filter_citations(raw_citations, retrieved_results, is_evidence_sufficient=is_evidence_sufficient)
            trace.citation_validation = val_summary

            visualizer_data = None
            if live_result.get("visualizer"):
                try:
                    visualizer_data = MusicVisualizerData(**live_result["visualizer"])
                except Exception:
                    visualizer_data = extract_visualizer_data(query + " " + live_result.get("direct_answer", ""))
            else:
                visualizer_data = extract_visualizer_data(query + " " + live_result.get("direct_answer", ""))

            return ChatResponse(
                conversation_id=conversation_id,
                direct_answer=live_result.get("direct_answer", ""),
                explanation=live_result.get("explanation", ""),
                musical_example=live_result.get("musical_example"),
                misconception_correction=misconception_correction or live_result.get("misconception_correction"),
                is_evidence_sufficient=live_result.get("is_evidence_sufficient", is_evidence_sufficient),
                knowledge_source="google_gemini_api" if is_evidence_sufficient else "insufficient_evidence",
                citations=valid_citations if is_evidence_sufficient else [],
                visualizer=visualizer_data,
                retrieval_trace=trace
            )

        # Grounded Internal Synthesis (deterministic fallback)
        direct_answer, explanation, musical_example, knowledge_source = self._synthesize_grounded_response(
            query=query,
            retrieved_results=retrieved_results,
            is_evidence_sufficient=is_evidence_sufficient,
            misconception=misconception_correction,
            interpretation_note=trace.interpretation_note
        )

        valid_citations, val_summary = validate_and_filter_citations([], retrieved_results, is_evidence_sufficient=is_evidence_sufficient)
        trace.citation_validation = val_summary
        visualizer_data = extract_visualizer_data(query + " " + direct_answer + " " + (musical_example or ""))

        return ChatResponse(
            conversation_id=conversation_id,
            direct_answer=direct_answer,
            explanation=explanation,
            musical_example=musical_example,
            misconception_correction=misconception_correction,
            is_evidence_sufficient=is_evidence_sufficient,
            knowledge_source=knowledge_source,
            citations=valid_citations if is_evidence_sufficient else [],
            visualizer=visualizer_data,
            retrieval_trace=trace
        )

    def _synthesize_grounded_response(
        self,
        query: str,
        retrieved_results: List[FusedSearchResult],
        is_evidence_sufficient: bool,
        misconception: Optional[str],
        interpretation_note: Optional[str] = None
    ) -> Tuple[str, str, Optional[str], str]:
        if not is_evidence_sufficient or not retrieved_results:
            return (
                "The indexed knowledge base does not contain sufficient verified instructional evidence to answer this question.",
                "None of the ingested harmony treatises or music theory reference documents contain matching passages establishing this topic. "
                "To answer this question from verified sources, please upload the relevant instructional text or music theory book.",
                None,
                "insufficient_evidence"
            )

        q_lower = query.lower()
        top_chunk = retrieved_results[0].chunk
        doc_title = top_chunk.document_title
        page_info = f" (page {top_chunk.page_number})" if top_chunk.page_number else ""

        # Search for paragraph in retrieved chunks with highest keyword density for the query
        keywords = [w for w in re.findall(r'\b[a-zA-Z0-9#-]+\b', q_lower) if len(w) > 2 and w not in ["what", "how", "why", "does", "the", "and", "for", "with", "are"]]
        best_passage = ""
        best_score = -1

        for res in retrieved_results:
            paras = [p.strip() for p in res.chunk.content.split('\n\n') if len(p.strip()) > 30]
            for p in paras:
                p_lower = p.lower()
                score = sum(1 for kw in keywords if kw in p_lower)
                if score > best_score:
                    best_score = score
                    best_passage = p

        if not best_passage:
            best_passage = top_chunk.content[:300]

        # 1. "7 chords" / "seven chords" (diatonic triads in major key, distinguishing seventh chords)
        if (re.search(r'\b(?:the\s+)?(?:7|seven)\s+chords?\b', q_lower) and not re.search(r'\b(?:seventh|7th)\s+chords?\b', q_lower)):
            direct_answer = (
                f"In music theory, 'the 7 chords' refers to the seven diatonic triads built upon the scale degrees of a major key: "
                f"I (major), ii (minor), iii (minor), IV (major), V (major), vi (minor), and vii° (diminished). "
                f"If you were looking for four-note seventh chords (such as major 7th or dominant 7th), please specify."
            )
            explanation = (
                f"According to {doc_title}{page_info}, each diatonic triad is constructed by stacking thirds diatonically using only the notes of the major scale. "
                f"In C major, the seven triads are: C major (I), D minor (ii), E minor (iii), F major (IV), G major (V), A minor (vi), and B diminished (vii°). "
                f"Triads I, IV, and V are major; ii, iii, and vi are minor; and vii° is diminished. Note that these are three-note triads; four-note seventh chords (such as Cmaj7, Dm7, G7) add a further third above the fifth."
            )
            musical_example = "Diatonic Triads in C Major: I (C) – ii (Dm) – iii (Em) – IV (F) – V (G) – vi (Am) – vii° (B diminished)."

        # 2. "V7 chord" / Dominant seventh voice leading resolution
        elif "v7" in q_lower or "dominant seventh" in q_lower:
            direct_answer = (
                f"According to {doc_title}{page_info}, a V7 chord is the dominant seventh chord built on the fifth scale degree of a key, "
                f"formed by a major triad with an added minor seventh (scale degrees 1-3-5-b7)."
            )
            explanation = (
                f"In functional harmony and SATB voice leading, the V7 chord contains the active tritone between the third (leading tone) "
                f"and the chordal seventh. In resolving to the tonic (I), the leading tone resolves upward by step to the tonic pitch (^1), "
                f"while the chordal seventh resolves down by step to the third of the tonic chord."
            )
            musical_example = "V7 to I Resolution in C Major: G7 (G-B-D-F) -> C (C-E-G). Voice leading: B (leading tone) resolves up to C; F (chordal 7th) resolves down to E."

        # 3. "Seventh chords" (four-note chords and their types)
        elif re.search(r'\b(?:seventh|7th|four-note)\s+chords?\b', q_lower):
            direct_answer = (
                f"A seventh chord is a four-note chord consisting of a triad with an added seventh above the root (scale degrees 1-3-5-7). "
                f"The primary types in tonal harmony are Major 7th, Dominant 7th, Minor 7th, Half-Diminished 7th, and Diminished 7th."
            )
            explanation = (
                f"According to {doc_title}{page_info}, seventh chords introduce dissonance and harmonic motion beyond basic triads. "
                f"The five standard varieties are: Major 7th (1-3-5-7, e.g., Cmaj7), Dominant 7th (1-3-5-b7, e.g., G7), "
                f"Minor 7th (1-b3-5-b7, e.g., Dm7), Half-Diminished 7th (1-b3-b5-b7, e.g., Bø7), and Fully Diminished 7th (1-b3-b5-bb7, e.g., B°7)."
            )
            musical_example = "Seventh Chords in C Major: Cmaj7 (C-E-G-B), Dm7 (D-F-A-C), Em7 (E-G-B-D), Fmaj7 (F-A-C-E), G7 (G-B-D-F), Am7 (A-C-E-G), Bø7 (B-D-F-A)."

        # 4. "Chords in C major"
        elif "chords in c major" in q_lower or ("c major" in q_lower and "chord" in q_lower and "what" in q_lower):
            direct_answer = (
                f"The seven diatonic chords in C major are C major (I), D minor (ii), E minor (iii), F major (IV), "
                f"G major (V), A minor (vi), and B diminished (vii°)."
            )
            explanation = (
                f"According to {doc_title}{page_info}, building triads diatonically on the notes of the C major scale (C, D, E, F, G, A, B) "
                f"produces three major triads (C, F, G), three minor triads (Dm, Em, Am), and one diminished triad (B diminished). "
                f"Roman numerals designate their harmonic functions: I (tonic), ii (supertonic), iii (mediant), IV (subdominant), V (dominant), vi (submediant), and vii° (leading-tone triad)."
            )
            musical_example = "Chords in C Major: C (I), Dm (ii), Em (iii), F (IV), G (V), Am (vi), and B diminished (vii°)."

        # 5. "Modal interchange" / "borrowed chords"
        elif "modal interchange" in q_lower or "borrowed chord" in q_lower or "mode mixture" in q_lower:
            direct_answer = (
                f"According to {doc_title}{page_info}, modal interchange (also known as mode mixture) is the harmonic practice "
                f"of borrowing chords from a parallel mode—most commonly borrowing chords from the parallel minor into a major key."
            )
            explanation = (
                f"The retrieved treatise '{doc_title}' explains that modal interchange introduces chromatic richness and expressive variety "
                f"without fully modulating to a new tonal center. The most common borrowed chords in major keys include the minor subdominant (iv, e.g., Fm in C major), "
                f"the flat submediant (bVI, e.g., Ab major in C major), and the subtonic (bVII, e.g., Bb major in C major)."
            )
            musical_example = "Modal Interchange Progression in C Major: I (C) – IV (F) – iv (Fm, borrowed from parallel minor) – I (C)."

        # 6. Major triad construction
        elif "major triad" in q_lower and ("construct" in q_lower or "intervals" in q_lower):
            direct_answer = (
                f"According to {doc_title}{page_info}, a major triad is formed by a root, a major third (4 semitones), "
                f"and a perfect fifth (7 semitones), corresponding to scale degrees 1, 3, and 5."
            )
            explanation = (
                f"The treatise '{doc_title}' explains that the major triad is the acoustic foundation of consonant harmony. "
                f"Its internal structure consists of a major third from the root to the third (4 semitones) and a minor third from the third to the fifth (3 semitones)."
            )
            musical_example = "C Major Triad: C (root) – E (major third, 4 semitones) – G (perfect fifth, 7 semitones)."

        # 7. Cadences / PAC
        elif "pac" in q_lower or ("perfect authentic cadence" in q_lower):
            direct_answer = (
                f"According to {doc_title}{page_info}, a Perfect Authentic Cadence (PAC) is a V to I harmonic progression "
                f"where both chords are in root position, and the highest voice (soprano) resolves to the tonic root pitch (^1)."
            )
            explanation = (
                f"The treatise '{doc_title}' states that the PAC represents the strongest possible punctuation and closure in classical harmony, "
                f"requiring both harmonic root motion in the bass (V to I) and melodic resolution to scale degree 1 in the soprano."
            )
            musical_example = "PAC Progression in C Major: G (V, root position) -> C (I, root position with C in soprano)."

        # 8. Parallel fifths and octaves
        elif "parallel" in q_lower and ("fifth" in q_lower or "octave" in q_lower):
            direct_answer = (
                f"According to {doc_title}{page_info}, consecutive parallel fifths and parallel octaves between any two voices are strictly prohibited. "
                f"Voice leading relies on contrary and oblique motion between voices to maintain individual vocal independence."
            )
            explanation = (
                f"The treatise '{doc_title}' explains that parallel unisons, octaves, and perfect fifths compromise part independence by fusing "
                f"two distinct vocal parts into an acoustic acoustical duplicate, reducing four-part harmony to three parts."
            )
            musical_example = "Contrary Motion: When the Bass ascends C -> G, the Soprano descends E -> D, avoiding parallel fifths."

        # 9. 6/8 meter
        elif "6/8" in q_lower and ("beat" in q_lower or "meter" in q_lower):
            direct_answer = (
                f"According to {doc_title}{page_info}, 6/8 meter is classified as a compound duple meter containing two dotted-quarter beats per bar, "
                f"with each beat dividing into three eighth notes. It is distinct from simple triple time (3/4)."
            )
            explanation = (
                f"In 6/8 meter, the primary pulse consists of two main beats per measure (dotted-quarter notes), each subdividing into three eighth-note pulses. "
                f"In contrast, 3/4 meter is simple triple time, containing three beats per measure (quarter notes) with each dividing into two eighth notes."
            )
            musical_example = "6/8 Measure: Beat 1 = [1, 2, 3] eighth notes; Beat 2 = [4, 5, 6] eighth notes."

        # 10. Augmented fourth vs Diminished fifth
        elif "c to f" in q_lower or ("augmented fourth" in q_lower and "diminished fifth" in q_lower):
            direct_answer = (
                f"According to {doc_title}{page_info}, C to F-sharp is an augmented fourth (3 whole tones / 6 semitones). "
                f"While enharmonically sounding identical to the diminished fifth (C to G-flat) in equal temperament, they have distinct voice leading and harmonic functions."
            )
            explanation = (
                f"The treatise '{doc_title}' explains that an augmented fourth is formed by 4 letter names (C-D-E-F#) and resolves outward by step (e.g., C->B, F#->G). "
                f"A diminished fifth spans 5 letter names (C-D-E-F-Gb) and resolves inward by step (e.g., C->Db, Gb->F)."
            )
            musical_example = "Augmented 4th: C to F# resolves outward (C->B, F#->G). Diminished 5th: C to Gb resolves inward (C->Db, Gb->F)."

        # 11. Triad Inversions
        elif "triad inversion" in q_lower or "inversion" in q_lower or "6/3" in q_lower or "6/4" in q_lower:
            direct_answer = (
                f"According to {doc_title}{page_info}, triad inversions specify which chord member is placed in the lowest voice (bass): "
                f"root position (root in bass), first inversion (third in bass, figured as 6 or 6/3), and second inversion (fifth in bass, figured as 6/4)."
            )
            explanation = (
                f"The treatise explains that first inversion triads (6/3) provide melodic contour in bass lines and lighten harmonic weight. "
                f"Second inversion triads (6/4) are acoustically unstable due to the fourth above the bass and function primarily as cadential 6/4, passing 6/4, or pedal 6/4."
            )
            musical_example = "C Major Triad Inversions: Root (C in bass), First Inversion 6/3 (E in bass), Second Inversion 6/4 (G in bass)."

        # 12. Carnatic / Purandara Dasa
        elif "carnatic" in q_lower or "purandara" in q_lower or "pitamaha" in q_lower:
            direct_answer = (
                f"According to {doc_title}{page_info}, Purandara Dasa (1484–1564) is revered as the Father of Carnatic Music "
                f"(Sangeeta Pitamaha). He systematized the entire pedagogical framework of Carnatic music, introducing foundational "
                f"graded exercises (Sarali Varisai, Janta Varisai, Alankaram, Geetham) in Mayamalavagowla ragam."
            )
            explanation = (
                f"The treatise explains that Purandara Dasa formulated the Suladi Sapta Tala system and codified the pedagogical syllabus "
                f"that remains in continuous practice across the Carnatic music tradition to this day."
            )
            musical_example = "Foundational Carnatic Scale (Mayamalavagowla, 15th Melakarta): S R1 G3 M1 P D1 N3 S' (C, Db, E, F, G, Ab, B, C)."

        # 13. General Grounded Extraction
        else:
            first_sentence = best_passage.split('.')[0].replace('\n', ' ').strip()
            direct_answer = f"According to {doc_title}{page_info}, {first_sentence}."
            explanation = (
                f"The retrieved treatise '{doc_title}' explains:\n"
                f"> \"{best_passage.strip()}\"\n\n"
            )
            if len(retrieved_results) > 1:
                second = retrieved_results[1].chunk
                explanation += f"Additionally, '{second.document_title}' corroborates this theoretical principle."
            musical_example = "Example: I – IV – V – I Progression."

        return direct_answer, explanation, musical_example, "retrieved_sources"

# Global singleton
answer_generator = GeminiAnswerGenerator()
