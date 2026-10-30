import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontSize=20, leading=24, textColor=colors.navy, spaceAfter=12
)
heading2_style = ParagraphStyle(
    'DocHeading2',
    parent=styles['Heading2'],
    fontSize=14, leading=18, textColor=colors.darkblue, spaceBefore=10, spaceAfter=6
)
heading3_style = ParagraphStyle(
    'DocHeading3',
    parent=styles['Heading3'],
    fontSize=11, leading=15, textColor=colors.HexColor("#1e3a8a"), spaceBefore=8, spaceAfter=4
)
body_style = ParagraphStyle(
    'DocBody',
    parent=styles['BodyText'],
    fontSize=9.5, leading=13.5, spaceAfter=6
)

# ==============================================================================
# PDF 1: Western Theory Fundamentals Study Notes
# ==============================================================================
def create_western_fundamentals_pdf():
    pdf_path = DOCS_DIR / "western_music_theory_fundamentals_study_notes.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = [
        Paragraph("Western Music Theory Fundamentals: Study Notes", title_style),
        Paragraph("<b>Subject:</b> Pitch, Staves, Clefs, Diatonic Scales, and Intervals | <i>Educational Reference Guide</i>", body_style),
        Spacer(1, 10),
        Paragraph("Section 1: Pitch, Staff Notation, and Clefs", heading2_style),
        Paragraph("Musical sounds are graphically recorded on a five-line staff. The pitch of a tone indicates its frequency of vibration.", body_style),
        Paragraph("<b>Clefs:</b><br/>"
                  "• <b>Treble Clef (G Clef):</b> Loops around the second line, establishing it as G4 (392 Hz), immediately above middle C.<br/>"
                  "• <b>Bass Clef (F Clef):</b> Two dots surround the fourth line, fixing it as F3 (174.6 Hz), directly below middle C.<br/>"
                  "• <b>Alto Clef (C Clef):</b> The center indentation defines middle C (C4) on the third line (used primarily for viola).<br/>"
                  "• <b>Tenor Clef (C Clef):</b> Indentation places middle C (C4) on the fourth line (used for cello, trombone, bassoon in high registers).", body_style),
        Paragraph("<b>Scientific Pitch Notation:</b> Middle C is designated C4. Octaves run from C to B. The octave below middle C is octave 3 (C3 to B3); the octave above is octave 5 (C5 to B5).", body_style),
        PageBreak(),

        Paragraph("Section 2: Diatonic Major and Minor Scales", heading2_style),
        Paragraph("A diatonic scale consists of seven distinct pitch classes arranged in alphabetical order within an octave.", body_style),
        Paragraph("<b>The Major Scale Formula:</b><br/>"
                  "The major scale follows the invariant sequence: <b>Tone – Tone – Semitone – Tone – Tone – Tone – Semitone</b> (W – W – H – W – W – W – H).<br/>"
                  "Semitones occur naturally between scale degrees 3–4 and 7–8. Scale degree names are: 1 Tonic, 2 Supertonic, 3 Mediant, 4 Subdominant, 5 Dominant, 6 Submediant, 7 Leading Tone.", body_style),
        Paragraph("<b>Minor Scale Forms:</b><br/>"
                  "• <b>Natural Minor:</b> Step pattern W – H – W – W – H – W – W (1 – 2 – b3 – 4 – 5 – b6 – b7).<br/>"
                  "• <b>Harmonic Minor:</b> The 7th degree is raised by one semitone both ascending and descending (1 – 2 – b3 – 4 – 5 – b6 – 7). This creates an augmented second (3 semitones) between degrees 6 and 7, establishing a half-step leading tone resolution to the tonic.<br/>"
                  "• <b>Melodic Minor:</b> Ascending, both 6th and 7th degrees are raised (1 – 2 – b3 – 4 – 5 – 6 – 7); descending, it reverts to the natural minor scale.", body_style),
        PageBreak(),

        Paragraph("Section 3: Intervals and Semitone Calculations", heading2_style),
        Paragraph("An interval measures the distance between two pitches reckoned upwards from the lower note. Intervals are classified by numerical size and quality (Perfect, Major, Minor, Augmented, Diminished).", body_style),
        Paragraph("<b>Table of Standard Intervals by Semitones:</b><br/>"
                  "• Perfect Unison: 0 semitones<br/>"
                  "• Minor Second: 1 semitone (e.g. C to Db)<br/>"
                  "• Major Second: 2 semitones (e.g. C to D)<br/>"
                  "• Minor Third: 3 semitones (e.g. C to Eb)<br/>"
                  "• Major Third: 4 semitones (e.g. C to E)<br/>"
                  "• Perfect Fourth: 5 semitones (e.g. C to F)<br/>"
                  "• Augmented Fourth / Diminished Fifth (Tritone): 6 semitones (e.g. C to F# is Augmented 4th; C to Gb is Diminished 5th)<br/>"
                  "• Perfect Fifth: 7 semitones (e.g. C to G)<br/>"
                  "• Minor Sixth: 8 semitones (e.g. C to Ab)<br/>"
                  "• Major Sixth: 9 semitones (e.g. C to A)<br/>"
                  "• Minor Seventh: 10 semitones (e.g. C to Bb)<br/>"
                  "• Major Seventh: 11 semitones (e.g. C to B)<br/>"
                  "• Perfect Octave: 12 semitones (e.g. C to C)", body_style)
    ]
    doc.build(story)
    print("Created:", pdf_path.name)

