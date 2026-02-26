"""LLM Service - LM Studio + OpenAI-Compatible API Integration"""
import requests
import json
import os
import random
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Security Header Intelligence: practical risk per header + industry impact
# ---------------------------------------------------------------------------

HEADER_INTELLIGENCE = {
    "Content-Security-Policy": {
        "risk": "Cross-Site Scripting (XSS) — Angreifer können Schadcode in Ihre Website einschleusen und Besucherdaten stehlen",
        "praxis": "Malware könnte Online-Terminformulare oder Patientenportale manipulieren und Gesundheitsdaten abfangen",
        "anwalt": "Angreifer könnten gefälschte Inhalte auf Ihrer Kanzlei-Website platzieren oder Kontaktformulare kapern",
        "wordpress": "XSS über verwundbare Plugins ist der häufigste WordPress-Angriffsvektor — ohne CSP kein Schutz",
    },
    "Strict-Transport-Security": {
        "risk": "Man-in-the-Middle — Datenverkehr zwischen Browser und Server kann abgefangen und mitgelesen werden",
        "praxis": "Patientendaten (Terminbuchungen, Kontaktformulare) könnten im öffentlichen WLAN mitgelesen werden",
        "anwalt": "Vertrauliche Mandantenkommunikation könnte bei der Übertragung abgefangen werden",
        "wordpress": "Login-Daten und Admin-Sessions können gestohlen werden — häufigste Ursache für gehackte WordPress-Seiten",
    },
    "X-Frame-Options": {
        "risk": "Clickjacking — Ihre Website kann unsichtbar in fremde Seiten eingebettet werden, um Besucher zu täuschen",
        "praxis": "Betrüger könnten Ihre Praxis-Website in eine Phishing-Seite einbetten, um Patientendaten abzugreifen",
        "anwalt": "Ihre Kanzlei-Seite könnte für Phishing-Angriffe missbraucht werden — Reputationsschaden inklusive",
        "wordpress": "Angreifer können Ihre Seite in einen iframe laden und Besucher zu ungewollten Aktionen verleiten",
    },
    "X-Content-Type-Options": {
        "risk": "MIME-Sniffing — Browser könnten Dateien falsch interpretieren und schädlichen Code ausführen",
        "praxis": "Hochgeladene Dokumente (z.B. PDF-Formulare) könnten als ausführbarer Code interpretiert werden",
        "anwalt": "Angehängte Dokumente auf Ihrer Website könnten als Angriffsvektor missbraucht werden",
        "wordpress": "Medien-Uploads und Plugin-Dateien könnten für Code-Injection ausgenutzt werden",
    },
    "Referrer-Policy": {
        "risk": "Datenleck — Sensible URL-Parameter werden an Drittseiten weitergegeben",
        "praxis": "Patienten-IDs oder Termin-Links in URLs könnten an externe Dienste übertragen werden",
        "anwalt": "Mandantenreferenzen in URLs könnten an Drittanbieter-Tools weitergegeben werden",
        "wordpress": "Interne Pfade und Parameter werden an externe Ressourcen übermittelt",
    },
    "Permissions-Policy": {
        "risk": "Browser-Zugriff — Drittanbieter-Skripte erhalten Zugriff auf Kamera, Mikrofon und Standort",
        "praxis": "Eingebettete Dienste könnten ohne Wissen der Patienten auf Gerätefunktionen zugreifen",
        "anwalt": "Drittanbieter-Code auf Ihrer Seite könnte Mikrofon oder Kamera der Mandanten aktivieren",
        "wordpress": "Drittanbieter-Plugins und Tracking-Scripts erhalten unkontrolliert Geräte-Zugriff",
    },
    "X-XSS-Protection": {
        "risk": "Fehlender XSS-Filter — Der Browser-eigene Schutz gegen Cross-Site Scripting ist deaktiviert",
        "praxis": "Zusätzliche Schutzschicht gegen eingeschleusten Code auf Ihrer Praxis-Website fehlt",
        "anwalt": "Browser-seitiger XSS-Schutz für Kanzlei-Website-Besucher ist nicht aktiv",
        "wordpress": "Fehlende Backup-Verteidigung gegen XSS-Angriffe neben CSP",
    },
}

# ---------------------------------------------------------------------------
# Industry Knowledge Base: deep context per target industry
# ---------------------------------------------------------------------------

