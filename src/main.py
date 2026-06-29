import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Any

# Add project root to sys.path so we can run this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.candidate import Candidate
# Ingestion Adapters
from src.adapters.csv_adapter import parse_csv
from src.adapters.ats_adapter import parse_ats
from src.adapters.resume_adapter import parse_resume
from src.adapters.notes_adapter import parse_notes
# Identity Resolution
from src.matching.identity_resolver import group_records
# Merge Engine
from src.merge.merge_engine import build_candidate
# Confidence Engine
from src.confidence.confidence_engine import calculate_candidate_confidence
# Provenance Builder
from src.provenance.provenance_builder import build_candidate_provenance
# Projection Engine
from src.projection.projection_engine import project
# Validation Layer
from src.validation.validator import validate_candidate, validate_projection_config, validate_output

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main_pipeline")

def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Source Candidate Data Transformer Pipeline")
    parser.add_argument("--csv", help="Path to Recruiter CSV file")
    parser.add_argument("--ats", help="Path to ATS JSON file")
    parser.add_argument("--resume", help="Path to Resume PDF/DOCX file")
    parser.add_argument("--notes", help="Path to Recruiter Notes TXT file")
    parser.add_argument("--config", help="Path to Projection Config JSON file")
    
    args = parser.parse_args()
    
    # 1. Ingestion / Data Extraction
    raw_profiles = []
    
    if args.csv:
        logger.info(f"Extracting from CSV: {args.csv}")
        raw_profiles.extend(parse_csv(args.csv))
    if args.ats:
        logger.info(f"Extracting from ATS JSON: {args.ats}")
        raw_profiles.extend(parse_ats(args.ats))
    if args.resume:
        logger.info(f"Extracting from Resume: {args.resume}")
        raw_profiles.extend(parse_resume(args.resume))
    if args.notes:
        logger.info(f"Extracting from Notes: {args.notes}")
        raw_profiles.extend(parse_notes(args.notes))
        
    if not raw_profiles:
        logger.error("No input files provided or no profiles extracted. Please provide at least one source file.")
        sys.exit(1)
        
    logger.info(f"Extracted {len(raw_profiles)} profile(s) from sources.")
    
    # 2. Identity Resolution
    logger.info("Resolving candidate identities...")
    groups = group_records(raw_profiles)
    logger.info(f"Resolved profiles into {len(groups)} unique candidate(s).")
    
    # 3. Merge & Confidence & Provenance Enrichment
    logger.info("Merging candidate profiles and computing confidence/provenance details...")
    canonical_candidates: List[Candidate] = []
    
    for idx, group in enumerate(groups):
        logger.info(f"Merging group {idx+1}/{len(groups)} containing {len(group)} profile(s)...")
        # a. Merge fields into Candidate
        candidate = build_candidate(group)
        # b. Enrichment - Confidence
        candidate = calculate_candidate_confidence(candidate, group)
        # c. Enrichment - Provenance
        candidate = build_candidate_provenance(candidate, group)
        
        canonical_candidates.append(candidate)
        
    # 4. Candidate Validation
    logger.info("Validating canonical candidate profiles...")
    for idx, cand in enumerate(canonical_candidates):
        res = validate_candidate(cand)
        if not res.valid:
            logger.warning(f"Canonical candidate [{idx}] (ID: {cand.candidate_id}) failed validation: {res.errors}")
        else:
            logger.info(f"Canonical candidate [{idx}] validated successfully.")
            
    # 5. Config Loading & Validation
    config = None
    if args.config:
        if os.path.exists(args.config):
            try:
                with open(args.config, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info(f"Loaded projection config from: {args.config}")
            except Exception as e:
                logger.error(f"Error reading projection config file: {e}")
        else:
            logger.warning(f"Config file not found at: {args.config}. Using defaults.")
            
    # Default fallback config
    if not config:
        config = {
            "fields": [
                {"path": "candidate_name", "from": "full_name"},
                {"path": "primary_email", "from": "emails[0]"},
                {"path": "primary_phone", "from": "phones[0]"},
                {"path": "job_headline", "from": "headline"},
                {"path": "skills_list", "from": "skills[].name"}
            ],
            "include_confidence": True,
            "include_provenance": True,
            "on_missing": "null"
        }
        
    # Validate the projection config
    config_val = validate_projection_config(config)
    if not config_val.valid:
        logger.error(f"Projection configuration is invalid: {config_val.errors}")
        sys.exit(1)
        
    # 6. Projection Engine & Output Validation
    projected_outputs = []
    for cand in canonical_candidates:
        projected = project(cand, config)
        
        # Validate output schema
        out_val = validate_output(projected)
        if not out_val.valid:
            logger.warning(f"Projected output validation failed: {out_val.errors}")
            
        projected_outputs.append(projected)
        
    # 7. Write Outputs
    os.makedirs("output", exist_ok=True)
    canonical_json_path = os.path.join("output", "canonical.json")
    custom_json_path = os.path.join("output", "custom_output.json")
    
    # Save first candidate or list of candidates
    canonical_to_save = canonical_candidates[0].model_dump() if len(canonical_candidates) == 1 else [c.model_dump() for c in canonical_candidates]
    custom_to_save = projected_outputs[0] if len(projected_outputs) == 1 else projected_outputs
    
    with open(canonical_json_path, "w", encoding="utf-8") as f:
        json.dump(canonical_to_save, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved canonical candidate profile to: {canonical_json_path}")
    
    with open(custom_json_path, "w", encoding="utf-8") as f:
        json.dump(custom_to_save, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved projected custom profile to: {custom_json_path}")
    
    logger.info("Pipeline executed successfully.")

if __name__ == "__main__":
    main()