# ==============================================================================
# PDF 2: Harmony and Voice Leading Study Notes
# ==============================================================================
def create_harmony_voice_leading_pdf():
    pdf_path = DOCS_DIR / "harmony_and_voice_leading_study_notes.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = [
        Paragraph("Harmony and Voice Leading: Study Notes", title_style),
        Paragraph("<b>Subject:</b> Triad Qualities, Inversions, SATB Part Writing, and Cadences", body_style),
        Spacer(1, 10),
        Paragraph("Chapter 1: Triad Construction and Inversions", heading2_style),
        Paragraph("A triad consists of three tones stacked in thirds above a fundamental root tone: the root, third, and fifth.", body_style),
        Paragraph("<b>The Four Triad Qualities:</b><br/>"
                  "1. <b>Major Triad:</b> Root, Major 3rd (4 semitones), Perfect 5th (7 semitones). Example: C – E – G.<br/>"
                  "2. <b>Minor Triad:</b> Root, Minor 3rd (3 semitones), Perfect 5th (7 semitones). Example: A – C – E, D – F – A.<br/>"
                  "3. <b>Diminished Triad:</b> Root, Minor 3rd (3 semitones), Diminished 5th (6 semitones). Example: B – D – F. Note: Contains a diminished fifth, NOT a perfect fifth.<br/>"
                  "4. <b>Augmented Triad:</b> Root, Major 3rd (4 semitones), Augmented 5th (8 semitones). Example: C – E – G#.", body_style),
        Paragraph("<b>Inversions & Figured Bass:</b><br/>"
                  "• <b>Root Position (5/3):</b> Root in bass. Denoted I, V, IV.<br/>"
                  "• <b>First Inversion (6/3 or 6):</b> Third of chord in bass. Intervals above bass are a 3rd and 6th. Denoted I6, V6, ii6.<br/>"
                  "• <b>Second Inversion (6/4):</b> Fifth of chord in bass. Intervals above bass are a 4th and 6th. Denoted I6/4 (cadential 6/4).", body_style),
        PageBreak(),

        Paragraph("Chapter 2: SATB Voice Leading Laws", heading2_style),
        Paragraph("Four-part choral writing utilizes Soprano, Alto, Tenor, and Bass voices (SATB). Good voice leading preserves melodic contour and independence.", body_style),
        Paragraph("<b>Strict Prohibition of Consecutive Parallel Fifths and Octaves:</b><br/>"
                  "In classical four-part SATB writing, consecutive parallel fifths and parallel octaves between any two voices are strictly prohibited. "
                  "When two voices move in parallel motion by fifths or octaves, their independent acoustic identity is destroyed. "
                  "Part writers prevent parallel motion primarily by employing contrary motion (voices moving in opposite directions).", body_style),
        Paragraph("<b>Leading Tone Resolution:</b> The leading tone (^7) possesses a strong upward melodic tendency and must resolve upward by step to the tonic (^1), particularly in outer soprano/bass voices.", body_style),
        PageBreak(),

        Paragraph("Chapter 3: Harmonic Cadences and Progressions", heading2_style),
        Paragraph("A cadence punctuates musical phrases and articulates formal structure.", body_style),
        Paragraph("<b>The Four Core Cadence Types:</b><br/>"
                  "1. <b>Perfect Authentic Cadence (PAC):</b> Dominant to Tonic progression (V to I). Both chords must be in root position, and the soprano voice must finish on the tonic root (^1). This is the most conclusive cadence in tonal music.<br/>"
                  "2. <b>Imperfect Authentic Cadence (IAC):</b> V to I cadence where either chord is inverted (e.g. V6 to I), or the soprano ends on scale degree ^3 or ^5.<br/>"
                  "3. <b>Half Cadence (HC):</b> Pauses on the Dominant chord (V), preceded by I, ii, or IV. It leaves the phrase open and expectant.<br/>"
                  "4. <b>Deceptive Cadence (DC):</b> The dominant V resolves unexpectedly to the submediant vi (or VI in minor), interrupting expected tonic arrival.", body_style),
        Paragraph("<b>Dominant Seventh (V7) Voice Leading:</b> In resolving V7 to I: the leading tone (3rd of V7) resolves up by step to ^1; the chordal 7th resolves down by step to ^3; the 5th steps down to ^1; and the bass root leaps from ^5 to ^1.", body_style)
    ]
    doc.build(story)
    print("Created:", pdf_path.name)

