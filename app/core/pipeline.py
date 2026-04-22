import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import List
from fastapi import UploadFile

from app.api.schemas import ClaimDecision
from app.models.schemas import ExtractedDocument, GateResult, PipelineTrace
from app.core.extract import extract_document
from app.core.gates import timeline_gate, coverage_gate, authenticity_gate
from app.core.rule_engine import decide
from app.utils.logger import logger
from app.utils import business_rules as rules

async def process_claim(description: str, files: List[UploadFile]) -> ClaimDecision:
    claim_id = str(uuid.uuid4())
    log_prefix = f"Claim {claim_id}"
    logger.info(f"{log_prefix}: Processing with {len(files)} files")
    all_traces: List[PipelineTrace] = []

    try:
        temp_dir = tempfile.mkdtemp()
        saved_files = []

        for file in files:
            file_path = Path(temp_dir) / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append(str(file_path))
        logger.info(f"{log_prefix}: Saved {len(saved_files)} files to temp dir")

        extract_tasks = [extract_document(fp) for fp in saved_files]
        extract_results = await asyncio.gather(*extract_tasks, return_exceptions=True)

        extracted_docs: List[ExtractedDocument] = []
        extraction_failed = False
        for i, result in enumerate(extract_results):
            if isinstance(result, Exception):
                logger.error(f"{log_prefix}: Extraction failed for file {i+1} - {str(result)}")
                extraction_failed = True
            else:
                doc, trace = result
                extracted_docs.append(doc)
                all_traces.append(trace)

        logger.info(f"{log_prefix}: Extracted {len(extracted_docs)} documents ({len(extract_results) - len(extracted_docs)} failed)")

        if extraction_failed and len(extracted_docs) == 0:
            return ClaimDecision(
                claim_id=claim_id,
                decision="DENY",
                confidence=0.85,
                reasoning=f"Document extraction failed for all submitted files. Unable to verify claim documentation.",
                gate_results=[],
                trace=all_traces
            )

        image_paths = [fp for fp in saved_files if Path(fp).suffix.lower() in rules.IMAGE_EXTENSIONS]
        logger.info(f"{log_prefix}: Found {len(image_paths)} images for authenticity check")
        
        coverage_result, coverage_trace = await coverage_gate(extracted_docs, description, saved_files)
        all_traces.append(coverage_trace)

        claimant_name = coverage_result.signals.get("claimant_name", "")
        is_third_party = coverage_result.signals.get("is_third_party_claim", False)

        gate_tasks = [
            timeline_gate(extracted_docs, description),
            authenticity_gate(image_paths)
        ]

        gate_results_with_traces = await asyncio.gather(*gate_tasks, return_exceptions=True)

        gate_results: List[GateResult] = [coverage_result]
        for result in gate_results_with_traces:
            if isinstance(result, Exception):
                logger.error(f"{log_prefix}: Gate execution failed - {str(result)}")
                return ClaimDecision(
                    claim_id=claim_id,
                    decision="UNCERTAIN",
                    confidence=0.0,
                    reasoning=f"Gate execution failed: {str(result)}",
                    gate_results=gate_results,
                    trace=all_traces
                )
            else:
                gate_result, trace = result
                gate_results.append(gate_result)
                all_traces.append(trace)

        for gate_result in gate_results:
            logger.info(f"{log_prefix}: {gate_result.gate_name} gate - passed={gate_result.passed}, confidence={gate_result.confidence:.2f}")

        decision, confidence, reasoning = decide(gate_results)
        logger.info(f"{log_prefix}: Final decision={decision}, confidence={confidence:.2f}")

        return ClaimDecision(
            claim_id=claim_id,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            gate_results=gate_results,
            trace=all_traces
        )

    except Exception as e:
        logger.error(f"{log_prefix}: Unexpected error - {str(e)}", exc_info=True)
        return ClaimDecision(
            claim_id=claim_id,
            decision="UNCERTAIN",
            confidence=0.0,
            reasoning=f"Unexpected error during processing: {str(e)}",
            gate_results=[],
            trace=all_traces
        )
