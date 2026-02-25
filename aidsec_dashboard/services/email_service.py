"""E-Mail Service - SMTP Integration"""
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    """Service for sending emails via SMTP"""

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_name = os.getenv("SMTP_FROM_NAME", "AidSec Team")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@aidsec.ch")

    def is_configured(self) -> bool:
        """Check if SMTP is configured"""
        return bool(self.host and self.username and self.password)

    def test_connection(self) -> Dict:
        """Test SMTP connection"""
        if not self.is_configured():
            return {"success": False, "error": "SMTP not configured"}

        try:
            server = smtplib.SMTP(self.host, self.port, timeout=10)
            server.ehlo()
            server.starttls()
            server.login(self.username, self.password)
            server.quit()
            return {"success": True, "message": "Connection successful!"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
        logo_b64: Optional[str] = None,
        logo_mime: Optional[str] = None,
    ) -> Dict:
        """Send an email. Always sends multipart (plain + HTML) for deliverability."""
        if not self.is_configured():
            return {"success": False, "error": "SMTP not configured"}

        try:
            has_logo = bool(logo_b64 and logo_mime)
            from_header = f"{self.from_name} <{self.from_email}>"

            if has_logo:
                msg = MIMEMultipart("related")
                alt_part = MIMEMultipart("alternative")
                alt_part.attach(MIMEText(body, "plain"))
                html_body = body if html else _text_to_html(body, include_logo_cid=True)
                alt_part.attach(MIMEText(html_body, "html"))
                msg.attach(alt_part)

                logo_bytes = base64.b64decode(logo_b64)
                subtype = logo_mime.split("/")[-1] if "/" in logo_mime else "png"
                img = MIMEImage(logo_bytes, _subtype=subtype)
                img.add_header("Content-ID", "<signature_logo>")
                img.add_header("Content-Disposition", "inline", filename=f"logo.{subtype}")
                msg.attach(img)
            else:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body, "plain"))
                html_body = body if html else _text_to_html(body)
                msg.attach(MIMEText(html_body, "html"))

            msg["From"] = from_header
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Reply-To"] = self.from_email
            msg["Sender"] = self.from_email

            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.ehlo()
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.from_email, to_email, msg.as_string())
            server.quit()

            return {"success": True, "message": f"Email sent to {to_email}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def render_template(self, template: str, variables: Dict) -> str:
        """Render email template with variables"""
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result


def _text_to_html(text: str, include_logo_cid: bool = False) -> str:
    """Convert plain text to HTML, preserving line breaks.

    When include_logo_cid is True an <img> referencing cid:signature_logo
    is appended after the signature separator (-- ).
    """
    import html as html_mod
    escaped = html_mod.escape(text)
    body_html = escaped.replace("\n", "<br>")

    logo_tag = ""
    if include_logo_cid:
        logo_tag = (
            '<br><img src="cid:signature_logo" '
            'style="max-width:140px;height:auto;" alt="Logo" />'
        )

    if include_logo_cid and "-- <br>" in body_html:
        body_html = body_html.replace(
            "-- <br>",
            "-- <br>" + logo_tag + "<br>",
            1,
        )
    elif include_logo_cid:
        body_html += logo_tag

    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;">'
        + body_html
        + "</div>"
    )