# ==============================================================================
# PDF 3: Rhythm, Meter, and Form Study Notes
# ==============================================================================
def create_rhythm_form_pdf():
    pdf_path = DOCS_DIR / "rhythm_meter_and_musical_form_study_notes.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = [
        Paragraph("Rhythm, Meter, and Musical Form: Study Notes", title_style),
        Paragraph("<b>Subject:</b> Metric Organization, Phrase Construction, and Structural Designs", body_style),
        Spacer(1, 10),
        Paragraph("Chapter 1: Meter and Time Signatures", heading2_style),
        Paragraph("Meter represents the recurring grouping of pulses into accented and unaccented beats.", body_style),
        Paragraph("<b>Simple Meter vs. Compound Meter:</b><br/>"
                  "• <b>Simple Meter:</b> Each beat divides naturally into <b>two equal parts</b>.<br/>"
                  "  - <i>Simple Duple:</i> 2/4 (two quarter-note beats per measure).<br/>"
                  "  - <i>Simple Triple:</i> 3/4 (three quarter-note beats per measure).<br/>"
                  "  - <i>Simple Quadruple:</i> 4/4 or Common Time (four quarter-note beats per measure).<br/>"
                  "• <b>Compound Meter:</b> Each beat is a dotted note that divides naturally into <b>three equal parts</b>.<br/>"
                  "  - <i>Compound Duple:</i> 6/8. It consists of <b>two dotted-quarter beats</b> per measure, each dividing into three eighth notes. It is NOT simple triple meter.<br/>"
                  "  - <i>Compound Triple:</i> 9/8 (three dotted-quarter beats per measure).<br/>"
                  "  - <i>Compound Quadruple:</i> 12/8 (four dotted-quarter beats per measure).", body_style),
        PageBreak(),

        Paragraph("Chapter 2: Elements of Musical Form", heading2_style),
        Paragraph("Musical architecture balances repetition, contrast, and variation.", body_style),
        Paragraph("<b>The Motive, Phrase, and Period:</b><br/>"
                  "• <b>Motive:</b> The smallest identifiable rhythmic and melodic fragment of musical thought.<br/>"
                  "• <b>Phrase:</b> A complete melodic thought (typically 4 measures) culminating in a cadence.<br/>"
                  "• <b>Period:</b> A balanced pairing of two phrases: the <i>Antecedent</i> (ending in an inconclusive Half Cadence) and the <i>Consequent</i> (answering with a conclusive Perfect Authentic Cadence).", body_style),
        Paragraph("<b>Core Formal Structures:</b><br/>"
                  "• <b>Binary Form (AB):</b> Two balanced sections. Section A begins in tonic and cadences in dominant/relative key; Section B departs and journeys back to close in tonic.<br/>"
                  "• <b>Ternary Form (ABA):</b> Three-part structure. Section A (Statement in tonic) – Section B (Contrast in mood/key) – Section A (Reprise / return in tonic). Examples: Minuet and Trio, Da Capo aria.<br/>"
                  "• <b>Rondo Form (ABACA or ABACABA):</b> Recurrent alternation of a principal theme (refrain A in tonic) with contrasting episodes (B, C).", body_style)
    ]
    doc.build(story)
    print("Created:", pdf_path.name)

