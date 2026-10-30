import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import EvaluationReport
from app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])
logger = logging.getLogger(__name__)

@router.post("/run", response_model=EvaluationReport)
def run_evaluation() -> EvaluationReport:
    """
    Executes the automated evaluation suite across 6 benchmark categories:
    A. Direct in-corpus factual
    B. Multi-passage synthesis
    C. Uncovered or out-of-scope
    D. Ambiguous musical questions
    E. Incorrect musical assumptions
    F. Strict citation requirements
    
    Returns calculated genuine metrics (pass rate, citation precision, coverage, latencies).
    """
    try:
        return evaluation_service.run_suite()
    except Exception:
        logger.exception("Evaluation suite failed")
        raise HTTPException(status_code=500, detail="Evaluation failed.")

@router.get("/results", response_model=EvaluationReport)
def get_evaluation_results() -> EvaluationReport:
    """
    Retrieves the most recent evaluation report.
    """
    report = evaluation_service.latest_report
    if not report:
        raise HTTPException(status_code=404, detail="No evaluation results found. Run an evaluation first.")
    return report