DEFAULT_TEMPLATES = {
    "erstkontakt": {
        "name": "Erstkontakt",
        "betreff": "Kurze Frage zur Website-Sicherheit — {firma}",
        "inhalt": """Guten Tag,

bei einer Analyse von Websites in {stadt} ist mir aufgefallen, dass {firma} aktuell einige Sicherheitslücken aufweist.

Konkret fehlen wichtige Schutzmechanismen, die sensible Daten gefährden könnten — besonders relevant seit dem neuen Datenschutzgesetz (nDSG).

Darf ich Ihnen die Ergebnisse kurz zusenden?

Freundliche Grüsse
{absender_name}
""",
    },
    "nachfassen": {
        "name": "Nachfassen",
        "betreff": "Sicherheitshinweis für {firma}",
        "inhalt": """Guten Tag,

ich hatte Ihnen kürzlich bezüglich der Website-Sicherheit von {firma} geschrieben.

Ein konkreter Tipp: Ihrer Website fehlt der HTTP-Header «Strict-Transport-Security». Das bedeutet, dass Verbindungen zu Ihrer Seite nicht erzwungen verschlüsselt werden — ein Risiko für sensible Daten.

Solche Lücken lassen sich innerhalb von 24 Stunden beheben. Gerne zeige ich Ihnen in einem kurzen Gespräch, welche Massnahmen sinnvoll wären.

Freundliche Grüsse
{absender_name}
""",
    },
    "angebot": {
        "name": "Angebot",
        "betreff": "Konkrete Lösung für die Website-Sicherheit von {firma}",
        "inhalt": """Guten Tag,

ich melde mich nochmals zum Thema Website-Sicherheit von {firma}.

Mit {produkt} ({preis}) beheben wir innerhalb kurzer Zeit die wichtigsten Sicherheitslücken Ihrer Website — darunter HSTS, Content-Security-Policy und Clickjacking-Schutz.

Das Ergebnis: Von der aktuellen Note auf Note A bei SecurityHeaders.com, nDSG-konform.

Wäre ein kurzes Gespräch diese Woche möglich?

Freundliche Grüsse
{absender_name}
""",
    },
    "kanzlei_erstkontakt": {
        "name": "Kanzlei Erstkontakt",
        "betreff": "Sicherheitsanalyse Ihrer Kanzlei-Website — {firma}",
        "inhalt": """Sehr geehrte Damen und Herren,

wir überprüfen im Rahmen unserer Sicherheitsforschung regelmässig zufällig ausgewählte Webseiten von Schweizer Kanzleien und Notariaten. Der Grund: In Ihrer Branche ist die digitale Vertraulichkeit (Anwaltsgeheimnis) das höchste Gut.

Ihre Kanzlei-Domain {website} wurde bei unserem aktuellen Scan analysiert und hat auf der unabhängigen Prüfplattform SecurityHeaders.com leider das Ergebnis "Note F" (ungenügend) erhalten.

Was bedeutet das konkret für Ihre Kanzlei?
Ihrer Webseite fehlen kritische HTTP-Security-Headers. Dies macht Ihre WordPress-Installation zu einem leichten Ziel für automatisierte Angriffe. Zu den fehlenden Schutzmechanismen gehören unter anderem:

- Fehlende Content-Security-Policy (CSP): Ohne CSP können Angreifer schädlichen Code auf Ihrer Seite einschleusen (Cross-Site Scripting), um beispielsweise Mandantendaten oder Passwörter abzufangen.

- Fehlendes Strict-Transport-Security (HSTS): Erlaubt sogenannte "Man-in-the-Middle"-Angriffe, bei denen die Kommunikation zwischen Ihren Mandanten und Ihrer Webseite mitgelesen werden kann.

- Fehlende X-Frame-Options: Ermöglicht "Clickjacking". Angreifer können Ihre Webseite unsichtbar überbauen und Besucher dazu bringen, ungewollt Klicks auszuführen.

Im Hinblick auf das revidierte Schweizer Datenschutzgesetz (nDSG Art. 8) stellt dieser Zustand ein vermeidbares Haftungsrisiko dar.

Die Lösung innert 24 Stunden
Als Schweizer Spezialist für Cybersicherheit (aidsec.ch) helfen wir Kanzleien dabei, diese Sicherheitslücken diskret zu schliessen. Mit unserer bewährten "Kanzlei-Härtung" beheben wir nicht nur die Note F, sondern implementieren zusätzlich eine professionelle Firewall und einen Login-Schutz.

- 0 Minuten Ausfallzeit
- Kein Zugriff auf Mandantendaten nötig
- Inkl. nDSG-Audit-Protokoll für Ihre Akten

Ihre nächsten Schritte:

1. Prüfen Sie Ihr Resultat selbst: https://securityheaders.com/?q={website}

2. Für das AidSec Kanzlei-Onboarding: https://aidsec.ch/#preise

Sie müssen für die Umsetzung keine technischen Kenntnisse haben. In unserem Onboarding können Sie uns einfach Ihren IT-Betreuer nennen, und wir klären die Umsetzung direkt von Techniker zu Techniker.

Bei Rückfragen stehe ich Ihnen gerne persönlich zur Verfügung.

Freundliche Grüsse

Aid Destani
Founder & Security Expert
aidsec.ch
""",
    },
    "praxis_erstkontakt": {
        "name": "Praxis Erstkontakt",
        "betreff": "Sicherheitsanalyse Ihrer Praxis-Website — {firma}",
        "inhalt": """Sehr geehrte Damen und Herren,

wir überprüfen im Rahmen unserer Sicherheitsforschung regelmässig Webseiten von Schweizer Arztpraxen. Der Grund: In Ihrer Branche verwalten Sie Gesundheitsdaten – die mit Abstand sensibelste Datenkategorie unter dem revidierten Schweizer Datenschutzgesetz (nDSG).

Ihre Praxis-Domain {website} wurde bei unserem aktuellen Scan analysiert und hat auf der unabhängigen IT-Prüfplattform SecurityHeaders.com leider das Ergebnis "Note F" (ungenügend) erhalten.

Was bedeutet das konkret für Ihre Praxis?
Ihrer Webseite fehlen grundlegende HTTP-Security-Headers. Dies macht Ihre Seite zu einem leichten Ziel für automatisierte Bot-Angriffe. Zu den konkreten Risiken gehören:

- Fehlende Content-Security-Policy (CSP): Angreifer können schädlichen Code auf Ihrer Webseite einschleusen, um beispielsweise Anfragen aus Ihrem Kontaktformular oder Online-Terminbuchungen heimlich abzufangen.

- Fehlendes Strict-Transport-Security (HSTS): Erlaubt Angreifern, die Kommunikation zwischen Ihren Patienten und Ihrer Webseite mitzulesen.

- Fehlende X-Frame-Options: Ermöglicht Betrügern, Ihre Webseite unsichtbar zu überbauen und das Vertrauen in Ihren Praxisnamen für Phishing zu missbrauchen.

Ohne diese technischen Massnahmen (nach Art. 8 nDSG) tragen Sie als Praxisinhaber ein erhebliches Haftungsrisiko.

Die schnelle Lösung: Der Rapid Header Fix
Als Schweizer Experten für Cybersicherheit (aidsec.ch) beheben wir diese Schwachstellen innert 24 Stunden. Mit unserem Paket "Rapid Header Fix" bringen wir Ihre Seite sofort von Note F auf die Bestnote A.

- 0 Minuten Ausfallzeit: Ihr Praxisbetrieb läuft ungestört weiter.
- 100% Diskret: Wir benötigen keinen Zugriff auf Ihre Patientendaten.
- Rechtssicher: Sie erhalten ein schriftliches Audit-Protokoll für Ihre Unterlagen.

Ihre nächsten Schritte:

1. Prüfen Sie Ihr Resultat selbst: https://securityheaders.com/?q={website}

2. Für das AidSec Praxis-Onboarding: https://aidsec.ch/#preise

Wichtig: Sie benötigen für die Umsetzung keine IT-Kenntnisse. Starten Sie einfach das Onboarding und hinterlegen Sie die E-Mail-Adresse Ihres IT-Betreuers. Wir klären die technische Umsetzung dann direkt von Techniker zu Techniker.

Bei Rückfragen stehe ich Ihnen gerne persönlich zur Verfügung.

Freundliche Grüsse

Aid Destani
Founder & Security Expert
aidsec.ch
""",
    },
}

OPT_OUT_FOOTER = ""


_email_service = None


def get_email_service() -> EmailService:
    """Get or create EmailService instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def reset_email_service():
    """Force re-creation on next get_email_service() call"""
    global _email_service
    _email_service = None
