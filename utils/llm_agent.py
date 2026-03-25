import urllib.request
import json
import re
from typing import Optional

class LLMAgent:
    """Agent LLM pour identifier les colonnes d un releve notaire"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = (
            "https://generativelanguage.googleapis.com/v1beta"
            "/models/gemini-1.5-flash:generateContent?key=" + api_key
        )

    def identifier_colonnes(self, tableau_brut: list) -> Optional[dict]:
        if not tableau_brut:
            return None

        lignes_texte = []
        for ligne in tableau_brut[:5]:
            lignes_texte.append(" | ".join([str(c).strip() if c else "" for c in ligne]))

        apercu = "\n".join(lignes_texte)

        prompt = (
            "Tu es un comptable expert en releves bancaires notariaux.\n"
            "Voici les premieres lignes d un releve notaire extrait d un PDF :\n\n"
            + apercu +
            "\n\nIdentifie l index (0 = premiere colonne) de chaque type de donnee :\n"
            "- date : la colonne contenant les dates\n"
            "- libelle : la colonne contenant les descriptions / libelles\n"
            "- debit : la colonne contenant les montants debits (sorties, positifs)\n"
            "- credit : la colonne contenant les montants credits (entrees, parfois negatifs)\n\n"
            "Regles importantes :\n"
            "- Un montant negatif est un credit meme s il est dans une colonne non nommee credit\n"
            "- Si une colonne n existe pas, mets null\n"
            "- Reponds UNIQUEMENT en JSON valide, aucun texte avant ou apres\n\n"
            'Exemple de reponse attendue : {"date": 0, "libelle": 1, "debit": 2, "credit": 3}'
        )

        try:
            data = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}]
            }).encode("utf-8")

            req = urllib.request.Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                texte = result["candidates"][0]["content"]["parts"][0]["text"]
                texte_clean = re.sub(r"```json|```", "", texte).strip()
                colonnes = json.loads(texte_clean)
                cles_attendues = {"date", "libelle", "debit", "credit"}
                if isinstance(colonnes, dict) and cles_attendues.issubset(colonnes.keys()):
                    return colonnes
                return None
        except Exception:
            return None
