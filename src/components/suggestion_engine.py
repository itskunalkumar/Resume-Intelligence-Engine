import sys
from src.components.requirement_classifier import RequirementClassifier
from src.exception import CustomException

class SuggestionEngine:
    def __init__(self):
        self.classifier = RequirementClassifier()

    def analyze_gap(self, resume_skills: dict, jd_skills_with_freq: dict, jd_text: str = "") -> dict:
        try:
            resume_set = set(resume_skills)
            jd_set = set(jd_skills_with_freq)
            matched = sorted(resume_set & jd_set)
            missing = jd_set - resume_set
            must_have, nice_to_have, unspecified = [], [], []
            for skill in missing:
                info = jd_skills_with_freq[skill]
                importance = self.classifier.classify_skill(skill, jd_text, info["category"])
                entry = {
                    "skill": skill,
                    "category": info["category"],
                    "mentions_in_jd": info["count"],
                    "importance": importance,
                }
                if importance == "must_have":
                    must_have.append(entry)
                elif importance == "nice_to_have":
                    nice_to_have.append(entry)
                else:
                    unspecified.append(entry)

            key = lambda x: (-x["mentions_in_jd"], x["skill"])
            for group in (must_have, nice_to_have, unspecified):
                group.sort(key=key)

            coverage = round(len(matched) / len(jd_set) * 100, 1) if jd_set else 0.0
            non_nice = jd_set - {x["skill"] for x in nice_to_have}
            required_matched = len(set(matched) & non_nice)
            required_coverage = round(required_matched / len(non_nice) * 100, 1) if non_nice else 100.0
            return {
                "matched_skills": matched,
                "must_have_missing": must_have,
                "nice_to_have_missing": nice_to_have,
                "unspecified_missing": unspecified,
                "keyword_coverage_pct": coverage,
                "required_skill_coverage_pct": required_coverage,
            }
        except Exception as e:
            raise CustomException(e, sys)

    @staticmethod
    def _skill_action(item: dict) -> str:
        skill = item["skill"]
        return (
            f"If you genuinely have {skill} experience, add the skill using the same terminology as the JD "
            f"and support it with a concrete project, work bullet, certification, or training. Do not add it only as a keyword."
        )

    def build_suggestions(self, gap: dict) -> list[dict]:
        suggestions = []
        for item in gap["must_have_missing"]:
            suggestions.append({"priority": "high", "type": "skill_gap", "skill": item["skill"], "action": self._skill_action(item)})
        for item in gap["nice_to_have_missing"]:
            suggestions.append({"priority": "medium", "type": "skill_gap", "skill": item["skill"], "action": self._skill_action(item)})
        for item in gap["unspecified_missing"]:
            suggestions.append({"priority": "low", "type": "skill_gap", "skill": item["skill"], "action": self._skill_action(item)})
        if not suggestions:
            suggestions.append({
                "priority": "info", "type": "strength", "skill": "Skill coverage",
                "action": "No taxonomy-level skill gaps were identified. Focus on strengthening evidence, quantified impact, and requirement-specific experience."
            })
        return suggestions[:20]

    def build_optimization_plan(self, gap: dict, requirement_coverage: list[dict]) -> dict:
        """Create a transparent plan for closing gaps toward the model's 100% target.

        A 100% score is not promised. The plan separates missing skills from requirements
        that need stronger evidence, because adding a keyword cannot prove experience.
        """
        try:
            skill_actions = []
            for group, priority in ((gap["must_have_missing"], "high"), (gap["nice_to_have_missing"], "medium"), (gap["unspecified_missing"], "low")):
                for item in group:
                    skill_actions.append({
                        "skill": item["skill"],
                        "priority": priority,
                        "category": item["category"],
                        "importance": item["importance"],
                        "action": self._skill_action(item),
                    })

            evidence_gaps = []
            for item in requirement_coverage:
                if item["best_score"] < 70:
                    evidence_gaps.append({
                        "requirement": item["requirement"],
                        "score": item["best_score"],
                        "best_evidence": item["best_bullet"],
                        "action": "Add or strengthen a truthful resume bullet that directly demonstrates this requirement, with tools, scope, and measurable outcome where available."
                    })

            target = 100.0 if not skill_actions and not evidence_gaps else None
            return {
                "target_score_pct": 100.0,
                "target_is_guaranteed": False,
                "skill_gaps_to_close": skill_actions,
                "evidence_gaps_to_close": evidence_gaps,
                "message": (
                    "100% is the model target, not a hiring guarantee. Add only skills and experience you can truthfully support. "
                    "The system cannot honestly guarantee 100% by inserting keywords alone."
                ),
                "skill_gap_count": len(skill_actions),
                "evidence_gap_count": len(evidence_gaps),
            }
        except Exception as e:
            raise CustomException(e, sys)
