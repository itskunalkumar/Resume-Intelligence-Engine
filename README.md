# 🧠 Resume Intelligence Engine

An explainable NLP system that scores how well a resume matches a job description — and tells you exactly what to add to close the gap, not just a single opaque percentage.

**🔗 Live demo:** [resume-intelligence-engine-production-e954.up.railway.app](https://resume-intelligence-engine-production-e954.up.railway.app)

---

## Why this exists

Job seekers apply into a black box: does this resume even pass the screen for this specific role? This engine answers that with a real, auditable match score, a section-by-section breakdown, requirement-level evidence mapping, and concrete missing-skill suggestions ranked by how critical the JD says they are.

## What makes this "advanced"

- **Multi-format parsing** — PDF, DOCX, and TXT, with automatic section detection (Skills, Experience, Education, Projects, Summary)
- **Hybrid skill extraction** — canonical taxonomy + alias normalization (e.g. "sklearn" → "scikit-learn") + conservative fuzzy matching, so extraction stays transparent instead of pretending a generic NER model understands every technology
- **Dual-layer matching**:
  - *Semantic similarity* (Sentence-BERT, `all-MiniLM-L6-v2`) for a relatedness score that understands "ML Engineer" and "Machine Learning Specialist" are connected
  - *Keyword-gap analysis* for concrete, specific missing skills against the taxonomy
- **Context-aware requirement classification** — missing skills are split into **required** (explicit "required"/"must"/"X+ years" language), **preferred** (explicit "nice-to-have"/"plus"/"bonus" language), and **unspecified** (mentioned without either signal) — not just frequency counting
- **Requirement-level evidence map** — every JD requirement sentence is matched against the single best-supporting resume bullet, sorted weakest-coverage-first, so you see *exactly which requirement* your resume fails to prove
- **Explainable composite score** — a transparent, auditable blend:
  ```
  45% semantic similarity
  30% required-skill coverage
  15% section alignment
  10% requirement-level coverage
  ```
  Every component is returned separately by the API — nothing is a black box.
- **"Path to 100%" optimization plan** — separates *skill gaps* (add a keyword) from *evidence gaps* (the skill exists in the JD but your resume has no bullet proving it), and explicitly states 100% is an optimization target, not a hiring guarantee — the system never tells you to add something you can't truthfully support
- **What-if score simulator** — click a missing skill and get a *real backend recomputation* of the match score, not a client-side guess
- **ATS compatibility heuristics** — flags scanned/image-based PDFs, missing section headings, tables, likely multi-column layouts, and missing contact info; explicitly marks checks it can't reliably run (e.g. column detection on DOCX) instead of silently passing them
- **Tested** — a pytest suite covers alias normalization, context-based gap classification, requirement extraction, the optimization plan, and ATS edge cases
- **Production foundations** — FastAPI, Docker (non-root user, healthcheck), GitHub Actions CI/CD, deployed on Google Cloud Run

## Architecture

```
Resume (PDF/DOCX/TXT)                        Job Description (text)
        │                                            │
        ▼                                            ▼
  Document Parser                            Requirement Extractor
  (section detection)                        (JD line/sentence split)
        │                                            │
        └───────────────────┬────────────────────────┘
                             ▼
                   Hybrid Skill Engine
            taxonomy + aliases + fuzzy recovery
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
     Semantic Matcher                Keyword Gap Engine
     (Sentence-BERT)             (required / preferred / unspecified)
              │                             │
              └──────────────┬──────────────┘
                             ▼
                  Explainable Composite Score
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                     ▼
  Section Scores    Requirement Coverage      ATS Findings
        │                    │                     │
        └────────────────────┼─────────────────────┘
                             ▼
                  Optimization Plan (path to 100%)
                             │
                             ▼
                    FastAPI JSON + Web UI
                             │
                    Docker → GitHub Actions
                             │
                     Google Cloud Run (live)
```

## Tech Stack

Python · Sentence-Transformers (`all-MiniLM-L6-v2`) · FastAPI · pdfplumber · python-docx · rapidfuzz · Docker · GitHub Actions · Google Cloud Run

## API

### `POST /analyze`
Multipart form-data: `resume` (PDF/DOCX/TXT file), `job_description` (text)

```json
{
  "overall_match_pct": 78.4,
  "section_scores": {"skills": 82.1, "experience": 71.3, "education": 45.0, "projects": 68.9, "summary": 74.2},
  "keyword_coverage_pct": 66.7,
  "matched_skills": ["python", "sql", "power bi"],
  "must_have_missing": [{"skill": "aws", "category": "cloud_devops", "mentions_in_jd": 3}],
  "nice_to_have_missing": [{"skill": "tableau", "category": "data_analysis", "mentions_in_jd": 1}],
  "unspecified_missing": [{"skill": "docker", "category": "cloud_devops"}],
  "requirement_coverage": [{"requirement": "...", "best_score": 63.7, "best_bullet": "..."}],
  "ats_findings": [{"issue": "No major heuristic issues detected", "severity": "none", "detail": "..."}],
  "optimization_plan": {"skill_gaps_to_close": [...], "evidence_gaps_to_close": [...], "message": "..."}
}
```

### `POST /simulate`
JSON: `{"base_resume_text": "...", "added_skills": ["docker", "aws"], "job_description": "..."}`
Recomputes the match score as if those skills were genuinely added — real recomputation, not a guess.

### `GET /health`
Returns service status and version.

Interactive docs: `/docs` (Swagger UI).

## Run locally

```bash
git clone https://github.com/itskunalkumar/Resume-Intelligence-Engine.git
cd Resume-Intelligence-Engine

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Visit `http://localhost:8000`.

## Run tests

```bash
pytest -q
```

## Run with Docker

```bash
docker build -t resume-intelligence-engine .
docker run --rm -p 8000:8000 resume-intelligence-engine
```

## Deployment

Deployed on **Google Cloud Run** directly from source (`gcloud run deploy --source .`), which builds the Dockerfile via Cloud Build — no manual registry push required. The container respects Cloud Run's `$PORT` convention out of the box.

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`) runs the full pytest suite on every push, then builds and publishes the Docker image to Docker Hub (`latest` + commit-SHA tags) on a successful push to `main`.

Required repository secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.

## Limitations & responsible interpretation

- Skill extraction is **taxonomy/rule-based**, not a trained NER model — it's designed to be transparent and easy to extend (add to `data/skills_taxonomy/`), not to claim understanding it doesn't have.
- Semantic similarity measures *relatedness*, not qualification — it does not predict hiring outcomes.
- ATS heuristics reflect what this tool can verify from extracted text; they can't see real document rendering, and no score guarantees acceptance by any specific ATS product.
- The optimization plan will never suggest adding a skill or claim you can't truthfully support — 100% is a target for genuine alignment, not a keyword-stuffing goal.

## Future Improvements

- [ ] Train a labeled NER model on skill spans and benchmark it against the current taxonomy engine (precision/recall/F1)
- [ ] Resume rewrite suggestions — not just *which* keyword is missing, but *where* it could naturally fit
- [ ] Support comparing multiple resume versions against the same JD

## 👤 Author

**Kunal Kumar**
Mechanical Engineering graduate transitioning into Data Science & ML Engineering
🔗 [GitHub](https://github.com/itskunalkumar)

---

⭐ If you found this project useful, consider giving it a star!