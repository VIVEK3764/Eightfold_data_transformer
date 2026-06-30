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
└── tests/                       # Pytest test suites (121 passed)
```

---

## Installation

Install all python dependencies:
```bash
pip install -r requirements.txt
```

---

## Running the Pipeline

### 1. Run with Default Schema (`config/default.json`)
To run the complete end-to-end pipeline and generate the canonical candidate profile:

**Windows PowerShell:**
```powershell
$env:PYTHONPATH="."
python src/main.py --csv inputs/recruiter.csv --ats inputs/ats.json --resume inputs/resume.pdf --notes inputs/notes.txt --config config/default.json
```

**Linux / macOS:**
```bash
PYTHONPATH=. python src/main.py --csv inputs/recruiter.csv --ats inputs/ats.json --resume inputs/resume.pdf --notes inputs/notes.txt --config config/default.json
```

### 2. Run with Custom Projection Schema (`config/custom.json`)
To run the pipeline applying custom schema projections (renaming fields, extracting nested array items, or projecting lists):

**Windows PowerShell:**
```powershell
$env:PYTHONPATH="."
python src/main.py --csv inputs/recruiter.csv --ats inputs/ats.json --resume inputs/resume.pdf --notes inputs/notes.txt --config config/custom.json
```

**Linux / macOS:**
```bash
PYTHONPATH=. python src/main.py --csv inputs/recruiter.csv --ats inputs/ats.json --resume inputs/resume.pdf --notes inputs/notes.txt --config config/custom.json
```

When executed, the pipeline outputs two files to the `output/` directory:
- `output/canonical.json`: The fully merged, standardized canonical candidate profile.
- `output/custom_output.json`: The projected custom profile shaped by the active configuration file.

---

## Example Ingestion Inputs

### ATS JSON
```json
{
  "candidateName": "Vivek K.",
  "contactEmail": "gkrmvv4726@gmail.com",
  "currentEmployer": "IIT Patna AI Lab",
  "jobTitle": "AI/ML Engineer Intern",
  "skills": ["Python", "C++", "PyTorch", "AWS"]
}
```

### Recruiter CSV
```csv
full_name,email,phone,headline,skills,location,years_experience
Vivek Kumar,gkrmvv4726@gmail.com,(+91)-91428-74726,Software Engineer Intern,Python;React.js;MySQL;Kubernetes,Bangalore KA,2
```

---

## Example Canonical Output (`canonical.json`)

```json
{
  "candidate_id": "c935a7d4-46bc-4de2-98f1-c88227164850",
  "full_name": "Vivek Kumar",
  "emails": [
    "gkrmvv4726@gmail.com"
  ],
  "phones": [
    "+919142874726"
  ],
  "location": {},
  "links": {},
  "headline": "AI/ML Engineer Intern",
  "years_experience": 2,
  "skills": [
    {
      "name": "Python",
      "confidence": 1.0,
      "confidence_reason": [
        "csv",
        "ats",
        "resume",
        "notes"
      ]
    }
  ],
  "overall_confidence": 0.971
}
```

---

## Example Projected Custom Output (`custom_output.json`)

When running the pipeline with `config/custom.json`, `output/custom_output.json` produces the transformed view:

```json
{
  "custom_profile_name": "Vivek Kumar",
  "first_email_address": "gkrmvv4726@gmail.com",
  "first_phone_number": "+919142874726",
  "custom_headline": "AI/ML Engineer Intern",
  "all_skills_list": [
    "Python",
    "React",
    "MySQL",
    "Kubernetes",
    "C++",
    "PyTorch",
    "AWS"
  ],
  "overall_confidence": 0.971
}
```

---

## Confidence Strategy

Calculates the correctness of each field value deterministically using:

```math
\text{confidence} = \text{base\_source\_reliability} + (0.05 \times \text{agreement\_count}) - (0.10 \times \text{conflict\_count})
```

Or expressed in plain text formula syntax:

```
Confidence = Base Source Reliability + (0.05 * Agreement Count) - (0.10 * Conflict Count)
```

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

Run all 121 tests in the repository:
```bash
python -m pytest tests/
```

---

## Assumptions & Descoped Items

### Assumptions
- **Priority order**: In case of duplicate/conflicting fields, data is sorted according to `Resume > ATS > CSV > Notes`.
- **E.164 Default Region**: Missing country-code prefixes for phone numbers are resolved assuming region `IN` by default.
- **Candidate completeness**: Candidate ID, institution in education, and company in experience are considered required fields.

### Descoped Items / Out of Scope
- **Live API/Web Crawling**: Live web scrapers or OAuth API integrations for LinkedIn/GitHub profiles are descoped in favor of robust ingestion of exported files (CSV, JSON, PDF/DOCX, TXT).
- **LLM/Embeddings Semantic Mapping**: Using heavyweight neural network embeddings or LLM calls for skill normalization is descoped to maintain 100% deterministic reproducibility, millisecond execution speed, and zero external API dependencies.
- **Deep Learning Graph Matching**: Graph neural networks for identity resolution are descoped in favor of deterministic BFS connected components graph clustering on exact/normalized contact identifiers.

---

## Future Improvements

1. **Additional Adapters**: Native API connection for LinkedIn and GitHub candidate profile crawling.
2. **Semantic Skill Mapping**: Grouping similar skills (e.g. `react` and `reactjs`) semantically rather than text-based matches.
3. **Deep Learning Entity Resolution**: Applying machine learning classifiers to resolve edge cases of candidate matching.

---

## Demo Video

🎥 **Watch the Walkthrough Demo (≈2 min)**: [Link to Loom/YouTube Demo Video - Insert URL here]
*(Demonstrates end-to-end pipeline execution, custom schema projection, conflict resolution, and output validation).*
