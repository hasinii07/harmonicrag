import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import settings
from app.models.schemas import (
    EvaluationTestCase,
    EvaluationReport,
    ChatRequest
)
from app.services.chat_service import chat_service
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)

BENCHMARK_CASES = [
    # --------------------------------------------------------------------------
    # Category A: Direct in-corpus factual questions
    # --------------------------------------------------------------------------
    {
        "test_id": "TEST-A1",
        "category": "A",
        "category_name": "Direct in-corpus factual",
        "question": "What intervals construct a major triad, and what are its scale degrees?",
        "expected_behavior": "Must identify root, major third (4 semitones), and perfect fifth (7 semitones) grounded in text.",
        "criteria": "answer_contains:major third;answer_contains:perfect fifth;grounded:true"
    },
    {
        "test_id": "TEST-A2",
        "category": "A",
        "category_name": "Direct in-corpus factual",
        "question": "What is a Perfect Authentic Cadence (PAC) in classical harmony?",
        "expected_behavior": "Must state progression V to I with both chords in root position and tonic in the highest voice (soprano).",
        "criteria": "answer_contains:root position;answer_contains:soprano;grounded:true"
    },

    # --------------------------------------------------------------------------
    # Category B: Multi-passage synthesis
    # --------------------------------------------------------------------------
    {
        "test_id": "TEST-B1",
        "category": "B",
        "category_name": "Multi-passage synthesis",
        "question": "Explain how the dominant seventh chord (V7) resolves to the tonic in four-part SATB voice leading.",
        "expected_behavior": "Must synthesize V7 chord construction and voice leading rules (3rd resolves up to tonic, 7th resolves down by step).",
        "criteria": "answer_contains:leading tone;answer_contains:resolves down;min_chunks:2"
    },
    {
        "test_id": "TEST-B2",
        "category": "B",
        "category_name": "Multi-passage synthesis",
        "question": "How do voice leading constraints regarding parallel octaves and fifths affect harmonic progressions between triads?",
        "expected_behavior": "Must combine rules against parallel motion with part-writing motion (contrary motion).",
        "criteria": "answer_contains:parallel;answer_contains:contrary;min_chunks:2"
    },

    # --------------------------------------------------------------------------
    # Category C: Uncovered or out-of-scope questions
    # --------------------------------------------------------------------------
    {
        "test_id": "TEST-C1",
        "category": "C",
        "category_name": "Uncovered or out-of-scope",
        "question": "What exact Moog modular synthesizer patch settings did Wendy Carlos use on the track 'Brandenburg Concerto No. 3'?",
        "expected_behavior": "Must abstain cleanly and declare that the indexed harmony treatises do not contain synthesizer patch documentation.",
        "criteria": "abstain:true;insufficient_evidence:true"
    },
    {
        "test_id": "TEST-C2",
        "category": "C",
        "category_name": "Uncovered or out-of-scope",
        "question": "How do you automate sidechain compression on an 808 kick drum in Ableton Live 12?",
        "expected_behavior": "Must state that modern digital audio workstation production tips are outside the scope of the classical music theory treatises.",
        "criteria": "abstain:true;insufficient_evidence:true"
    },

    # --------------------------------------------------------------------------
    # Category D: Ambiguous musical questions
    # --------------------------------------------------------------------------
    {
        "test_id": "TEST-D1",
        "category": "D",
        "category_name": "Ambiguous musical questions",
        "question": "Is 6/8 meter classified as having two beats or six beats?",
        "expected_behavior": "Must clarify the distinction between beats (2 compound dotted-quarter beats) and pulses (6 eighth-note subdivisions).",
        "criteria": "answer_contains:compound;answer_contains:dotted"
    },
    {
        "test_id": "TEST-D2",
        "category": "D",
        "category_name": "Ambiguous musical questions",
        "question": "Is the interval from C to F-sharp an augmented fourth or a diminished fifth?",
        "expected_behavior": "Must explain that C to F# is an augmented fourth; while enharmonically sounding the same as C to Gb, they are theoretically distinct.",
        "criteria": "answer_contains:augmented;answer_contains:enharmonic"
    },

    # --------------------------------------------------------------------------
    # Category E: Incorrect musical assumptions
    # --------------------------------------------------------------------------
    {
        "test_id": "TEST-E1",
        "category": "E",
        "category_name": "Incorrect musical assumptions",
        "question": "Why does a major scale consist of 12 notes?",
        "expected_behavior": "Must politely correct the assumption: the major scale is heptatonic (7 notes), while the chromatic scale has 12 semitones.",
        "criteria": "misconception_detected:true"
    },
    {
        "test_id": "TEST-E2",
        "category": "E",
        "category_name": "Incorrect musical assumptions",
        "question": "In classical SATB voice leading, why are parallel fifths allowed between the soprano and bass voices?",
        "expected_behavior": "Must correct the false premise: parallel fifths are strictly forbidden in classical part writing.",
        "criteria": "misconception_detected:true"
    },

    # --------------------------------------------------------------------------
    # Category F: Strict citation requirements
    # --------------------------------------------------------------------------
    {
        "test_id": "TEST-F1",
        "category": "F",
        "category_name": "Strict citation requirements",
        "question": "Cite the definition of harmonic cadences and voice leading from the ingested treatise.",
        "expected_behavior": "Must supply verified citations with exact chunk ID and document title.",
        "criteria": "citations_required:true;verified_citations:true"
    },
    {
        "test_id": "TEST-F2",
        "category": "F",
        "category_name": "Strict citation requirements",
        "question": "Provide the exact citation and passage for triad inversions (first inversion 6/3 and second inversion 6/4).",
        "expected_behavior": "Must return verified citations referencing treatise chapters/pages.",
        "criteria": "citations_required:true;verified_citations:true"
    },

    # --------------------------------------------------------------------------
    # Category REG: Targeted Regression Tests for Music Theory Retrieval
    # --------------------------------------------------------------------------
    {
        "test_id": "TEST-REG1",
        "category": "REG",
        "category_name": "Music Theory Ambiguity & Retrieval",
        "question": "What are the 7 chords?",
        "expected_behavior": "Must explain the seven diatonic triads in a major key (I, ii, iii, IV, V, vi, vii°) and not confuse with modal interchange.",
        "criteria": "answer_contains:triad;answer_contains:major;answer_excludes:modal interchange;grounded:true"
    },
    {
        "test_id": "TEST-REG2",
        "category": "REG",
        "category_name": "Music Theory Ambiguity & Retrieval",
        "question": "What are seventh chords?",
        "expected_behavior": "Must explain four-note seventh chords and their constituent types.",
        "criteria": "answer_contains:four-note;answer_contains:seventh;grounded:true"
    },
    {
        "test_id": "TEST-REG3",
        "category": "REG",
        "category_name": "Music Theory Ambiguity & Retrieval",
        "question": "What are the chords in C major?",
        "expected_behavior": "Must return the seven diatonic triads: C, D minor, E minor, F, G, A minor, and B diminished.",
        "criteria": "answer_contains:c major;answer_contains:d minor;answer_contains:b diminished;grounded:true"
    },
    {
        "test_id": "TEST-REG4",
        "category": "REG",
        "category_name": "Music Theory Ambiguity & Retrieval",
        "question": "Explain modal interchange.",
        "expected_behavior": "Must retrieve and explain modal interchange and borrowed chords from parallel modes.",
        "criteria": "answer_contains:modal interchange;answer_contains:borrowed;grounded:true"
    },
    {
        "test_id": "TEST-REG5",
        "category": "REG",
        "category_name": "Music Theory Ambiguity & Retrieval",
        "question": "What is a V7 chord?",
        "expected_behavior": "Must retrieve dominant seventh chord material and explain its function.",
        "criteria": "answer_contains:dominant;answer_contains:fifth;grounded:true"
    },
    {
        "test_id": "TEST-REG6",
        "category": "REG",
        "category_name": "Music Theory Ambiguity & Retrieval",
        "question": "What Moog synthesizer patch presets did Wendy Carlos use for Switched-On Bach?",
        "expected_behavior": "Must abstain cleanly with honest limitation and zero fabricated citations.",
        "criteria": "abstain:true;insufficient_evidence:true;no_citations:true"
    },
    {
        "test_id": "TEST-REG7",
        "category": "REG",
        "category_name": "Music Theory Ambiguity & Retrieval",
        "question": "What is the secret lost chord of ancient Atlantis in hyper-dimensional tuning?",
        "expected_behavior": "Missing source material triggers an honest limitation response.",
        "criteria": "abstain:true;insufficient_evidence:true;no_citations:true"
    }
]

