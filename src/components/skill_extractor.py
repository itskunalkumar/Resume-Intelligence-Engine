import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz

from src.exception import CustomException

BASE_DIR = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = BASE_DIR / "data" / "skills_taxonomy" / "skills.json"
ALIASES_PATH = BASE_DIR / "data" / "skills_taxonomy" / "aliases.json"


def normalize_text(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[\u2010-\u2015\-_/]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class SkillExtractor:
    """Hybrid skill extraction: taxonomy, aliases, phrase normalization and fuzzy matching.

    This is intentionally explainable. It is NER-style entity extraction rather than a
    claim of a statistically trained NER model. A learned NER model can be plugged in later.
    """

    def __init__(self):
        with open(TAXONOMY_PATH, encoding="utf-8") as f:
            taxonomy = json.load(f)
        aliases = {}
        if ALIASES_PATH.exists():
            with open(ALIASES_PATH, encoding="utf-8") as f:
                aliases = json.load(f)

        self.skill_to_category = {}
        for category, skills in taxonomy.items():
            for skill in skills:
                self.skill_to_category[normalize_text(skill)] = category
        self.alias_to_canonical = {}
        for canonical, values in aliases.items():
            canonical = normalize_text(canonical)
            for alias in values:
                self.alias_to_canonical[normalize_text(alias)] = canonical
        self.all_phrases = sorted(set(self.skill_to_category) | set(self.alias_to_canonical), key=len, reverse=True)

    def _canonical(self, phrase: str) -> str:
        phrase = normalize_text(phrase)
        return self.alias_to_canonical.get(phrase, phrase)

    def extract(self, text: str) -> dict:
        try:
            normalized = normalize_text(text)
            found = {}
            for phrase in self.all_phrases:
                pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
                if re.search(pattern, normalized):
                    canonical = self._canonical(phrase)
                    if canonical in self.skill_to_category:
                        found[canonical] = self.skill_to_category[canonical]
            # Conservative fuzzy recovery for short, noisy phrases.
            tokens = set(re.findall(r"[a-z][a-z0-9+#.]{1,30}", normalized))
            for phrase in self.skill_to_category:
                if " " in phrase or len(phrase) < 4 or phrase in found:
                    continue
                if any(fuzz.ratio(token, phrase) >= 94 for token in tokens):
                    found[phrase] = self.skill_to_category[phrase]
            return found
        except Exception as e:
            raise CustomException(e, sys)

    def extract_with_frequency(self, text: str) -> dict:
        try:
            normalized = normalize_text(text)
            result = {}
            for phrase in self.all_phrases:
                pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
                count = len(re.findall(pattern, normalized))
                if count:
                    canonical = self._canonical(phrase)
                    if canonical in self.skill_to_category:
                        result.setdefault(canonical, {"category": self.skill_to_category[canonical], "count": 0, "matched_phrases": []})
                        result[canonical]["count"] += count
                        result[canonical]["matched_phrases"].append(phrase)
            return result
        except Exception as e:
            raise CustomException(e, sys)

    def extract_entities(self, text: str) -> list[dict]:
        """Return explainable skill entities with source phrase and category."""
        freq = self.extract_with_frequency(text)
        return [
            {"skill": skill, "category": info["category"], "mentions": info["count"], "aliases": sorted(set(info["matched_phrases"]))}
            for skill, info in sorted(freq.items())
        ]
