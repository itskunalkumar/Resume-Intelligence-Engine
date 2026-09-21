# ResuMatch — Advanced NLP Resume ↔ Job Description Matcher

An explainable NLP system that compares a resume with a job description using document parsing, hybrid technical-skill extraction, Sentence-BERT semantic matching, requirement-level coverage, section-aware scoring, ATS compatibility heuristics, and actionable gap analysis.

## What makes this version advanced?

- **Multi-format parsing:** PDF, DOCX and TXT with section-aware extraction.
- **Hybrid skill extraction:** canonical taxonomy + aliases + normalization + conservative fuzzy recovery. The extractor exposes entity provenance instead of pretending a generic NER model understands every technology.
- **Dual-layer matching:** Sentence-BERT semantic similarity plus explicit skill-gap coverage.
- **Requirement-level explainability:** every JD requirement is matched to the strongest relevant resume bullet.
- **Section-aware scoring:** Skills ↔ requirements, Experience/Projects ↔ responsibilities, Education ↔ education requirements.
- **Requirement importance classification:** explicit language such as `required`, `must`, `essential`, `preferred`, `plus`, and `bonus` is used instead of the old frequency-only rule.
- **Explainable composite score:** configurable heuristic weights combine semantic, required-skill, section, and requirement coverage. This is not a hiring probability.
- **ATS compatibility heuristics:** extractability, scanned-PDF detection, tables/images, likely columns, standard sections, contact information, and length signals.
- **What-if simulator:** recomputes semantic and skill coverage after hypothetical skill additions.
- **Production foundations:** FastAPI, Docker, non-root container, healthcheck, pytest, GitHub Actions, Docker image tags.

## Architecture

```text
Resume PDF/DOCX/TXT                         Job Description
        │                                          │
        ▼                                          ▼
 Document Parser                             JD Section Parser
        │                                          │
        ▼                                          ▼
 Section Extraction                    Requirement Extraction
        │                                          │
        └──────────────┬───────────────────────────┘
                       ▼
              Hybrid Skill Engine
       taxonomy + aliases + normalization
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
      Semantic Matcher       Keyword Gap Engine
      Sentence-BERT          matched/missing skills
            │                     │
            └──────────┬──────────┘
                       ▼
             Explainable Scoring
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
 Section Scores   Requirement Map    ATS Analysis
       │               │                │
       └───────────────┼────────────────┘
                       ▼
               Recommendation Engine
                       │
                       ▼
                   FastAPI API
                       │
                 Docker / CI-CD
```

## 100% Target Optimization

The application reports a 100% model target as an optimization goal, not a hiring guarantee. When the score is below 100%, it separates: (1) missing taxonomy skills, and (2) weak requirement evidence. The simulator can project the score after adding selected skill terms, while the UI warns that skills should only be added when they are truthfully supported.

## Scoring

The default composite score is an **explainable heuristic**, not a prediction of hiring outcome:

```text
45% semantic similarity
30% required-skill coverage
15% section alignment
10% requirement-level coverage
```

The API also returns each component separately so the result is auditable.

## API

### `POST /analyze`

Multipart form:

- `resume`: PDF, DOCX or TXT
- `job_description`: text

### `POST /simulate`

JSON:

```json
{
  "base_resume_text": "...",
  "added_skills": ["docker", "aws"],
  "job_description": "..."
}
```

### `GET /health`

Returns service status and version.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

## Run tests

```bash
pytest -q
```

## Docker

```bash
docker build -t resume-jd-matcher:latest .
docker run --rm -p 8000:8000 resume-jd-matcher:latest
```

## CI/CD

GitHub Actions runs pytest on pushes and pull requests. A successful push to `main` builds the Docker image and publishes both `latest` and commit-SHA tags to Docker Hub.

Required repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## Limitations and responsible interpretation

- The skill engine is **taxonomy/entity-rule based**, not a statistically trained custom NER model. It is designed to be transparent and extensible. A labeled resume/JD dataset can later be used to train a learned NER component.
- Sentence-BERT similarity measures semantic relatedness; it does not establish that a candidate is qualified or predict hiring decisions.
- ATS analysis is a compatibility heuristic. Different ATS products parse documents differently, so no score can guarantee acceptance or rejection.
- Resume recommendations should only add skills or claims that the candidate can substantiate.

## Suggested next research upgrade

Create a labeled dataset of skill spans and train a domain NER model, then evaluate it against the current taxonomy engine using precision, recall and F1. This would turn the extraction layer from an explainable rule system into a measurable ML component.
