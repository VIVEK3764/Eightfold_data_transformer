# Multi-Source Candidate Data Transformer

A production-quality Python pipeline that ingests candidate data from multiple structured (CSV, JSON) and unstructured (PDF, DOCX, TXT) sources, performs identity resolution, merges profiles with conflict resolution rules, calculates explainable confidence scores, maintains a detailed provenance lineage, and supports configurable schema projections.

---

## Architecture Diagram

The system operates as a sequence of independent, decoupled layers:

```
    Sources (CSV, ATS JSON, Resume PDF/DOCX, Notes TXT)
                        ↓
                 Adapters Layer
                        ↓
                 Normalization
                        ↓
              Identity Resolution (BFS Connected Components)
                        ↓
                  Merge Engine
                        ↓
                Confidence Engine
                        ↓
                Provenance Engine
                        ↓
               Canonical Candidate (Pydantic Model)
                        ↓
               Projection Engine (Transformed Custom View)
                        ↓
                Validation Layer
                        ↓
                 JSON Output files
```

---

## Folder Structure

```
eightfold-transformer/
├── config/
│   ├── default.json             # Canonical export config
│   └── custom.json              # Schema custom projection config
├── inputs/
│   ├── recruiter.csv            # CSV candidate source
│   ├── ats.json                 # ATS JSON candidate source
│   ├── resume.docx              # Resume Word source
│   ├── resume.pdf               # Resume PDF source
│   └── notes.txt                # Recruiter Notes source
├── output/
│   ├── canonical.json           # Ingested Canonical candidate output
│   └── custom_output.json       # Projected output
├── src/
│   ├── adapters/
│   │   ├── csv_adapter.py       # Ingests CSV files
│   │   ├── ats_adapter.py       # Ingests JSON files
│   │   ├── resume_adapter.py    # Ingests PDF/DOCX resumes (with OCR fallback)
│   │   └── notes_adapter.py     # Ingests text notes
│   ├── matching/
│   │   ├── identity_resolver.py # Matches records
│   │   └── match_result.py      # Match result model
│   ├── merge/
│   │   └── merge_engine.py      # Merges candidate groups using priority
│   ├── confidence/
│   │   └── confidence_engine.py # Calculates agreement/conflict confidence
│   ├── provenance/
│   │   └── provenance_builder.py# Builds field-level traceability records
│   ├── normalizers/
│   │   ├── email.py             # Validates and cleans emails
│   │   ├── phone.py             # Standardizes numbers to E.164
│   │   ├── dates.py             # Normalizes formats to YYYY-MM
│   │   └── skills.py            # Maps skill aliases
│   ├── models/
│   │   └── candidate.py         # Canonical Pydantic schemas
│   ├── projection/
│   │   └── projection_engine.py # Projects view from runtime configs
│   ├── validation/
│   │   ├── validator.py         # Candidate & Output validators
│   │   └── validation_result.py # validation result wrapper
│   └── main.py                  # CLI pipeline orchestrator
└── tests/                       # Pytest test suites (91 passed)
```

---

## Installation

Install all python dependencies:
```bash
pip install -r requirements.txt
```

---

## Running the Pipeline

To run the complete end-to-end pipeline:

**Windows PowerShell:**
```powershell
$env:PYTHONPATH="."
python src/main.py --csv inputs/recruiter.csv --ats inputs/ats.json --resume inputs/resume.pdf --notes inputs/notes.txt --config config/default.json
```

**Linux / macOS:**
```bash
PYTHONPATH=. python src/main.py --csv inputs/recruiter.csv --ats inputs/ats.json --resume inputs/resume.pdf --notes inputs/notes.txt --config config/default.json
```

---

## Example Ingestion Inputs

### ATS JSON
```json
{
  "candidateName": "John A Doe",
  "contactEmail": "john@gmail.com",
  "currentEmployer": "Google LLC",
  "jobTitle": "Software Engineer II",
  "skills": ["Java", "AWS"]
}
```

### Recruiter CSV
```csv
name,email,phone,current_company,title,skills
John Doe,john@gmail.com,9876543210,Google,Software Engineer,Java;Spring Boot
```

---

## Example Canonical Output (`canonical.json`)

```json
{
  "candidate_id": "8488e09f-0955-4cc6-8e10-911e860959f6",
  "full_name": "John Andrew Doe",
  "emails": [
    "john@gmail.com"
  ],
  "phones": [
    "+919876543210"
  ],
  "location": {},
  "links": {},
  "headline": "Senior Software Engineer",
  "years_experience": 6,
  "skills": [
    {
      "name": "Java",
      "confidence": 1.0,
      "confidence_reason": [
        "resume",
        "ats",
        "csv",
        "notes"
      ]
    }
  ],
  "overall_confidence": 0.912
}
```

---

## Confidence Strategy

Calculates the correctness of each field value deterministically using:

$$\text{confidence} = \text{base\_source\_reliability} + (0.05 \times \text{agreement\_count}) - (0.10 \times \text{conflict\_count})$$

- **Base Reliabilities**: Resume (0.95), ATS (0.90), CSV (0.75), Notes (0.60).
- **Agreement**: Adds $0.05$ for each additional agreeing source.
- **Conflict**: Subtracts $0.10$ for each conflicting source.
- Clamped strictly between $0.0$ and $1.0$.

---

## Provenance Strategy

Provides field-level traceability by recording:
1. **Source**: The origin record that contributed the winning value.
2. **Method**: The extraction strategy (e.g. `skills_section_extraction`).
3. **Winner Selected**: Flags `winner_selected_from_conflict` if a conflict was resolved using priority sorting.
4. **Source Confidence**: Trust score of the originating source.

---

## Projection Engine

Supports transforming candidate data to match custom configurations dynamically at runtime:
1. **Renaming**: Map `full_name` to `candidate_name`.
2. **Nested Path Access**: Retrieve item offsets (e.g. `emails[0]`).
3. **List Projection**: Retrieve nested keys within lists (e.g. `skills[].name`).
4. **Missing Policies**:
   - `null`: Assigns null to missing fields.
   - `omit`: Excludes the path.
   - `error`: Raises a `ProjectionError`.

---

## Testing

Run all 91 tests in the repository:
```bash
python -m pytest tests/
```

---

## Assumptions

- **Priority order**: In case of duplicate/conflicting fields, data is sorted according to `Resume > ATS > CSV > Notes`.
- **E.164 Default Region**: Missing country-code prefixes for phone numbers are resolved assuming region `IN` by default.
- **Candidate completeness**: Candidate ID, institution in education, and company in experience are considered required fields.

---

## Future Improvements

1. **Additional Adapters**: Native API connection for LinkedIn and GitHub candidate profile crawling.
2. **Semantic Skill Mapping**: Grouping similar skills (e.g. `react` and `reactjs`) semantically rather than text-based matches.
3. **Deep Learning Entity Resolution**: Applying machine learning classifiers to resolve edge cases of candidate matching.
