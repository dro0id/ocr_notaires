import urllib.request
import urllib.error
import json
import re
import time
from typing import Optional, List

class LLMAgent:
    """Agent LLM pour identifier les colonnes d un releve notaire"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = (
            "https://generativelanguage.googleapis.com/v1beta"
            "/models/gemini-2.0-flash:generateContent?key=" + api_key
        )
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

        # Retry avec backoff exponentiel pour les rate limits (429)
        delays = [2, 5, 10]
        for attempt, delay in enumerate([0] + delays):
            if delay:
                time.sleep(delay)
            try:
                req = urllib.request.Request(
                    self.url,
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
                        return colonnes
                    self.last_error = f"Réponse JSON invalide : {texte_clean}"
                    return None

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429 and attempt < len(delays):
                    # Rate limit → on réessaie
                    continue
                if e.code == 429:
                    self.last_error = (
                        "Quota Gemini dépassé (429). "
                        "Vérifiez votre plan sur https://ai.dev/rate-limit "
                        "ou attendez quelques minutes avant de réessayer."
                    )
                else:
                    self.last_error = f"Erreur HTTP {e.code} : {body[:300]}"
                return None

            except urllib.error.URLError as e:
                self.last_error = f"Erreur réseau : {e.reason}"
                return None

            except Exception as e:
                self.last_error = f"Erreur inattendue : {e}"
                return None

        return None
