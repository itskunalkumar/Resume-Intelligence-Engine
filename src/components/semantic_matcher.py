import sys
import numpy as np
from sentence_transformers import SentenceTransformer, util
from src.exception import CustomException
from src.logger import logging

MODEL_NAME = "all-MiniLM-L6-v2"

class SemanticMatcher:
    def __init__(self):
        self.model = None

    def load(self):
        if self.model is None:
            logging.info("Loading sentence-transformer model: %s", MODEL_NAME)
            self.model = SentenceTransformer(MODEL_NAME)
        return self.model

    def encode(self, texts: list[str]):
        return self.load().encode(texts, convert_to_tensor=True, normalize_embeddings=True)

    def similarity(self, text_a: str, text_b: str) -> float:
        try:
            if not text_a.strip() or not text_b.strip():
                return 0.0
            emb = self.encode([text_a, text_b])
            return round(float(max(0.0, util.cos_sim(emb[0], emb[1]).item())) * 100, 1)
        except Exception as e:
            raise CustomException(e, sys)

    def best_match(self, query: str, candidates: list[str]) -> tuple[float, str]:
        if not query.strip() or not candidates:
            return 0.0, ""
        q = self.encode([query])
        c = self.encode(candidates)
        scores = util.cos_sim(q, c)[0].cpu().numpy()
        idx = int(np.argmax(scores))
        return round(float(max(0.0, scores[idx])) * 100, 1), candidates[idx]

    def section_scores(self, resume_sections: dict, jd_sections: dict) -> dict:
        # Explicit section-to-section alignment; no silent full-JD fallback.
        mappings = {
            "skills": ["requirements", "preferred"],
            "experience": ["responsibilities", "requirements"],
            "education": ["education", "requirements"],
            "projects": ["responsibilities", "requirements"],
            "summary": ["summary", "responsibilities"],
        }
        scores = {}
        for resume_key, jd_keys in mappings.items():
            a = resume_sections.get(resume_key, "").strip()
            candidates = [jd_sections.get(k, "").strip() for k in jd_keys]
            candidates = [x for x in candidates if x]
            if not a or not candidates:
                scores[resume_key] = None
                continue
            scores[resume_key] = max(self.similarity(a, b) for b in candidates)
        return scores

    def requirement_coverage(self, requirements: list[str], bullets: list[str]) -> list[dict]:
        if not requirements or not bullets:
            return []
        req_emb = self.encode(requirements)
        bullet_emb = self.encode(bullets)
        matrix = util.cos_sim(req_emb, bullet_emb)
        results = []
        for i, req in enumerate(requirements):
            row = matrix[i].cpu().numpy()
            idx = int(np.argmax(row))
            results.append({"requirement": req, "best_score": round(float(max(0.0, row[idx])) * 100, 1), "best_bullet": bullets[idx]})
        return sorted(results, key=lambda x: x["best_score"])
