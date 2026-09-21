import re

MUST_PATTERNS = [
    r"\brequired\b", r"\bmust\b", r"\bmandatory\b", r"\bessential\b",
    r"\bminimum qualifications?\b", r"\brequired qualifications?\b", r"\bmust have\b",
    r"\bproficien(?:t|cy)\b", r"\bexperience with\b", r"\bstrong experience\b",
    r"\b(?:at least|minimum of)\s+\d+\s+(?:years?|months?)\b",
]
NICE_PATTERNS = [
    r"\bpreferred\b", r"\bpreferably\b", r"\bnice to have\b", r"\bgood to have\b",
    r"\bplus\b", r"\bbonus\b", r"\bdesirable\b", r"\bpreferred qualifications?\b",
    r"\bwould be a plus\b", r"\boptional\b",
]

class RequirementClassifier:
    """Classify requirements from contextual language rather than mention frequency."""

    def classify_text(self, text: str, section: str = "other") -> str:
        low = text.lower()
        # Explicit preferred language wins when a sentence contains both labels.
        if any(re.search(p, low) for p in NICE_PATTERNS):
            return "nice_to_have"
        if any(re.search(p, low) for p in MUST_PATTERNS):
            return "must_have"
        if section in {"requirements", "education"}:
            return "must_have"
        return "unspecified"

    @staticmethod
    def _contains_skill(sentence: str, skill: str) -> bool:
        low = sentence.lower()
        skill = skill.lower().strip()
        # Normalize common punctuation/spacing differences for phrases such as CI/CD.
        variants = {skill, skill.replace("-", " "), skill.replace("/", " "), skill.replace(" ", "")}
        return any(re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", low) for v in variants if v)

    def classify_skill(self, skill: str, jd_text: str, category: str = "other") -> str:
        # Use line/sentence context around each mention instead of the entire JD.
        chunks = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n", jd_text) if x.strip()]
        contexts = [x for x in chunks if self._contains_skill(x, skill)]
        labels = [self.classify_text(s, category) for s in contexts]
        if "must_have" in labels:
            return "must_have"
        if "nice_to_have" in labels:
            return "nice_to_have"
        return "unspecified"

    def classify_requirements(self, requirements: list[str]) -> list[dict]:
        return [{"requirement": r, "importance": self.classify_text(r)} for r in requirements]
