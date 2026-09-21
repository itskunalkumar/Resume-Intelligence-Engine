import re
from src.exception import CustomException

EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_PATTERN = r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4})"
STANDARD_SECTIONS = {"skills", "experience", "education", "projects", "certifications"}

class ATSChecker:
    def check(self, raw_text: str, sections_detected: bool, document_info: dict | None = None, detected_sections: list[str] | None = None) -> dict:
        try:
            findings = []
            info = document_info or {}
            detected_sections = set(detected_sections or [])
            text = raw_text.strip()
            if len(text) < 200:
                findings.append({"issue": "Low extractable text", "severity": "high", "detail": "Very little text was extracted; a scanned/image-only document may not be machine-readable."})
            if info.get("scanned_like"):
                findings.append({"issue": "Possible scanned PDF", "severity": "high", "detail": "No PDF pages contained extractable text. OCR may be required."})
            if not sections_detected:
                findings.append({"issue": "No standard section headings detected", "severity": "high", "detail": "Use conventional headings such as Skills, Experience and Education."})
            elif not (detected_sections & STANDARD_SECTIONS):
                findings.append({"issue": "Few recognizable resume sections", "severity": "medium", "detail": "Use standard ATS-friendly section names."})
            if not re.search(EMAIL_PATTERN, text):
                findings.append({"issue": "No email detected", "severity": "medium", "detail": "Keep contact information as selectable text."})
            if not re.search(PHONE_PATTERN, text):
                findings.append({"issue": "No phone detected", "severity": "low", "detail": "Consider adding a phone number if appropriate for the application."})
            if info.get("table_count", 0) > 0:
                findings.append({"issue": "Tables detected", "severity": "medium", "detail": "Tables can affect reading order in some ATS parsers; verify the extracted order."})
            if info.get("image_count", 0) > 0:
                findings.append({"issue": "Images detected", "severity": "low", "detail": "Avoid putting critical text inside images or icons."})
            if info.get("column_detection_supported") is False:
                findings.append({"issue": "Column detection not evaluated", "severity": "info", "detail": "DOCX column detection is not implemented yet; this check is currently supported for PDF only."})
            elif info.get("possible_columns"):
                findings.append({"issue": "Possible multi-column layout", "severity": "medium", "detail": "Verify that text extraction preserves the intended reading order."})
            word_count = len(re.findall(r"\b\w+\b", text))
            if word_count > 1200:
                findings.append({"issue": "Long resume", "severity": "low", "detail": f"Approximately {word_count} words were extracted. Length is not an automatic rejection, but concise role-relevant content is easier to scan."})
            if not findings:
                findings.append({"issue": "No major heuristic issues detected", "severity": "none", "detail": "The document appears machine-readable and uses recognizable structure. This is not a guarantee of ATS acceptance."})
            weights = {"high": 25, "medium": 12, "low": 5, "info": 0, "none": 0}
            penalty = min(70, sum(weights.get(x["severity"], 0) for x in findings))
            score = max(0, 100 - penalty)
            return {"score": score, "findings": findings, "document_info": info}
        except Exception as e:
            raise CustomException(e, __import__("sys"))
