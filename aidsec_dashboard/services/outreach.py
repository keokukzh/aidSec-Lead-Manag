"""Outreach - Zentrales Modul fuer Produkte, E-Mail-Typen und Hilfsfunktionen."""
import json
import re
from typing import Dict, List, Optional, Union


PRODUCT_CATALOG: Dict[str, Dict] = {
    "rapid_header_fix": {
        "name": "Rapid Header Fix",
        "preis": "CHF 490.–",
        "typ": "Einmalige Optimierung",
        "zielgruppe": "Einzelkanzleien, Praxen, WordPress-Seiten",
        "features": [
            "Behebung Note F zu A (SecurityHeaders.com)",
            "Implementierung HSTS & CSP",
            "X-Frame-Options (Clickjacking Schutz)",
            "Umsetzung innerhalb von 24h",
        ],
        "argument": "≈ 0.05% der Ø Ransomware-Kosten (CHF 1 Mio.)",
    },
    "kanzlei_haertung": {
        "name": "Kanzlei-Härtung",
        "preis": "CHF 950.–",
        "typ": "Komplett-Schutz",
        "zielgruppe": "Schweizer Anwaltskanzleien",
        "features": [
            "Alles aus «Rapid Header Fix»",
            "Login-Verschleierung & Brute-Force Schutz",
            "Professionelle Firewall-Konfiguration",
            "nDSG-Konformitäts-Check",
            "Schriftliches Audit-Protokoll",
        ],
        "argument": "Schutz vor Reputationsschaden und nDSG-Verstössen",
    },
    "cyber_mandat": {
        "name": "Cyber Mandat",
        "preis": "ab CHF 89.– /Mt.",
        "typ": "Monatliche Betreuung",
        "zielgruppe": "Kanzleien, die nichts dem Zufall überlassen",
        "features": [
            "Kontinuierliches Sicherheits-Monitoring",
            "Monatlicher Sicherheitsbericht für Partner",
            "Priorisierter Notfall-Support",
            "Cloud-Backups auf Schweizer Servern",
        ],
        "argument": "Laufende Absicherung statt punktueller Reaktion",
    },
}

KATEGORIE_PRODUCT_MAP: Dict[str, str] = {
    "praxis": "rapid_header_fix",
    "wordpress": "rapid_header_fix",
    "anwalt": "kanzlei_haertung",
}

EMAIL_TYPE_LABELS: Dict[str, str] = {
    "erstkontakt": "Erstkontakt",
    "nachfassen": "Nachfassen",
    "angebot": "Angebot",
}

EMAIL_TYPE_COLORS: Dict[str, str] = {
    "erstkontakt": "#3498db",
    "nachfassen": "#f39c12",
    "angebot": "#2ecc71",
}


def detect_email_type(sent_count: int) -> str:
    """Auto-detect the appropriate email type based on how many emails
    have already been sent to a lead."""
    if sent_count == 0:
        return "erstkontakt"
    elif sent_count <= 2:
        return "nachfassen"
    return "angebot"


def get_recommended_product(kategorie: str) -> Dict:
    """Return full product details for a lead category."""
    key = KATEGORIE_PRODUCT_MAP.get(kategorie, "rapid_header_fix")
    return PRODUCT_CATALOG[key]


def get_recommended_product_key(kategorie: str) -> str:
    """Return product key for a lead category."""
    return KATEGORIE_PRODUCT_MAP.get(kategorie, "rapid_header_fix")


def parse_llm_json(
    content: str, expect_array: bool = False
) -> Union[Dict, List]:
    """Robustly extract JSON from LLM response, stripping markdown fences."""
    cleaned = content.strip()
    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    if expect_array:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])

    return json.loads(cleaned)