# ==============================================================================
# PDF 4: Carnatic Music Theory and History Study Notes
# ==============================================================================
def create_carnatic_music_pdf():
    pdf_path = DOCS_DIR / "carnatic_music_theory_and_history_study_notes.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = [
        Paragraph("Carnatic Music Theory and History: Study Notes", title_style),
        Paragraph("<b>Subject:</b> Sangeeta Pitamaha Purandara Dasa, Sapta Swaras, Melakarta Ragas, and Talas", body_style),
        Spacer(1, 10),
        Paragraph("Chapter 1: The Father of Carnatic Music — Purandara Dasa", heading2_style),
        Paragraph("<b>Purandara Dasa (c. 1484 – 1564 CE):</b><br/>"
                  "In the history of Indian classical music, <b>Purandara Dasa</b> is universally revered and acclaimed as the <b>Sangeeta Pitamaha</b> (the <b>Father of Carnatic Music</b>). "
                  "He was a saint-composer of the Haridasa tradition in Karnataka who systematized the entire foundation and pedagogy of South Indian classical music.", body_style),
        Paragraph("<b>Foundational Pedagogical Contributions of Purandara Dasa:</b><br/>"
                  "1. <b>The Graded Pedagogical Syllabus:</b> Purandara Dasa designed the standard graded exercises that every student of Carnatic music learns to this day: "
                  "<i>Sarali Varisais</i> (stepwise exercises), <i>Janta Varisais</i> (twinning exercises), <i>Dhatu Varisais</i> (zigzag patterns), <i>Alankaras</i> (tala exercises), and <i>Geethams</i> (simple melodic compositions).<br/>"
                  "2. <b>Selection of Mayamalavagowla:</b> He designated <b>Mayamalavagowla</b> (the 15th Melakarta ragam) as the foundational raga for beginners. "
                  "He chose Mayamalavagowla because of its symmetrical structure: both poorvanga (S-R1-G3-M1) and uttaranga (P-D1-N3-S') feature identical semitone intervals between Sa-Ri and Pa-Dha, making it ideal for vocal stability and ear training.<br/>"
                  "3. <b>Codification of the Suladi Sapta Talas:</b> He formulated the system of seven fundamental rhythmic cycles: Dhruva, Matya, Rupaka, Jhampa, Triputa, Ata, and Eka talas.<br/>"
                  "4. <b>Prolific Compositions:</b> He composed tens of thousands of devotional songs, Kritis, and Suladis (Devaranamas) embedding profound philosophical truths in simple musical expressions.", body_style),
        PageBreak(),

        Paragraph("Chapter 2: Core Theoretical Framework of Carnatic Music", heading2_style),
        Paragraph("<b>1. Nada, Sruti, and Swaras:</b><br/>"
                  "• <b>Nada:</b> Musical sound, originating as subtle inner vibration (Anahata) and realized as audible sound (Ahata).<br/>"
                  "• <b>Sruti:</b> The microtonal pitch interval. Carnatic music recognizes 22 distinct srutis within an octave.<br/>"
                  "• <b>The Sapta Swaras:</b> The seven basic musical notes:<br/>"
                  "  1. <b>Shadjam (Sa)</b> — Fundamental tonic (invariant, Achala swara).<br/>"
                  "  2. <b>Rishabham (Ri)</b> — Suddha Ri (R1), Chatusruti Ri (R2), Shatsruti Ri (R3).<br/>"
                  "  3. <b>Gandharam (Ga)</b> — Suddha Ga (G1), Sadharana Ga (G2), Antara Ga (G3).<br/>"
                  "  4. <b>Madhyamam (Ma)</b> — Suddha Ma (M1), Prati Ma (M2).<br/>"
                  "  5. <b>Panchamam (Pa)</b> — Fifth degree (invariant, Achala swara).<br/>"
                  "  6. <b>Dhaivatam (Dha)</b> — Suddha Dha (D1), Chatusruti Dha (D2), Shatsruti Dha (D3).<br/>"
                  "  7. <b>Nishadam (Ni)</b> — Suddha Ni (N1), Kaisiki Ni (N2), Kakali Ni (N3).<br/>"
                  "Together with Sa and Pa, these generate the 16 Swarasthanas.", body_style),
        Paragraph("<b>2. The Melakarta Raga Scheme:</b><br/>"
                  "Codified by Venkatamakhin in his treatise <i>Chaturdandi Prakasika</i> (17th century), the system comprises <b>72 Melakarta</b> (parent heptatonic) ragas. "
                  "They are systematically grouped into 12 Chakras of 6 ragas each. Ragas 1–36 use Suddha Madhyamam (M1); ragas 37–72 use Prati Madhyamam (M2). "
                  "Derived scales are known as <i>Janya ragas</i>.", body_style),
        PageBreak(),

        Paragraph("Chapter 3: Tala System and The Carnatic Trinity", heading2_style),
        Paragraph("<b>The Tala System:</b><br/>"
                  "Tala governs meter in Carnatic music. A tala consists of Angas (limbs):<br/>"
                  "• <b>Laghu (I):</b> A beat followed by finger counts. Can have 5 Jathis: Tisra (3), Chaturasra (4), Khanda (5), Misra (7), Sankeerna (9).<br/>"
                  "• <b>Dhrutam (O):</b> A beat followed by a wave of the hand (2 aksharas).<br/>"
                  "• <b>Anudhrutam (U):</b> A single beat (1 akshara).<br/>"
                  "Applying the 5 jathis to the 7 Suladi Sapta Talas produces the 35 Tala scheme. The most popular tala in concerts is <b>Adi Tala</b> (Chaturasra Jathi Triputa Tala: I4 O O = 8 aksharas).", body_style),
        Paragraph("<b>The Trinity of Carnatic Music (18th–19th Century):</b><br/>"
                  "• <b>Tyagaraja (1767–1847):</b> Master of devotional Kritis, Pancharatna Kritis, and expressive sangathis in Telugu.<br/>"
                  "• <b>Muthuswami Dikshitar (1775–1835):</b> Known for grand Sanskrit Kritis set in intellectual vilamba laya, Kamalamba Navavarna Kritis, and rich gamakas.<br/>"
                  "• <b>Syama Sastri (1762–1827):</b> Renowned for intricate rhythmic patterns, Swarajatis, and soulful compositions dedicated to Goddess Kamakshi.", body_style)
    ]
    doc.build(story)
    print("Created:", pdf_path.name)