INDUSTRY_CONTEXT = {
    "praxis": {
        "branche_label": "Arzt-/Zahnarzt-/Tierarztpraxis",
        "sensible_daten": "Patientendaten, Krankengeschichten, Versicherungsinformationen, Terminbuchungen",
        "regulierung": (
            "nDSG (neues Schweizer Datenschutzgesetz seit Sept. 2023) — Bussen bis CHF 250'000 "
            "bei Verstössen. Elektronisches Patientendossier (EPD) erfordert höchste Sicherheitsstandards."
        ),
        "reale_vorfaelle": (
            "2024/2025 wurden mehrere Schweizer Gesundheitseinrichtungen Opfer von Ransomware. "
            "Die Comparis-Attacke zeigte, wie schnell Gesundheitsdaten im Darknet landen."
        ),
        "schmerzpunkte": (
            "Kein IT-Personal vorhanden, Praxis-Software hat Priorität, "
            "Website wird als 'Nebensache' behandelt, Update-Zyklen werden ignoriert"
        ),
        "entscheider_typ": "Praxisinhaber/in — reagiert auf konkretes Risiko und Compliance-Pflichten, hat wenig Zeit für IT-Themen",
        "argument": "Eine einzige Sicherheitslücke kann Patientenvertrauen zerstören und nDSG-Konsequenzen nach sich ziehen",
    },
    "anwalt": {
        "branche_label": "Anwaltskanzlei / Rechtsberatung",
        "sensible_daten": "Mandantenakten, Verträge, Korrespondenz, Prozessstrategien — alles unter Anwaltsgeheimnis (Art. 13 BGFA)",
        "regulierung": (
            "nDSG, Anwaltsgeheimnis (Art. 13 BGFA), standesrechtliche Sorgfaltspflichten. "
            "Ein Datenleck kann zur Disziplinarstrafe durch die Aufsichtsbehörde führen."
        ),
        "reale_vorfaelle": (
            "Internationale Kanzleien wie DLA Piper verloren durch NotPetya Millionen. "
            "Schweizer Kanzleien sind zunehmend Ziel gezielter Phishing-Angriffe."
        ),
        "schmerzpunkte": (
            "Hoher Reputationsdruck, Mandanten erwarten absolute Vertraulichkeit, "
            "IT wird oft extern verwaltet, Website-Sicherheit hat niedrige Priorität"
        ),
        "entscheider_typ": "Managing Partner / Senior Partner — reagiert auf Reputationsrisiko und standesrechtliche Pflichten",
        "argument": "Ein Sicherheitsvorfall kann das Anwaltsgeheimnis verletzen und die gesamte Kanzleireputation gefährden",
    },
    "wordpress": {
        "branche_label": "KMU / Unternehmen mit WordPress-Website",
        "sensible_daten": "Kundendaten, Kontaktformulare, Login-Daten, geschäftliche Korrespondenz",
        "regulierung": "nDSG gilt für alle Schweizer Unternehmen. Google stuft unsichere Websites im Ranking herab.",
        "reale_vorfaelle": (
            "WordPress ist das meistangegriffene CMS weltweit — über 90'000 Angriffe pro Minute. "
            "Veraltete Plugins sind Einfallstor Nr. 1."
        ),
        "schmerzpunkte": (
            "Website wurde einmal erstellt und nie aktualisiert, Plugins veraltet, "
            "kein Monitoring, kein Budget für IT-Sicherheit"
        ),
        "entscheider_typ": "Geschäftsinhaber/in oder Marketing-Verantwortliche/r — reagiert auf SEO-Auswirkungen und Kundenvertrauen",
        "argument": "Eine gehackte Website verliert Google-Ranking, wird von Browsern als 'unsicher' markiert und vergrault Kunden",
    },
}

# ---------------------------------------------------------------------------
# Variation: opening angle pools per email type
# ---------------------------------------------------------------------------

OPENING_ANGLES = {
    "erstkontakt": [
        ("regulatory", "Fokus auf gesetzliche Pflichten (nDSG, Datenschutz, Compliance)"),
        ("technical", "Fokus auf ein spezifisches technisches Sicherheitsproblem (nenne den Header beim Namen und erkläre die Auswirkung)"),
        ("risk_scenario", "Beschreibe ein realistisches Angriffsszenario für diese Branche"),
        ("peer_comparison", "Erwähne, dass ähnliche Unternehmen in der Region bereits handeln"),
        ("discovery", "Einstieg über deine Recherche zur IT-Sicherheit in dieser Branche"),
    ],
    "nachfassen": [
        ("concrete_tip", "Gib einen Tipp, den der Empfänger sofort selbst prüfen kann (z.B. Browser-Konsole, securityheaders.com)"),
        ("news_hook", "Beziehe dich auf aktuelle Cybersecurity-Vorfälle in der Schweiz"),
        ("value_add", "Teile ein branchenspezifisches Insight zur IT-Sicherheit"),
        ("quick_check", "Beschreibe einen einfachen Selbst-Check den jeder machen kann"),
    ],
    "angebot": [
        ("problem_solution", "Verbinde das konkrete Problem direkt mit deiner Lösung"),
        ("roi_focused", "Betone die Kosten von Nichtstun vs. die geringe Investition"),
        ("social_proof", "Erwähne deine Erfahrung mit ähnlichen Kunden in der Branche"),
        ("urgency_soft", "Weise sachlich auf wachsende Bedrohungslage oder nDSG-Fristen hin"),
    ],
}

MARKETING_STRATEGIST_SYSTEM_PROMPT = """Du bist ein Marketing-Stratege für AidSec (aidsec.ch), einem Schweizer IT-Sicherheitsunternehmen.
Dein Ziel ist es, effektive Marketing-Strategien und Ideen zu generieren oder zu optimieren, 
die auf spezifische Zielgruppen wie Anwälte, Arztpraxen oder WordPress-Agenturen zugeschnitten sind.

STIL-REGELN:
- Deutsch (Schweiz).
- Professioneller, hochwertiger 'Swiss Intel' Tonfall (präzise, sicherheitsbewusst, vertrauenswürdig).
- Strukturiere deine Antwort klar mit Mardown formatting (Titel, Aufzählungen).
- Biete konkrete, umsetzbare Schritte (Actionable Steps).
- Vermeide generische Ratschläge; nutze branchenspezifische Schmerzpunkte (z.B. nDSG bei medizinischen Daten, Anwaltsgeheimnis bei Kanzleien).

Antworte NUR mit JSON im folgenden Format:
{
    "title": "Titel der Strategie",
    "description": "Ausführliche Beschreibung mit Actionable Steps im Markdown-Format"
}"""

HEADER_PRIORITY = {
    "anwalt": [
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    ],
    "praxis": [
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "X-Frame-Options",
        "Referrer-Policy",
        "X-Content-Type-Options",
        "Permissions-Policy",
    ],
    "wordpress": [
        "X-Frame-Options",
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "Permissions-Policy",
        "Referrer-Policy",
    ],
}


def pick_worst_header(ranking_details, kategorie: str) -> Optional[Dict]:
    """Select the most impactful missing header for this lead's industry.

    Returns dict with keys: name, risk, industry_risk  — or None if no data.
    """
    if not ranking_details or not isinstance(ranking_details, list):
        return None

    missing = []
    for h in ranking_details:
        if h.get("rating") == "bad":
            missing.append(h.get("name", ""))

    if not missing:
        return None

    kat = kategorie if kategorie in HEADER_PRIORITY else "wordpress"
    priority = HEADER_PRIORITY[kat]

    chosen = None
    for header_name in priority:
        if header_name in missing:
            chosen = header_name
            break
    if not chosen:
        chosen = missing[0]

    intel = HEADER_INTELLIGENCE.get(chosen, {})
    return {
        "name": chosen,
        "risk": intel.get("risk", "Sicherheitsluecke"),
        "industry_risk": intel.get(kat, intel.get("risk", "")),
    }


