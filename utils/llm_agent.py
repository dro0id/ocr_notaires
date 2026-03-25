import urllib.request
import urllib.error
import base64
import json
import re
import time
from typing import Optional, List

class LLMAgent:
    """Agent LLM pour identifier les colonnes d un releve notaire"""

    # Modèles tentés dans l'ordre (du plus récent au plus ancien)
    MODELS = [
        "gemini-2.5-flash-lite",  # Meilleur free tier new users (GA depuis 2026)
        "gemini-2.5-flash",       # Fallback 2.5
        "gemini-2.0-flash",       # Fallback legacy (retire juin 2026)
    ]
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_error = None

    def identifier_colonnes(self, tableau_brut: list, headers: List[str] = None) -> Optional[dict]:
        self.last_error = None
        if not tableau_brut:
            return None

        lignes_texte = []

        # Inclure les en-têtes si disponibles (crucial pour identifier les colonnes)
        if headers and any(headers):
            lignes_texte.append("EN-TÊTES : " + " | ".join(headers))

        # Inclure jusqu'à 10 premières lignes de données
        for ligne in tableau_brut[:10]:
            lignes_texte.append(" | ".join([str(c).strip() if c else "" for c in ligne]))

        apercu = "\n".join(lignes_texte)

        prompt = (
            "Tu es un comptable expert en relevés bancaires notariaux français.\n"
            "Voici les premières lignes d'un relevé notaire extrait d'un PDF :\n\n"
            + apercu +
            "\n\nIdentifie l'index (0 = première colonne) de chaque type de donnée :\n"
            "- date : colonne contenant les dates (ex: 01/01/2024, formats DD/MM/YYYY)\n"
            "- libelle : colonne contenant les descriptions / libellés des opérations\n"
            "- debit : colonne contenant les montants débits (sorties d'argent, valeurs positives)\n"
            "- credit : colonne contenant les montants crédits (entrées d'argent)\n\n"
            "Règles importantes :\n"
            "- Les en-têtes de colonnes peuvent être en français : DEBIT, CREDIT, LIBELLE, DATE, MONTANT, etc.\n"
            "- Un montant négatif dans la colonne débit = crédit\n"
            "- Certains relevés n'ont qu'une colonne montant : mets debit=index et credit=null\n"
            "- Si une colonne n'existe pas, mets null\n"
            "- Réponds UNIQUEMENT en JSON valide, aucun texte avant ou après\n\n"
            'Exemple de réponse : {"date": 0, "libelle": 2, "debit": 3, "credit": 4}'
        )

        data = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode("utf-8")

        # Essayer chaque modèle dans l'ordre
        for model in self.MODELS:
            url = self.BASE_URL.format(model=model, key=self.api_key)
            if self._appeler_api(url, data):
                return self._resultat
            # Si 404 (modèle indisponible), passer au suivant
            if self._dernier_code == 404:
                continue
            # Autre erreur → arrêter
            return None

        return None

    def _appeler_api(self, url: str, data: bytes) -> bool:
        """Tente l'appel API avec retry sur 429. Retourne True si succès."""
        self._resultat = None
        self._dernier_code = None
        delays = [2, 5, 10]
        for attempt, delay in enumerate([0] + delays):
            if delay:
                time.sleep(delay)
            try:
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=20) as response:
                    result = json.loads(response.read())
                    texte = result["candidates"][0]["content"]["parts"][0]["text"]
                    texte_clean = re.sub(r"```json|```", "", texte).strip()
                    colonnes = json.loads(texte_clean)
                    cles_attendues = {"date", "libelle", "debit", "credit"}
                    if isinstance(colonnes, dict) and cles_attendues.issubset(colonnes.keys()):
                        self._resultat = colonnes
                        return True
                    self.last_error = f"Réponse JSON invalide : {texte_clean}"
                    return False

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                self._dernier_code = e.code
                if e.code == 429 and attempt < len(delays):
                    continue
                try:
                    api_msg = json.loads(body).get("error", {}).get("message", body[:300])
                except Exception:
                    api_msg = body[:300]
                self.last_error = f"Erreur HTTP {e.code} : {api_msg}"
                return False

            except urllib.error.URLError as e:
                self.last_error = f"Erreur réseau : {e.reason}"
                return False

            except Exception as e:
                self.last_error = f"Erreur inattendue : {e}"
                return False

        return False

    def ocr_page(self, image_bytes: bytes) -> List[List[str]]:
        """OCR une page scannée via Gemini Vision. Retourne liste de lignes."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "Cette image est une page d'un relevé bancaire notarial français.\n"
            "Extrais toutes les lignes du tableau visible.\n"
            "Retourne UNIQUEMENT un JSON valide : liste de listes de strings.\n"
            "Inclus la ligne d'en-tête en premier.\n"
            'Exemple : [["Date","Libellé","Débit","Crédit"],["01/01/2024","Virement","100",""]]\n'
            "Si aucun tableau visible, retourne []."
        )

        data = json.dumps({
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                    {"text": prompt}
                ]
            }]
        }).encode("utf-8")

        for model in self.MODELS:
            url = self.BASE_URL.format(model=model, key=self.api_key)
            try:
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read())
                    texte = result["candidates"][0]["content"]["parts"][0]["text"]
                    texte_clean = re.sub(r"```json|```", "", texte).strip()
                    rows = json.loads(texte_clean)
                    if isinstance(rows, list):
                        return [[str(c) for c in row] for row in rows if row]
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
            except Exception:
                pass

        return []