# ==============================================================================
# PDF 5: Music Theory Questions and Analysis Study Notes
# ==============================================================================
def create_questions_analysis_pdf():
    pdf_path = DOCS_DIR / "music_theory_questions_and_analysis_study_notes.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = [
        Paragraph("Music Theory Questions and Analysis: Study Notes", title_style),
        Paragraph("<b>Subject:</b> Comparative Analysis, Examination Inquiries, and Theoretical Solutions", body_style),
        Spacer(1, 10),
        Paragraph("Frequently Asked Questions in Music Theory", heading2_style),
        Paragraph("<b>Q1: Who is the father of Carnatic music?</b><br/>"
                  "<b>Answer:</b> <b>Purandara Dasa</b> (1484–1564) is universally revered as the <b>Father of Carnatic music</b> (<i>Sangeeta Pitamaha</i>). "
                  "He earned this title because he systematized the entire pedagogy of Carnatic music (Sarali, Janta, Alankaras, Geethams in Mayamalavagowla), "
                  "standardized the Suladi Sapta Talas, and composed foundational devotional works.", body_style),
        Paragraph("<b>Q2: What intervals construct a major triad, and what are its scale degrees?</b><br/>"
                  "<b>Answer:</b> A major triad consists of a root tone, a major third (4 semitones above the root), and a perfect fifth (7 semitones above the root). "
                  "In scale degrees, it corresponds to degrees 1, 3, and 5 of the major scale (e.g. C – E – G).", body_style),
        Paragraph("<b>Q3: What is a Perfect Authentic Cadence (PAC) in classical harmony?</b><br/>"
                  "<b>Answer:</b> A PAC is a harmonic progression from the Dominant (V) to the Tonic (I) where both chords are in fundamental root position, "
                  "and the soprano voice terminates on the tonic root pitch (^1). It provides maximum tonal finality.", body_style),
        Paragraph("<b>Q4: Why are parallel fifths and octaves forbidden in classical SATB part writing?</b><br/>"
                  "<b>Answer:</b> In classical four-part voice leading, consecutive parallel fifths and octaves between any two voices are strictly prohibited "
                  "because they destroy the vocal independence of the parts. Composers maintain independence by employing contrary and oblique motion.", body_style),
        Paragraph("<b>Q5: How does 6/8 meter differ from 3/4 meter?</b><br/>"
                  "<b>Answer:</b> 6/8 is a compound duple meter containing two dotted-quarter beats per measure, with each beat dividing into three eighth notes. "
                  "In contrast, 3/4 is a simple triple meter containing three quarter-note beats per measure, each dividing into two eighth notes.", body_style),
        Paragraph("<b>Q6: What is the equivalent of the Western Major Scale in the Carnatic Melakarta system?</b><br/>"
                  "<b>Answer:</b> The Western Major scale (diatonic Ionian mode) is identical in interval structure (S R2 G3 M1 P D2 N3 S) to the 29th Melakarta raga, "
                  "<b>Dheerasankarabharanam</b> (commonly known as Shankarabharanam).", body_style)
    ]
    doc.build(story)
    print("Created:", pdf_path.name)

def main():
    print("Generating comprehensive study-note PDFs in:", DOCS_DIR)
    create_western_fundamentals_pdf()
    create_harmony_voice_leading_pdf()
    create_rhythm_form_pdf()
    create_carnatic_music_pdf()
    create_questions_analysis_pdf()
    print("All 5 study-note PDFs generated successfully!")

if __name__ == "__main__":
    main()