class LLMService:
    """Service for LLM interactions via LM Studio or any OpenAI-compatible API"""

    def __init__(self, provider: str = None):
        if provider is None:
            provider = os.getenv("DEFAULT_PROVIDER", "lm_studio")
        self.provider = provider
        self.lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.default_model = os.getenv("DEFAULT_MODEL", "llama-3")

    def _is_openai_compat(self) -> bool:
        return self.provider in ("openai", "openai_compatible")

    def is_available(self) -> bool:
        """Check if LLM provider is available"""
        result = self.test_connection()
        return result.get("success", False)

    def test_connection(self) -> Dict:
        """Test connectivity and return detailed result with error info."""
        if self.provider == "lm_studio":
            try:
                response = requests.get(f"{self.lm_studio_url}/models", timeout=3)
                if response.status_code == 200:
                    return {"success": True, "detail": f"LM Studio erreichbar ({self.lm_studio_url})"}
                return {"success": False, "detail": f"LM Studio antwortet mit HTTP {response.status_code}"}
            except requests.exceptions.ConnectionError:
                return {"success": False, "detail": f"Verbindung zu {self.lm_studio_url} fehlgeschlagen. Ist LM Studio gestartet?"}
            except Exception as e:
                return {"success": False, "detail": str(e)}

        elif self._is_openai_compat():
            if not self.openai_api_key:
                return {"success": False, "detail": "API Key fehlt."}
            try:
                url = f"{self.openai_base_url}/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_api_key}",
                }
                data = {
                    "model": self.openai_model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 1,
                }
                response = requests.post(url, json=data, headers=headers, timeout=10)
                if response.status_code == 200:
                    return {"success": True, "detail": f"Verbunden mit {self.openai_base_url} | Model: {self.openai_model}"}
                try:
                    body = response.json()
                    err_msg = body.get("error", {}).get("message", "") or body.get("base_resp", {}).get("status_msg", "") or str(body)
                except Exception:
                    err_msg = response.text[:300]
                return {"success": False, "detail": f"HTTP {response.status_code} von {self.openai_base_url}: {err_msg}"}
            except requests.exceptions.ConnectionError:
                return {"success": False, "detail": f"Verbindung zu {self.openai_base_url} fehlgeschlagen. URL korrekt?"}
            except requests.exceptions.Timeout:
                return {"success": False, "detail": f"Timeout bei Verbindung zu {self.openai_base_url} (10s)"}
            except Exception as e:
                return {"success": False, "detail": str(e)}

        return {"success": False, "detail": f"Unbekannter Provider: {self.provider}"}

    def chat(self, prompt: str, system_prompt: str = "", model: str = None, max_tokens: int = 2000) -> Dict:
        """Send a chat request to the LLM"""
        if model is None:
            model = self.openai_model if self._is_openai_compat() else self.default_model

        if self.provider == "lm_studio":
            return self._lm_studio_chat(prompt, system_prompt, model, max_tokens)
        else:
            return self._openai_chat(prompt, system_prompt, model, max_tokens)

    def _lm_studio_chat(self, prompt: str, system_prompt: str, model: str, max_tokens: int = 2000) -> Dict:
        """Send chat to LM Studio"""
        try:
            url = f"{self.lm_studio_url}/chat/completions"
            headers = {"Content-Type": "application/json"}

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": max_tokens
            }

            response = requests.post(url, json=data, headers=headers, timeout=120)
            response.raise_for_status()

            result = response.json()
            return {
                "success": True,
                "content": result["choices"][0]["message"]["content"],
                "model": model,
                "provider": "lm_studio"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"LM Studio connection failed: {str(e)}",
                "provider": "lm_studio"
            }
        except (KeyError, json.JSONDecodeError) as e:
            return {
                "success": False,
                "error": f"Failed to parse LM Studio response: {str(e)}",
                "provider": "lm_studio"
            }

    def _openai_chat(self, prompt: str, system_prompt: str, model: str, max_tokens: int = 2000) -> Dict:
        """Send chat to any OpenAI-compatible API endpoint"""
        try:
            url = f"{self.openai_base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": max_tokens
            }

            response = requests.post(url, json=data, headers=headers, timeout=60)
            response.raise_for_status()

            result = response.json()
            return {
                "success": True,
                "content": result["choices"][0]["message"]["content"],
                "model": model,
                "provider": "openai_compatible"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API error ({self.openai_base_url}): {str(e)}",
                "provider": "openai_compatible"
            }
        except (KeyError, json.JSONDecodeError) as e:
            return {
                "success": False,
                "error": f"Failed to parse API response: {str(e)}",
                "provider": "openai_compatible"
            }

    # ------------------------------------------------------------------
    # Adaptive system prompts per email type
    # ------------------------------------------------------------------

    EMAIL_SYSTEM_PROMPTS = {
        "erstkontakt": (
            "Du bist Aid Destani, IT-Sicherheitsberater bei AidSec (aidsec.ch), "
            "einem Schweizer Cybersecurity-Unternehmen.\n\n"
            "DEINE SITUATION:\n"
            "Du hast die Website dieses Unternehmens persönlich auf Sicherheitslücken "
            "geprüft und konkrete Probleme gefunden. Du schreibst jetzt eine erste, "
            "kurze Kontaktaufnahme.\n\n"
            "STIL-REGELN:\n"
            "- Deutsch (Schweiz), Siez-Form ('Sie/Ihnen/Ihre')\n"
            "- Max. 80 Wörter im E-Mail-Body (kurz und prägnant)\n"
            "- Schreibe wie ein kompetenter Berater, NICHT wie ein Verkäufer\n"
            "- Nenne das KONKRETE Sicherheitsproblem mit dem technischen Fachbegriff "
            "UND erkläre in einem Halbsatz, was es praktisch bedeutet\n"
            "- Ende mit einer offenen Frage, die Neugierde weckt\n"
            "- Betreff: max. 50 Zeichen, sachlich, KEINE Emojis\n\n"
            "VERBOTEN:\n"
            "- Kein Preis, kein Produktname, keine Links, keine Anhänge\n"
            "- Keine Wörter: kostenlos, Angebot, exklusiv, Rabatt, dringend, limitiert\n"
            "- Keine Ausrufezeichen, keine Grossbuchstaben für Betonung\n"
            "- KEINE generischen Phrasen wie 'im Rahmen meiner Tätigkeit', "
            "'ich habe festgestellt', 'ich möchte Sie darauf aufmerksam machen'\n"
            "- Jede E-Mail muss ANDERS klingen — variiere Einstieg, "
            "Satzstruktur und Fragestellung\n\n"
            "QUALITÄTSKRITERIUM:\n"
            "Die E-Mail muss so spezifisch sein, dass der Empfänger sofort merkt: "
            "'Das ist keine Massen-Mail, jemand hat sich wirklich meine Website angeschaut.'"
        ),
        "nachfassen": (
            "Du bist Aid Destani, IT-Sicherheitsberater bei AidSec (aidsec.ch), "
            "einem Schweizer Cybersecurity-Unternehmen.\n\n"
            "DEINE SITUATION:\n"
            "Du hast diesem Unternehmen bereits eine E-Mail geschickt. "
            "Du möchtest jetzt konkreten Mehrwert bieten — einen Sicherheitstipp, "
            "den der Empfänger sofort selbst prüfen kann.\n\n"
            "STIL-REGELN:\n"
            "- Deutsch (Schweiz), Siez-Form\n"
            "- Max. 100 Wörter im E-Mail-Body\n"
            "- Persönlicher und hilfsbereiter Ton als beim Erstkontakt\n"
            "- Gib einen KONKRETEN, umsetzbaren Sicherheitstipp "
            "(z.B. 'Geben Sie Ihre URL auf securityheaders.com ein...')\n"
            "- Erkläre WARUM dieser Tipp für ihre Branche relevant ist\n"
            "- Beziehe dich kurz auf die vorherige Nachricht "
            "(Betreff/Thema wird im Kontext mitgeliefert)\n"
            "- Betreff: max. 50 Zeichen, sachlich\n\n"
            "VERBOTEN:\n"
            "- Kein Preis, kein Produktname\n"
            "- Keine Wörter: kostenlos, Angebot, exklusiv, Rabatt, dringend, limitiert\n"
            "- KEINE generischen Phrasen\n"
            "- Keine Ausrufezeichen\n\n"
            "QUALITÄTSKRITERIUM:\n"
            "Der Empfänger soll denken: 'Der kennt sich aus und will mir helfen' "
            "— nicht 'Noch so eine Werbemail'."
        ),
        "angebot": (
            "Du bist Aid Destani, IT-Sicherheitsberater bei AidSec (aidsec.ch), "
            "einem Schweizer Cybersecurity-Unternehmen.\n\n"
            "DEINE SITUATION:\n"
            "Du hast diesem Unternehmen bereits geschrieben und konkreten Mehrwert "
            "geboten. Jetzt stellst du dein Angebot vor — sachlich, "
            "lösungsorientiert, ohne Druck.\n\n"
            "STIL-REGELN:\n"
            "- Deutsch (Schweiz), Siez-Form\n"
            "- Max. 120 Wörter im E-Mail-Body\n"
            "- Verbinde das KONKRETE Problem des Leads direkt mit deiner Lösung\n"
            "- Nenne Produkt, Preis und 2-3 zentrale Leistungen\n"
            "- Erkläre, warum das speziell für IHRE Branche relevant ist\n"
            "- Klarer, unaufdringlicher CTA am Ende "
            "(z.B. '15 Minuten für ein kurzes Gespräch diese Woche?')\n"
            "- Betreff: max. 50 Zeichen, sachlich\n\n"
            "VERBOTEN:\n"
            "- Keine Wörter: kostenlos, exklusiv, Rabatt, dringend, limitiert\n"
            "- Keine Ausrufezeichen, kein Druck\n\n"
            "QUALITÄTSKRITERIUM:\n"
            "Die E-Mail liest sich wie ein Angebot von einem Berater, "
            "dem man vertraut — nicht wie eine Werbe-Mail."
        ),
    }

    # ------------------------------------------------------------------
    # Context builder: assemble ALL lead data into one rich prompt block
    # ------------------------------------------------------------------

    def _build_email_context(self, lead, session, email_type: str) -> str:
        """Assemble all available lead data into a rich context block for the LLM."""
        from database.models import EmailHistory, EmailStatus
        from services.outreach import get_recommended_product

        parts = []
        kategorie = lead.kategorie.value if lead.kategorie else "wordpress"
        ranking_details = lead.ranking_details
        if isinstance(ranking_details, dict):
            nested_headers = ranking_details.get("headers")
            ranking_details = nested_headers if isinstance(nested_headers, list) else []
        elif not isinstance(ranking_details, list):
            ranking_details = []

        # -- Lead basics --
        parts.append("LEAD-DATEN:")
        parts.append(f"- Firma: {lead.firma}")
        parts.append(f"- Stadt: {lead.stadt or 'Schweiz'}")
        parts.append(f"- Website: {lead.website or 'unbekannt'}")
        parts.append(f"- Kategorie: {kategorie}")
        if lead.telefon:
            parts.append(f"- Telefon: {lead.telefon}")
            
        if hasattr(lead, "enrichment") and lead.enrichment:
            parts.append("\nERWEITERTE FIRMENDATEN (GESCRAPET):")
            if lead.enrichment.mission_statement:
                parts.append(f"- Mission / Slogan: {lead.enrichment.mission_statement}")
            if lead.enrichment.about_us:
                parts.append(f"- Über Uns / Fokus: {lead.enrichment.about_us}")
            
            parts.append("\nZUSÄTZLICHE SICHERHEITSCHECKS:")
            if lead.enrichment.ssl_valid is not None:
                ssl_status = "Gültig" if lead.enrichment.ssl_valid else "Ungültig oder Fehlend"
                parts.append(f"- SSL Zertifikat: {ssl_status}")
            if lead.enrichment.cms_detected:
                parts.append(f"- Verwendetes CMS: {lead.enrichment.cms_detected}")

        parts.append("")

        # -- Security ranking intelligence --
        worst = pick_worst_header(ranking_details, kategorie)

        if lead.ranking_grade or ranking_details:
            parts.append("SICHERHEITSANALYSE DER WEBSITE:")
            if lead.ranking_grade:
                parts.append(
                    f"- Gesamtnote: {lead.ranking_grade} "
                    "(A=exzellent, B=gut, C=mittelmässig, D=schlecht, F=kritisch)"
                )
            if lead.ranking_score is not None:
                parts.append(f"- Score: {lead.ranking_score}/100")

            if worst:
                parts.append(
                    f"\n  GRAVIERENDSTES PROBLEM (als Aufhaenger verwenden):"
                )
                parts.append(f"  * Header: {worst['name']}")
                parts.append(f"  * Risiko allgemein: {worst['risk']}")
                parts.append(
                    f"  * Konkretes Risiko fuer diesen Kunden: {worst['industry_risk']}"
                )

            if ranking_details:
                missing = []
                present = []
                for h in ranking_details:
                    name = h.get("name", "?")
                    if h.get("rating") == "bad":
                        intel = HEADER_INTELLIGENCE.get(name, {})
                        missing.append({
                            "name": name,
                            "risk": intel.get("risk", "Sicherheitsrisiko"),
                            "industry_risk": intel.get(kategorie, ""),
                        })
                    else:
                        present.append(name)

                if missing:
                    parts.append(
                        f"\n  FEHLENDE SICHERHEITS-HEADER ({len(missing)} von 7):"
                    )
                    for m in missing:
                        parts.append(f"  * {m['name']}:")
                        parts.append(f"    Allgemeines Risiko: {m['risk']}")
                        if m["industry_risk"]:
                            parts.append(
                                f"    Konkretes Risiko fuer diesen Kunden: "
                                f"{m['industry_risk']}"
                            )

                if present:
                    parts.append(f"\n  Vorhandene Header: {', '.join(present)}")
        else:
            parts.append(
                "SICHERHEITSANALYSE: Noch nicht durchgeführt "
                "(keine Ranking-Daten vorhanden)."
            )
        parts.append("")

        # -- Industry context --
        industry = INDUSTRY_CONTEXT.get(
            kategorie, INDUSTRY_CONTEXT.get("wordpress", {})
        )
        parts.append(
            f"BRANCHEN-KONTEXT ({industry.get('branche_label', kategorie)}):"
        )
        parts.append(f"- Sensible Daten: {industry.get('sensible_daten', '-')}")
        parts.append(f"- Regulierung: {industry.get('regulierung', '-')}")
        parts.append(f"- Reale Vorfälle: {industry.get('reale_vorfaelle', '-')}")
        parts.append(
            f"- Typische Schwachstellen: {industry.get('schmerzpunkte', '-')}"
        )
        parts.append(f"- Entscheider-Typ: {industry.get('entscheider_typ', '-')}")
        parts.append(f"- Kern-Argument: {industry.get('argument', '-')}")
        parts.append("")

        # -- Email history --
        try:
            history = (
                session.query(EmailHistory)
                .filter(
                    EmailHistory.lead_id == lead.id,
                    EmailHistory.status == EmailStatus.SENT,
                )
                .order_by(EmailHistory.gesendet_at.desc())
                .limit(5)
                .all()
            )
        except Exception:
            history = []

        if history:
            parts.append(
                f"BISHERIGE KOMMUNIKATION ({len(history)} E-Mail(s) gesendet):"
            )
            for i, eh in enumerate(history):
                d = (
                    eh.gesendet_at.strftime("%d.%m.%Y")
                    if eh.gesendet_at
                    else "?"
                )
                parts.append(f"  {i + 1}. [{d}] Betreff: {eh.betreff}")
                preview = (eh.inhalt or "")[:200].replace("\n", " ")
                parts.append(f"     Inhalt (Auszug): {preview}...")
            parts.append(
                "  WICHTIG: Wiederhole NICHTS aus früheren E-Mails. "
                "Bringe neue Perspektiven und Argumente."
            )
        else:
            parts.append(
                "BISHERIGE KOMMUNIKATION: Keine — dies ist der erste Kontakt."
            )
        parts.append("")

        # -- Lead notes (may contain research data from search agent) --
        if lead.notes:
            parts.append("NOTIZEN / RECHERCHE-ERGEBNISSE ZUM LEAD:")
            parts.append(lead.notes[:600])
            parts.append("")

        # -- Product context (only for Angebot) --
        if email_type == "angebot":
            product = get_recommended_product(kategorie)
            parts.append("EMPFOHLENES PRODUKT:")
            parts.append(f"- Name: {product.get('name', '?')}")
            parts.append(f"- Preis: {product.get('preis', '?')}")
            parts.append(f"- Typ: {product.get('typ', '?')}")
            features = product.get("features", [])
            if features:
                parts.append(f"- Leistungen: {'; '.join(features)}")
            arg = product.get("argument", "")
            if arg:
                parts.append(f"- Kern-Argument: {arg}")
            parts.append("")

        # -- Variation angle --
        angles = OPENING_ANGLES.get(
            email_type, OPENING_ANGLES["erstkontakt"]
        )
        _, angle_desc = random.choice(angles)
        parts.append(f"GEWÄHLTER EINSTIEGS-WINKEL: {angle_desc}")
        parts.append(
            "(Nutze diesen Winkel als kreativen Ausgangspunkt, "
            "aber bleibe natürlich und authentisch.)"
        )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Few-shot example builder (uses real lead data)
    # ------------------------------------------------------------------

    def _build_few_shot(self, lead, email_type: str) -> str:
        """Build a concrete few-shot example using the current lead's data."""
        kategorie = lead.kategorie.value if lead.kategorie else "wordpress"
        industry = INDUSTRY_CONTEXT.get(kategorie, INDUSTRY_CONTEXT.get("wordpress", {}))
        branche_label = industry.get("branche_label", kategorie)
        firma = lead.firma or "Unbekannt"
        website = lead.website or "unbekannt"
        grade = lead.ranking_grade
        worst = pick_worst_header(lead.ranking_details, kategorie)

        if grade and worst:
            return (
                f"\n--- BEISPIEL (orientiere dich am Stil, NICHT kopieren) ---\n"
                f'Betreff: {worst["name"]} fehlt bei {firma}\n'
                f"Body:\n"
                f"Guten Tag\n\n"
                f"Bei der Pruefung von {website} ist mir aufgefallen, "
                f"dass der Security-Header {worst['name']} nicht gesetzt ist. "
                f"Fuer {branche_label} bedeutet das konkret: "
                f"{worst['industry_risk']}\n\n"
                f"Ihre aktuelle Bewertung auf securityheaders.com: Note {grade}.\n\n"
                f"Darf ich Ihnen zeigen, wie sich das in 24 Stunden beheben laesst?\n\n"
                f"Freundliche Gruesse\n"
                f"Aid Destani, AidSec\n"
                f"--- ENDE BEISPIEL ---\n"
            )

        return (
            f"\n--- BEISPIEL (orientiere dich am Stil, NICHT kopieren) ---\n"
            f"Betreff: Website-Sicherheit von {firma}\n"
            f"Body:\n"
            f"Guten Tag\n\n"
            f"Im Rahmen unserer Branchenanalyse fuer {branche_label} in der Schweiz "
            f"habe ich Ihre Website {website} geprueft. "
            f"Aktuell fehlen grundlegende Sicherheits-Header, die das nDSG "
            f"fuer den Schutz von Kundendaten voraussetzt.\n\n"
            f"Ich wuerde Ihnen gerne die Ergebnisse in einem kurzen Gespraech zeigen "
            f"und eine kostenlose Analyse anbieten.\n\n"
            f"Freundliche Gruesse\n"
            f"Aid Destani, AidSec\n"
            f"--- ENDE BEISPIEL ---\n"
        )

    # ------------------------------------------------------------------
    # Main email generation method
    # ------------------------------------------------------------------

    def generate_outreach_email(
        self,
        lead,
        session,
        email_type: str = "erstkontakt",
    ) -> Dict:
        """Generate a deeply personalized outreach email using all available
        lead context: ranking intelligence, email history, notes, industry
        knowledge, and a randomly selected opening angle for variation."""
        context = self._build_email_context(lead, session, email_type)
        system_prompt = self.EMAIL_SYSTEM_PROMPTS.get(
            email_type, self.EMAIL_SYSTEM_PROMPTS["erstkontakt"]
        )

        type_label = {
            "erstkontakt": "Erstkontakt",
            "nachfassen": "Nachfassen",
            "angebot": "Angebot",
        }.get(email_type, email_type)

        kategorie = lead.kategorie.value if lead.kategorie else "wordpress"
        industry = INDUSTRY_CONTEXT.get(kategorie, INDUSTRY_CONTEXT.get("wordpress", {}))
        branche_label = industry.get("branche_label", kategorie)
        worst = pick_worst_header(lead.ranking_details, kategorie)

        if worst and lead.ranking_grade:
            mandatory_block = (
                f"\n\nPFLICHT -- Diese Daten MUESSEN woertlich in der E-Mail vorkommen:\n"
                f"- Firmenname: {lead.firma}\n"
                f"- Konkretes Sicherheitsproblem: Header '{worst['name']}' fehlt -> {worst['risk']}\n"
                f"- Branchenspezifisches Risiko: {worst['industry_risk']}\n"
                f"- Ranking-Note: {lead.ranking_grade} (von securityheaders.com)\n"
                f"- Branche: {branche_label}\n"
                f"\nWenn du diese konkreten Daten NICHT in den E-Mail-Text einbaust, "
                f"ist die E-Mail WERTLOS und generisch."
            )
        else:
            mandatory_block = (
                f"\n\nPFLICHT -- Diese Daten MUESSEN woertlich in der E-Mail vorkommen:\n"
                f"- Firmenname: {lead.firma}\n"
                f"- Branche: {branche_label}\n"
                f"- Website: {lead.website or 'unbekannt'}\n"
                f"\nEs liegen KEINE Ranking-Daten vor. Deshalb:\n"
                f"- Fokussiere auf allgemeine nDSG-Compliance-Pflichten fuer {branche_label}\n"
                f"- Biete eine KOSTENLOSE Website-Sicherheitspruefung an\n"
                f"- Beispiel-Formulierung: 'Ich wuerde gerne Ihre Website kostenlos "
                f"auf Security-Headers pruefen und Ihnen die Ergebnisse zeigen.'\n"
                f"\nWenn du den Firmennamen NICHT im E-Mail-Text verwendest, "
                f"ist die E-Mail WERTLOS und generisch."
            )

        few_shot = self._build_few_shot(lead, email_type)

        prompt = (
            f"Erstelle eine personalisierte Outreach-E-Mail (Typ: {type_label}).\n\n"
            f"Hier ist ALLES, was du ueber diesen Lead weisst — "
            f"nutze diese Informationen GEZIELT:\n\n"
            f"{context}"
            f"{mandatory_block}\n"
            f"{few_shot}\n"
            "Antworte NUR mit JSON:\n"
            "{\n"
            '    "betreff": "...",\n'
            '    "inhalt": "..."\n'
            "}"
        )

        return self.chat(prompt, system_prompt, max_tokens=2000)

    def analyze_lead(
        self,
        firma: str,
        url: str,
        grade: str = None,
        score: int = None,
        headers: list = None,
    ) -> Dict:
        """Analyze a lead's website security and generate a research summary."""
        system_prompt = """Du bist ein IT-Sicherheitsanalyst bei AidSec, einem Schweizer IT-Sicherheitsunternehmen.
Deine Aufgabe ist es, eine kurze aber fundierte Sicherheitsanalyse einer Website zu erstellen.
Sei professionell, konkret und fokussiert."""

        missing = []
        present = []
        if headers:
            for h in headers:
                if h.get("rating") == "bad":
                    missing.append(h.get("name", "?"))
                elif h.get("rating") == "good":
                    present.append(h.get("name", "?"))

        prompt = f"""Analysiere die Website-Sicherheit für folgendes Unternehmen:

- Firma: {firma}
- Website: {url}
- Security-Header Grade: {grade or 'unbekannt'}
- Security-Score: {score or 'unbekannt'}/100
- Fehlende/schlechte Header: {', '.join(missing) if missing else 'Keine Daten'}
- Vorhandene Header: {', '.join(present) if present else 'Keine Daten'}

Erstelle eine kurze Analyse (max 200 Wörter) mit:
1. Zusammenfassung der Sicherheitslage
2. Gefundene Schwachstellen und deren Risiko
3. Risikobewertung: Hoch / Mittel / Niedrig
4. 2-3 konkrete Empfehlungen

Erstelle die Antwort als JSON-Objekt mit den Feldern 'zusammenfassung', 'schwachstellen' (Liste), 'risiko' (Hoch|Mittel|Niedrig) und 'empfehlungen' (Liste).
"""
        return self.chat(prompt, system_prompt, max_tokens=1500)

    def generate_marketing_strategy(self, category: str = None, intent: str = "Taktik") -> Dict:
        """Generate a new marketing idea using the marketing-strategist skill profile."""
        prompt = f"Generiere eine innovative Marketing-Idee für AidSec. Fokus: {category or 'Allgemein'}. Absicht: {intent}."
        
        response = self.chat(prompt, MARKETING_STRATEGIST_SYSTEM_PROMPT, max_tokens=1500)
        
        if not response.get("success"):
            return {"success": False, "error": response.get("error")}
            
        from services.outreach import parse_llm_json
        try:
            data = parse_llm_json(response["content"])
            return {"success": True, "title": data.get("title", "Neue Idee"), "description": data.get("description", "")}
        except Exception as e:
            return {"success": False, "error": str(e), "raw": response["content"]}

    def optimize_marketing_strategy(self, current_title: str, current_description: str, category: str = None) -> Dict:
        """Optimize an existing marketing idea with actionable steps."""
        prompt = (
            f"Optimiere diese bestehende Marketing-Idee und mach sie actionable. Fokus-Zielgruppe: {category or 'Allgemein'}.\n\n"
            f"AKTUELLER TITEL: {current_title}\n"
            f"AKTUELLE BESCHREIBUNG: {current_description}\n\n"
            f"Formatiere die Rückgabe als weiterentwickelte, tiefergehende Strategie."
        )
        
        response = self.chat(prompt, MARKETING_STRATEGIST_SYSTEM_PROMPT, max_tokens=1500)
        
        if not response.get("success"):
            return {"success": False, "error": response.get("error")}
            
        from services.outreach import parse_llm_json
        try:
            data = parse_llm_json(response["content"])
            return {"success": True, "title": data.get("title", current_title), "description": data.get("description", "")}
        except Exception as e:
            return {"success": False, "error": str(e), "raw": response["content"]}

    def search_leads(
        self,
        stadt: str = None,
        kategorie: str = None,
        branche: str = None,
        groesse: str = None,
        schmerzpunkte: list = None,
        anzahl: int = 10,
        extra_kriterien: str = "",
    ) -> Dict:
        """Search for potential leads using LLM with full ICP context."""
        system_prompt = (
            "Du bist ein Lead-Research-Assistent für AidSec, ein Schweizer IT-Sicherheitsunternehmen "
            "mit Sitz in der Schweiz.\n\n"
            "ÜBER AIDSEC:\n"
            "AidSec bietet Website-Sicherheitslösungen an:\n"
            "- Rapid Header Fix (CHF 490): Security-Header-Optimierung in 24h, Note F→A\n"
            "- Kanzlei-Härtung (CHF 950): Komplett-Schutz für Anwaltskanzleien inkl. nDSG-Check\n"
            "- Cyber Mandat (ab CHF 89/Mt.): Laufendes Sicherheits-Monitoring\n\n"
            "ZIELKUNDEN:\n"
            "- Arztpraxen, Zahnarztpraxen, Tierarztpraxen mit eigener Website\n"
            "- Anwaltskanzleien (besonders sensibel wegen Mandatsgeheimnis & nDSG)\n"
            "- Steuerberater, Treuhänder\n"
            "- KMU mit WordPress-Websites und schlechtem Security-Ranking\n\n"
            "DEINE AUFGABE:\n"
            "Identifiziere reale, existierende Schweizer Unternehmen die zu den Suchkriterien passen. "
            "Bewerte jeden Lead mit einem Fit-Score (1-10) basierend auf:\n"
            "- Wahrscheinlichkeit von Sicherheitslücken (WordPress, veraltete Technologie)\n"
            "- Branchenrelevanz (sensible Daten = höherer Bedarf)\n"
            "- Unternehmensgrösse (KMU ohne eigene IT-Abteilung = ideal)\n"
            "- Regulatorischer Druck (nDSG, Datenschutz)\n\n"
            "Antworte NUR mit einem JSON-Array. Keine Erklärungen ausserhalb des JSON."
        )

        pain_str = ""
        if schmerzpunkte:
            pain_str = f"Schmerzpunkte/Signale: {', '.join(schmerzpunkte)}\n"

        prompt = f"""Finde {anzahl} potenzielle Leads für AidSec IT-Sicherheit mit folgenden Kriterien:

Region/Stadt: {stadt if stadt else 'Schweiz (alle Regionen)'}
Kategorie: {kategorie if kategorie else 'Alle'}
Branche: {branche if branche else 'Alle'}
Unternehmensgrösse: {groesse if groesse else 'Alle'}
{pain_str}Zusätzliche Kriterien: {extra_kriterien if extra_kriterien else 'Keine'}

Gib ein JSON-Array zurück. Jeder Lead hat folgende Felder:
- "firma": Firmenname
- "website": Website-URL (falls bekannt, sonst "")
- "stadt": Standort
- "branche": Branchenbezeichnung
- "groesse": Geschätzte Grösse (z.B. "Einzelpraxis", "5-10 MA")
- "fit_score": Bewertung 1-10 wie gut der Lead zu AidSec passt
- "fit_grund": 2-3 Sätze WARUM dieser Lead gut passt
- "entscheider": Zielperson/Rolle für Kontaktaufnahme (z.B. "Praxisinhaber", "Managing Partner")
- "kontakt_strategie": Konkreter Vorschlag wie man diesen Lead ansprechen sollte
- "wertversprechen": Spezifischer Nutzen von AidSec für DIESEN Lead
- "gespraechseinstieg": Array mit 2-3 konkreten Gesprächseinstieg-Punkten
- "bemerkung": Weitere relevante Infos

Sortiere nach fit_score absteigend (beste zuerst).

Beispiel für EIN Element:
[
    {{
        "firma": "Praxis Muster",
        "website": "praxis-muster.ch",
        "stadt": "Zürich",
        "branche": "Arztpraxis",
        "groesse": "Einzelpraxis",
        "fit_score": 8,
        "fit_grund": "Arztpraxis mit eigener Website, verarbeitet Patientendaten. Hohes nDSG-Risiko bei ungenügenden Security-Headers.",
        "entscheider": "Praxisinhaber/in",
        "kontakt_strategie": "Persönliche E-Mail mit Verweis auf nDSG-Pflichten und kostenlose Header-Prüfung anbieten.",
        "wertversprechen": "Patientendaten schützen und nDSG-konform werden mit Security-Header-Optimierung in 24h.",
        "gespraechseinstieg": ["nDSG-Konformität der Praxis-Website", "Schutz sensibler Patientendaten", "Schnelle Umsetzung ohne Praxisunterbrechung"],
        "bemerkung": "WordPress-basierte Website"
    }}
]

Antworte NUR mit dem JSON-Array. Keine Erklärungen davor oder danach."""

        return self.chat(prompt, system_prompt, max_tokens=4000)

    def recommend_marketing_ideas(self, pipeline_stats: Dict) -> Dict:
        """Recommend top marketing ideas based on current pipeline stats."""
        from services.marketing_ideas import get_condensed_catalog

        system_prompt = (
            "Du bist ein Marketing-Stratege für AidSec, ein Schweizer IT-Sicherheitsunternehmen.\n"
            "AidSec verkauft:\n"
            "- Rapid Header Fix (CHF 490): Security-Header-Optimierung in 24h\n"
            "- Kanzlei-Härtung (CHF 950): Komplett-Schutz für Anwaltskanzleien\n"
            "- Cyber Mandat (ab CHF 89/Mt.): Laufendes Monitoring\n\n"
            "Zielkunden: Arztpraxen, Anwaltskanzleien, KMU mit WordPress-Websites in der Schweiz.\n"
            "AidSec ist ein kleines Unternehmen (Einzelgründer Aid Destani), Budget ist begrenzt.\n\n"
            "Du erhältst die aktuelle Pipeline-Situation und einen Katalog von 140 Marketing-Ideen.\n"
            "Wähle die 5-7 besten Ideen aus und begründe warum sie JETZT am sinnvollsten sind.\n"
            "Berücksichtige: verfügbare Ressourcen, aktuelle Pipeline-Lage, ROI-Potenzial.\n\n"
            "Antworte NUR mit einem JSON-Array. Jedes Element:\n"
            '{"nr": <Idee-Nummer>, "warum": "<2-3 Sätze warum gerade jetzt>", '
            '"prioritaet": "hoch|mittel", "erster_schritt": "<konkreter erster Schritt>"}\n'
        )

        catalog = get_condensed_catalog()

        prompt = (
            f"Aktuelle Pipeline-Situation von AidSec:\n"
            f"- Total Leads: {pipeline_stats.get('total', 0)}\n"
            f"- Offene Leads: {pipeline_stats.get('offene', 0)}\n"
            f"- Pending: {pipeline_stats.get('pending', 0)}\n"
            f"- Gewonnen: {pipeline_stats.get('gewonnen', 0)}\n"
            f"- Verloren: {pipeline_stats.get('verloren', 0)}\n"
            f"- Praxen: {pipeline_stats.get('praxis', 0)}\n"
            f"- Anwälte: {pipeline_stats.get('anwalt', 0)}\n"
            f"- WordPress: {pipeline_stats.get('wordpress', 0)}\n"
            f"- E-Mails gesendet: {pipeline_stats.get('emails_sent', 0)}\n"
            f"- Aktive Kampagnen: {pipeline_stats.get('active_campaigns', 0)}\n"
            f"- Marketing-Ideen bereits in Umsetzung: {pipeline_stats.get('active_ideas', 0)}\n\n"
            f"Verfügbarer Ideen-Katalog:\n{catalog}\n\n"
            "Wähle die 5-7 relevantesten Ideen und begründe deine Auswahl. "
            "Antworte NUR mit dem JSON-Array."
        )

        return self.chat(prompt, system_prompt, max_tokens=3000)


_llm_service = None


def get_llm_service(provider: str = None) -> LLMService:
    """Get or create LLMService instance. Reads DEFAULT_PROVIDER from env if no arg given."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(provider)
    return _llm_service


def reset_llm_service():
    """Force re-creation on next get_llm_service() call"""
    global _llm_service
    _llm_service = None
