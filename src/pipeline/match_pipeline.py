import sys
from src.components.ats_checker import ATSChecker
from src.components.document_parser import DocumentParser
from src.components.semantic_matcher import SemanticMatcher
from src.components.skill_extractor import SkillExtractor
from src.components.suggestion_engine import SuggestionEngine
from src.components.requirement_classifier import RequirementClassifier
from src.exception import CustomException

SCORING_WEIGHTS = {"semantic": 0.45, "required_skill": 0.30, "section": 0.15, "requirement": 0.10}

class MatchPipeline:
    def __init__(self):
        self.parser = DocumentParser()
        self.skill_extractor = SkillExtractor()
        self.matcher = SemanticMatcher()
        self.suggester = SuggestionEngine()
        self.ats_checker = ATSChecker()
        self.req_classifier = RequirementClassifier()

    @staticmethod
    def _composite(semantic: float, required_skill: float, section_scores: dict, requirement_scores: list[dict]) -> float:
        available = [v for v in section_scores.values() if v is not None]
        section_score = sum(available) / len(available) if available else semantic
        requirement_score = sum(x["best_score"] for x in requirement_scores) / len(requirement_scores) if requirement_scores else semantic
        score = (
            SCORING_WEIGHTS["semantic"] * semantic
            + SCORING_WEIGHTS["required_skill"] * required_skill
            + SCORING_WEIGHTS["section"] * section_score
            + SCORING_WEIGHTS["requirement"] * requirement_score
        )
        return round(min(100.0, max(0.0, score)), 1)

    def _analyze_text(self, raw: str, jd_text: str, doc_info: dict | None = None, headings: bool = True, detected_sections=None) -> dict:
        sections = self.parser.split_sections(raw)
        sections.pop("_headings_detected", None)
        sections.pop("_detected_section_names", None)
        jd_sections = self.parser.split_jd_sections(jd_text)

        skills_source = sections["skills"] or sections["full_text"]
        resume_skills = self.skill_extractor.extract(skills_source)
        jd_skills = self.skill_extractor.extract_with_frequency(jd_text)
        gap = self.suggester.analyze_gap(resume_skills, jd_skills, jd_text)
        semantic = self.matcher.similarity(sections["full_text"], jd_text)
        section_scores = self.matcher.section_scores(sections, jd_sections)
        bullets = self.parser.extract_bullets(sections["experience"] + "\n" + sections["projects"])
        if not bullets:
            bullets = self.parser.extract_bullets(sections["full_text"])
        requirements = self.parser.extract_requirements(jd_text)
        requirement_coverage = self.matcher.requirement_coverage(requirements, bullets)
        requirement_labels = self.req_classifier.classify_requirements(requirements)
        label_by_requirement = {x["requirement"]: x["importance"] for x in requirement_labels}
        for item in requirement_coverage:
            item["importance"] = label_by_requirement.get(item["requirement"], "unspecified")
        composite = self._composite(semantic, gap["required_skill_coverage_pct"], section_scores, requirement_coverage)
        optimization = self.suggester.build_optimization_plan(gap, requirement_coverage)
        return {
            "overall_match_pct": composite,
            "explainable_match_pct": composite,
            "semantic_score_pct": semantic,
            "required_skill_coverage_pct": gap["required_skill_coverage_pct"],
            "keyword_coverage_pct": gap["keyword_coverage_pct"],
            "section_scores": section_scores,
            "matched_skills": gap["matched_skills"],
            "resume_skill_entities": self.skill_extractor.extract_entities(skills_source),
            "jd_skill_entities": self.skill_extractor.extract_entities(jd_text),
            "must_have_missing": gap["must_have_missing"],
            "nice_to_have_missing": gap["nice_to_have_missing"],
            "unspecified_missing": gap["unspecified_missing"],
            "suggestions": self.suggester.build_suggestions(gap),
            "ats_score": None,
            "ats_findings": [],
            "document_info": doc_info or {},
            "sections_detected": detected_sections or [],
            "requirement_classification": requirement_labels,
            "requirement_coverage": requirement_coverage,
            "optimization_plan": optimization,
            "resume_full_text": raw,
            "scoring_method": SCORING_WEIGHTS,
            "disclaimer": "Scores are explainable heuristics, not a probability of hiring or a guarantee of ATS acceptance. A 100% target cannot be guaranteed by adding keywords alone.",
        }

    def run(self, resume_bytes: bytes, resume_filename: str, jd_text: str) -> dict:
        try:
            if not jd_text or len(jd_text.strip()) < 30:
                raise ValueError("Job description is too short. Provide at least 30 characters.")
            raw = self.parser.extract_text(resume_bytes, resume_filename)
            if len(raw.strip()) < 30:
                raise ValueError("Could not extract enough text from the resume.")
            sections = self.parser.split_sections(raw)
            headings = sections["_headings_detected"]
            detected_sections = sections["_detected_section_names"]
            doc_info = self.parser.inspect_document(resume_bytes, resume_filename)
            result = self._analyze_text(raw, jd_text, doc_info, headings, detected_sections)
            ats = self.ats_checker.check(raw, headings, doc_info, detected_sections)
            result["ats_score"] = ats["score"]
            result["ats_findings"] = ats["findings"]
            result["ats_summary"] = {
                "score": ats["score"],
                "column_detection_supported": doc_info.get("column_detection_supported", False),
            }
            return result
        except Exception as e:
            raise CustomException(e, sys)

    def simulate_addition(self, base_resume_text: str, added_skills: list[str], jd_text: str) -> dict:
        try:
            unique = []
            for skill in added_skills:
                if skill and skill.strip() and skill.strip().lower() not in {x.lower() for x in unique}:
                    unique.append(skill.strip())
            augmented = base_resume_text + "\nSkills: " + ", ".join(unique)
            result = self._analyze_text(augmented, jd_text)
            return {
                "overall_match_pct": result["overall_match_pct"],
                "explainable_match_pct": result["explainable_match_pct"],
                "semantic_score_pct": result["semantic_score_pct"],
                "keyword_coverage_pct": result["keyword_coverage_pct"],
                "required_skill_coverage_pct": result["required_skill_coverage_pct"],
                "remaining_must_have": result["must_have_missing"],
                "remaining_evidence_gaps": result["optimization_plan"]["evidence_gaps_to_close"],
            }
        except Exception as e:
            raise CustomException(e, sys)