class EvaluationService:
    """
    Executes automated RAG evaluation benchmarks across the six mandatory categories
    and computes genuine mathematical metrics from live retrieval & generation traces.
    """

    def __init__(self, results_file: Optional[Path] = None):
        self.results_file = results_file or (settings.metadata_dir / "evaluation_results.json")
        self.latest_report: Optional[EvaluationReport] = None
        self.load_latest_report()

    def load_latest_report(self):
        if self.results_file.exists():
            try:
                with open(self.results_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.latest_report = EvaluationReport(**data)
            except Exception as e:
                logger.error(f"Failed to load evaluation results: {e}")

    def save_report(self, report: EvaluationReport):
        try:
            with open(self.results_file, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
            self.latest_report = report
        except Exception as e:
            logger.error(f"Failed to save evaluation report: {e}")

    def run_suite(self) -> EvaluationReport:
        """
        Executes all benchmark test cases and computes real metrics.
        """
        total_chunks_in_db = vector_store.get_total_chunks_count()
        executed_cases: List[EvaluationTestCase] = []

        passed_count = 0
        failed_count = 0
        retrieval_success_count = 0
        applicable_retrieval_count = 0
        total_candidate_citations = 0
        total_verified_citations = 0
        citation_required_count = 0
        citation_satisfied_count = 0
        unsupported_claims_count = 0
        abstention_opportunities = 0
        correct_abstentions = 0
        total_latencies = []

        for case_data in BENCHMARK_CASES:
            test_id = case_data["test_id"]
            category = case_data["category"]
            question = case_data["question"]
            criteria = case_data["criteria"]

            # If vector DB has no documents, report honestly for grounded tests
            if total_chunks_in_db == 0 and category in ["A", "B", "F"]:
                tc = EvaluationTestCase(
                    test_id=test_id,
                    category=category,
                    category_name=case_data["category_name"],
                    question=question,
                    expected_behavior=case_data["expected_behavior"],
                    criteria=criteria,
                    actual_answer="No documents currently indexed in knowledge base.",
                    status="fail",
                    failure_reason="No documents indexed in knowledge base. Ingest reference treatises first."
                )
                executed_cases.append(tc)
                failed_count += 1
                continue

            req = ChatRequest(message=question, include_trace=True)
            res = chat_service.process_message(req)

            ret_latency = res.retrieval_trace.latencies_ms.get("total_retrieval_ms", 0.0)
            gen_latency = res.retrieval_trace.latencies_ms.get("generation_ms", 0.0)
            tot_latency = res.retrieval_trace.latencies_ms.get("total_ms", ret_latency + gen_latency)
            total_latencies.append(tot_latency)

            # Evaluate criteria
            reasons = []
            is_pass = True
            combined_text = (res.direct_answer + " " + res.explanation).lower()

            for criterion in criteria.split(';'):
                c_clean = criterion.strip()
                if not c_clean:
                    continue

                if c_clean.startswith("answer_contains:"):
                    expected_term = c_clean.split(":", 1)[1].lower()
                    if expected_term not in combined_text:
                        is_pass = False
                        reasons.append(f"Answer missing expected term '{expected_term}'")

                elif c_clean.startswith("answer_excludes:"):
                    excluded_term = c_clean.split(":", 1)[1].lower()
                    if excluded_term in combined_text:
                        is_pass = False
                        reasons.append(f"Answer improperly contains excluded term '{excluded_term}'")

                elif c_clean == "no_citations:true":
                    if res.citations:
                        is_pass = False
                        reasons.append(f"Expected zero citations for ungrounded question, but got {len(res.citations)}")

                elif c_clean == "grounded:true":
                    applicable_retrieval_count += 1
                    if res.is_evidence_sufficient and res.citations:
                        retrieval_success_count += 1
                    else:
                        is_pass = False
                        reasons.append("Answer was not successfully grounded in retrieved sources.")

                elif c_clean == "min_chunks:2":
                    if len(res.retrieval_trace.selected_chunks) < 2:
                        is_pass = False
                        reasons.append(f"Expected at least 2 retrieved chunks, got {len(res.retrieval_trace.selected_chunks)}")

                elif c_clean == "abstain:true":
                    abstention_opportunities += 1
                    if "does not contain" in combined_text or "insufficient" in combined_text or not res.is_evidence_sufficient:
                        correct_abstentions += 1
                    else:
                        is_pass = False
                        unsupported_claims_count += 1
                        reasons.append("Model failed to abstain on uncovered/out-of-scope question.")

                elif c_clean == "insufficient_evidence:true":
                    if res.is_evidence_sufficient:
                        is_pass = False
                        reasons.append("Evidence should have been marked as insufficient.")

                elif c_clean == "misconception_detected:true":
                    if not res.misconception_correction:
                        is_pass = False
                        reasons.append("Failed to detect and flag the musical misconception.")

                elif c_clean == "citations_required:true":
                    citation_required_count += 1
                    if res.citations:
                        citation_satisfied_count += 1
                    else:
                        is_pass = False
                        reasons.append("No citations provided when strictly required.")

                elif c_clean == "verified_citations:true":
                    if not all(c.is_verified for c in res.citations):
                        is_pass = False
                        reasons.append("One or more citations failed verification against source passages.")

            # Track citation precision
            val_summary = res.retrieval_trace.citation_validation
            total_candidate_citations += val_summary.get("candidate_count", len(res.citations))
            total_verified_citations += val_summary.get("verified_count", len(res.citations))

            tc_status = "pass" if is_pass else "fail"
            if is_pass:
                passed_count += 1
            else:
                failed_count += 1

            executed_cases.append(EvaluationTestCase(
                test_id=test_id,
                category=category,
                category_name=case_data["category_name"],
                question=question,
                expected_behavior=case_data["expected_behavior"],
                criteria=criteria,
                actual_answer=res.direct_answer,
                retrieved_chunk_ids=[c.get("chunk_id", "") for c in res.retrieval_trace.selected_chunks],
                citations=[f"{c.document_title} (p.{c.page_number or 'N/A'} - {c.chunk_id})" for c in res.citations],
                status=tc_status,
                failure_reason="; ".join(reasons) if reasons else None,
                retrieval_latency_ms=ret_latency,
                generation_latency_ms=gen_latency
            ))

        total_tests = len(executed_cases)
        pass_rate_pct = round((passed_count / total_tests * 100), 2) if total_tests > 0 else 0.0
        ret_succ_pct = round((retrieval_success_count / applicable_retrieval_count * 100), 2) if applicable_retrieval_count > 0 else 0.0
        cit_prec_pct = round((total_verified_citations / total_candidate_citations * 100), 2) if total_candidate_citations > 0 else 100.0
        cit_cov_pct = round((citation_satisfied_count / citation_required_count * 100), 2) if citation_required_count > 0 else 100.0
        unsupp_pct = round((unsupported_claims_count / total_tests * 100), 2) if total_tests > 0 else 0.0
        abstain_pct = round((correct_abstentions / abstention_opportunities * 100), 2) if abstention_opportunities > 0 else 100.0
        avg_lat = round(sum(total_latencies) / len(total_latencies), 2) if total_latencies else 0.0

        report = EvaluationReport(
            total_tests=total_tests,
            passed_tests=passed_count,
            failed_tests=failed_count,
            pass_rate_pct=pass_rate_pct,
            retrieval_success_rate_pct=ret_succ_pct,
            citation_precision_pct=cit_prec_pct,
            citation_coverage_pct=cit_cov_pct,
            unsupported_answer_rate_pct=unsupp_pct,
            abstention_performance_pct=abstain_pct,
            avg_latency_ms=avg_lat,
            evaluated_at=datetime.now().isoformat(),
            cases=executed_cases
        )

        self.save_report(report)
        return report

# Global singleton
evaluation_service = EvaluationService()
