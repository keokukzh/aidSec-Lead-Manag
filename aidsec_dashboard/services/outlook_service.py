"""Outlook Service - Microsoft Graph API Integration for Email Drafts"""
import secrets
import json
import requests
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# In-memory token storage (for production, use database)
# Refactored: Now uses database via the Settings table for persistence.
# We keep a local cache for performance, but sync with DB.
_token_store_cache: Dict[str, Dict] = {}


class OutlookService:
    """Service for Microsoft Graph API integration to create email drafts in Outlook."""

    def __init__(self):
        self.tenant_id = os.getenv("OUTLOOK_TENANT_ID", "common")
        self.client_id = os.getenv("OUTLOOK_CLIENT_ID", "")
        self.client_secret = os.getenv("OUTLOOK_CLIENT_SECRET", "")
        self.user_email = os.getenv("OUTLOOK_USER_EMAIL", "")
        self.redirect_uri = os.getenv("OUTLOOK_REDIRECT_URI", "http://localhost:3000/api/auth/outlook/callback")
        self.scopes = os.getenv("OUTLOOK_SCOPES", "openid profile email Mail.Read Mail.Send User.Read offline_access").split()
        self.graph_url = "https://graph.microsoft.com/v1.0"
        
        # Validation
        if not self.client_id:
            print("WARNING: OUTLOOK_CLIENT_ID is missing in .env")
        if not self.client_secret:
            print("WARNING: OUTLOOK_CLIENT_SECRET is missing in .env")
            
        self._load_tokens_from_db()

    def _load_tokens_from_db(self):
        """Load tokens from the database into the cache."""
        global _token_store_cache
        from database.database import get_session
        from database.models import Settings
        
        session = get_session()
        try:
            setting = session.query(Settings).filter(Settings.key == "outlook_token_store").first()
            if setting and setting.value:
                _token_store_cache = json.loads(setting.value)
            else:
                _token_store_cache = {}
        except Exception as e:
            print(f"Error loading outlook tokens from DB: {e}")
            _token_store_cache = {}
        finally:
            session.close()

    def _save_tokens_to_db(self):
        """Save the current token cache to the database."""
        from database.database import get_session
        from database.models import Settings
        
        session = get_session()
        try:
            setting = session.query(Settings).filter(Settings.key == "outlook_token_store").first()
            if not setting:
                setting = Settings(key="outlook_token_store")
                session.add(setting)
            
            setting.value = json.dumps(_token_store_cache)
            session.commit()
        except Exception as e:
            print(f"Error saving outlook tokens to DB: {e}")
            session.rollback()
        finally:
            session.close()

    def is_configured(self) -> bool:
        """Check if Outlook is configured"""
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""
        import urllib.parse
        scope_str = " ".join(self.scopes)
        scope_quoted = urllib.parse.quote(scope_str)
        redirect_quoted = urllib.parse.quote(self.redirect_uri)
        auth_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_quoted}"
            f"&response_mode=query"
            f"&scope={scope_quoted}"
            f"&state={state}"
        )
        return auth_url

    def exchange_code_for_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "scope": " ".join(self.scopes),
        }

        print(f"DEBUG: Exchanging code for token with redirect_uri: {self.redirect_uri}")

        try:
            response = requests.post(token_url, data=data, timeout=30)
            print(f"DEBUG: Token response status = {response.status_code}")

            if response.status_code != 200:
                print(f"DEBUG: Token exchange error ({response.status_code}): {response.text}")
                # Log specific error if possible
                try:
                    err_data = response.json()
                    print(f"DEBUG: Microsoft Error: {err_data.get('error')} - {err_data.get('error_description')}")
                except:
                    pass
                return None

            token_data = response.json()

            # Store token data
            access_token = token_data.get("access_token")
            if access_token:
                # Get user email from token
                user_email = self._get_user_email(access_token)
                if not user_email:
                    print("DEBUG: Could not get user email from token")
                    return None
                
                token_data["user_email"] = user_email
                _token_store_cache[user_email] = token_data
                self._save_tokens_to_db()
                return token_data

        except requests.exceptions.RequestException as e:
            print(f"Token exchange error: {e}")
        return None

    def refresh_token(self, user_email: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        if user_email not in _token_store_cache:
            return None

        refresh_token = _token_store_cache[user_email].get("refresh_token")
        if not refresh_token:
            return None

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(self.scopes),
        }

        try:
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code != 200:
                print(f"Refresh token error: {response.status_code} {response.text}")
                # Clear invalid token if it's a 400/401
                if response.status_code in (400, 401):
                     del _token_store_cache[user_email]
                     self._save_tokens_to_db()
                return None
                
            token_data = response.json()

            access_token = token_data.get("access_token")
            if access_token:
                # Preserve user_email
                token_data["user_email"] = user_email
                _token_store_cache[user_email] = token_data
                self._save_tokens_to_db()
                return access_token

        except requests.exceptions.RequestException as e:
            print(f"Token refresh error: {e}")
        return None

    def _get_user_email(self, access_token: str) -> Optional[str]:
        """Get user email from Graph API"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{self.graph_url}/me", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("mail") or data.get("userPrincipalName")
        except Exception as e:
            print(f"Error getting user email: {e}")
        return None

    def get_user_token(self, user_email: str = None) -> Optional[str]:
        """Get valid access token for user"""
        if user_email is None:
            user_email = self.user_email

        if not user_email and _token_store_cache:
            # Fallback to first available account
            user_email = next(iter(_token_store_cache))

        if user_email not in _token_store_cache:
            return None

        token_data = _token_store_cache[user_email]
        access_token = token_data.get("access_token")

        # Simplified check for expiry
        # In a real app we'd store issued_at + expires_in
        # For now, let's always try to refresh if it looks old or on error
        return access_token

    def is_connected(self, user_email: str = None) -> bool:
        """Check if user is connected"""
        if user_email is None:
            user_email = self.user_email
        
        if not user_email and _token_store_cache:
            return True
            
        return user_email in _token_store_cache

    def get_connected_user(self) -> Optional[str]:
        """Get currently connected user email"""
        for email in _token_store_cache:
            return email
        return None

    def disconnect(self, user_email: str = None):
        """Disconnect user (clear tokens)"""
        if user_email is None:
            user_email = self.get_connected_user()
        
        if user_email and user_email in _token_store_cache:
            del _token_store_cache[user_email]
            self._save_tokens_to_db()

    def _make_graph_request(self, method: str, endpoint: str, user_email: str = None, **kwargs) -> requests.Response:
        """Helper to make a Graph API request and automatically refresh the token on 401."""
        target_email = user_email
        if target_email is None:
            target_email = self.get_connected_user()
            
        token = self.get_user_token(target_email)
        if not token:
            # We will return a fake response with 401 to let the caller handle it
            res = requests.Response()
            res.status_code = 401
            res._content = b'{"error": {"message": "No token available"}}'
            return res

        url = f"{self.graph_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                # Token might have expired, attempt refresh
                new_token = self.refresh_token(target_email)
                if new_token:
                    headers["Authorization"] = f"Bearer {new_token}"
                    response = requests.request(method, url, headers=headers, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            # Re-raise or let the caller handle it
            raise e

    def test_connection(self, user_email: str = None) -> Dict:
        """Test the Outlook connection for a user"""
        if not self.is_configured():
            return {"success": False, "detail": "Outlook nicht konfiguriert"}

        try:
            response = self._make_graph_request("GET", "/me", user_email=user_email, timeout=10)
            if response.status_code == 200:
                user_info = response.json()
                return {
                    "success": True,
                    "detail": f"Verbunden als {user_info.get('userPrincipalName')}",
                    "user_email": user_info.get("mail") or user_info.get("userPrincipalName")
                }
            elif response.status_code == 401:
                return {"success": False, "detail": "Token abgelaufen - Bitte erneut verbinden"}
            else:
                return {"success": False, "detail": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "detail": f"Verbindungsfehler: {str(e)}"}

    def create_draft(
        self,
        subject: str,
        body: str,
        to_email: Optional[str] = None,
        body_type: str = "text",
        user_email: str = None
    ) -> Dict:
        """Create an email draft in Outlook."""
        if not self.is_configured():
            return {"success": False, "error": "Outlook nicht konfiguriert"}

        message = {
            "subject": subject,
            "body": {
                "contentType": body_type,
                "content": body
            }
        }

        if to_email:
            message["toRecipients"] = [
                {"emailAddress": {"address": to_email}}
            ]

        try:
            response = self._make_graph_request(
                "POST", "/me/messages",
                user_email=user_email,
                headers={"Content-Type": "application/json"},
                json=message,
                timeout=30
            )

            if response.status_code in (200, 201):
                draft_data = response.json()
                return {
                    "success": True,
                    "draft_id": draft_data.get("id"),
                    "web_link": draft_data.get("webLink", ""),
                    "message": f"Entwurf erstellt: {subject}"
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Fehler beim Erstellen: {str(e)}"}

    def create_draft_with_html(
        self,
        subject: str,
        html_body: str,
        to_email: Optional[str] = None,
        plain_text_fallback: Optional[str] = None,
        user_email: str = None
    ) -> Dict:
        """Create an email draft with HTML body content."""
        return self.create_draft(subject, html_body, to_email, "HTML", user_email)

    def send_email(
        self,
        subject: str,
        body: str,
        to_email: str,
        body_type: str = "HTML",
        user_email: str = None
    ) -> Dict:
        """Send an email directly via Outlook."""
        if not self.is_configured():
            return {"success": False, "error": "Outlook nicht konfiguriert"}

        message = {
            "subject": subject,
            "body": {
                "contentType": body_type,
                "content": body
            },
            "toRecipients": [
                {"emailAddress": {"address": to_email}}
            ]
        }

        try:
            response = self._make_graph_request(
                "POST", "/me/sendMail",
                user_email=user_email,
                headers={"Content-Type": "application/json"},
                json={"message": message},
                timeout=30
            )

            if response.status_code in (200, 202):
                return {
                    "success": True,
                    "message": f"E-Mail gesendet an {to_email}"
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Fehler beim Senden: {str(e)}"}

    def get_sent_emails(
        self,
        user_email: str = None,
        limit: int = 50
    ) -> Dict:
        """Get sent emails from Outlook."""
        if not self.is_configured():
            return {"success": False, "error": "Outlook nicht konfiguriert"}

        try:
            endpoint = f"/me/mailFolders/sentitems/messages?$top={limit}&$orderby=sentDateTime desc"
            response = self._make_graph_request(
                "GET", endpoint,
                user_email=user_email,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"DEBUG: get_sent_emails status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                emails = []
                for msg in data.get("value", []):
                    emails.append({
                        "id": msg.get("id"),
                        "subject": msg.get("subject"),
                        "to": [r.get("emailAddress", {}).get("address") for r in msg.get("toRecipients", [])],
                        "sent_at": msg.get("sentDateTime"),
                        "preview": msg.get("bodyPreview", "")[:100]
                    })
                return {
                    "success": True,
                    "emails": emails,
                    "total": data.get("@odata.count", len(emails))
                }
            else:
                print(f"DEBUG: get_sent_emails failed: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:100]}"}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Fehler: {str(e)}"}


# Singleton instance
_outlook_service = None


def get_outlook_service() -> OutlookService:
    """Get singleton instance of OutlookService"""
    global _outlook_service
    if _outlook_service is None:
        _outlook_service = OutlookService()
    return _outlook_service


def reset_outlook_service():
    """Force re-creation on next get_outlook_service() call"""
    global _outlook_service
    _outlook_service = None
