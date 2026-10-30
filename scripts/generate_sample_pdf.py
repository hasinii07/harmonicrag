import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf():
    pdf_path = Path(__file__).resolve().parent.parent / "data" / "documents" / "richter_manual_of_harmony.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22, leading=26, textColor=colors.navy, spaceAfter=14
    )
    heading_style = ParagraphStyle(
        'DocHeading',
        parent=styles['Heading2'],
        fontSize=15, leading=18, textColor=colors.darkblue, spaceBefore=12, spaceAfter=8
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontSize=10, leading=14, spaceAfter=8
    )

    story = []

    # ------------------ PAGE 1 ------------------
    story.append(Paragraph("A Manual of Harmony", title_style))
    story.append(Paragraph("<b>Author:</b> Ernst Friedrich Richter | <i>Authorized Translation</i>", body_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Chapter I: The Construction of Fundamental Triads", heading_style))
    story.append(Paragraph(
        "Harmony is the science of chords and their sequential relationship. The foundation of harmonic theory rests upon the triad. "
        "A triad is a chord consisting of three tones: a fundamental root, a third above the root, and a fifth above the root.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Major Triad:</b> Formed by a root, a major third (4 semitones), and a perfect fifth (7 semitones). In C major, this is C – E – G. "
        "The triad provides tonal resolution and acoustic clarity.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Minor Triad:</b> Formed by a root, a minor third (3 semitones), and a perfect fifth (7 semitones). In A minor, this is A – C – E.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Diminished Triad:</b> Formed by a root, a minor third (3 semitones), and a diminished fifth (6 semitones). For example, on the seventh degree of C major: B – D – F. "
        "Note: The diminished triad contains a diminished fifth, NOT a perfect fifth.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Augmented Triad:</b> Formed by a root, a major third (4 semitones), and an augmented fifth (8 semitones). For example: C – E – G#.",
        body_style
    ))
    story.append(PageBreak())

    # ------------------ PAGE 2 ------------------
    story.append(Paragraph("Chapter II: Inversions of the Triad", heading_style))
    story.append(Paragraph(
        "When the fundamental root tone is in the lowest voice (bass), the chord is in its fundamental root position. "
        "When another tone is placed in the bass, the chord is in an inversion.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The First Inversion (Chord of the Sixth, 6/3):</b> When the third of the triad is placed in the lowest voice (bass), "
        "the chord is in the First Inversion. The intervals above the bass are a third and a sixth; hence it is denoted as the Chord of the Sixth, "
        "or figured as 6 or 6/3. In C major, with E in the bass, the chord is E – G – C, represented as I6.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Second Inversion (Chord of the Sixth and Fourth, 6/4):</b> When the fifth of the triad is placed in the lowest voice (bass), "
        "the chord is in the Second Inversion. The intervals above the bass are a fourth and a sixth; hence it is designated the Chord of the Fourth and Sixth, "
        "or figured as 6/4. In C major, with G in the bass, the chord is G – C – E, represented as I6/4. "
        "The 6/4 chord has an unstable, dependent character and frequently functions as a cadential 6/4 delaying the dominant V.",
        body_style
    ))
    story.append(PageBreak())

    # ------------------ PAGE 3 ------------------
    story.append(Paragraph("Chapter III: Principles of Four-Part SATB Voice Leading", heading_style))
    story.append(Paragraph(
        "The standard choral setting consists of four voices: Soprano, Alto, Tenor, and Bass (abbreviated SATB). "
        "The soprano and alto are high voices; the tenor and bass are lower voices.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Prohibition of Parallel Fifths and Octaves:</b> One of the most foundational and strict laws of classical part writing is: "
        "Consecutive parallel fifths and parallel octaves between any two voices are strictly prohibited. "
        "If two voices sound a perfect fifth (or perfect octave) and move in parallel motion to another perfect fifth (or octave), "
        "the independence of the two voices is destroyed.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Contrary Motion:</b> Contrary motion, in which voices move in opposite directions, provides the most effective protection against parallel fifths and octaves.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Leading Tone Resolution:</b> The leading tone (seventh degree, ^7) possesses an energetic tendency to resolve upward by step to the tonic (^1). "
        "In cadences, the leading tone in an outer voice must resolve upward.",
        body_style
    ))
    story.append(PageBreak())

    # ------------------ PAGE 4 ------------------
    story.append(Paragraph("Chapter IV: Harmonic Cadences", heading_style))
    story.append(Paragraph(
        "A cadence is a harmonic progression that marks the close of a musical phrase, section, or complete composition.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Perfect Authentic Cadence (PAC):</b> The most conclusive harmonic close is the Perfect Authentic Cadence. It requires: "
        "1. The harmonic progression from the Dominant (V) to the Tonic (I). "
        "2. Both chords must be in fundamental root position. "
        "3. The highest voice (soprano) must arrive on the tonic root pitch (^1) in the final chord.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Imperfect Authentic Cadence (IAC):</b> An Authentic Cadence is termed Imperfect if either chord is in an inversion (e.g., V6 to I, or V to I6), "
        "or if the soprano voice ends on the third (^3) or fifth (^5) of the tonic chord instead of the root.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Half Cadence (HC):</b> A Half Cadence pauses upon the Dominant chord (V), typically preceded by the tonic (I to V), subdominant (IV to V), or supertonic (ii to V).",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Deceptive Cadence (DC):</b> A Deceptive Cadence occurs when the dominant chord (V) leads not to the expected tonic (I), but to another scale degree, "
        "most frequently the submediant (vi). In C major, this is the progression V to vi.",
        body_style
    ))

    doc.build(story)
    print(f"Successfully generated PDF at: {pdf_path}")

if __name__ == "__main__":
    generate_pdf()
