import pdfplumber
import pandas as pd
import re
from typing import Tuple, Dict, List, Optional
import time

class PDFProcessor:
    """Classe pour traiter les PDFs et extraire les donnees comptables"""

    def __init__(self, max_pages: int = 30, ocr_resolution: int = 200, api_key: str = None):
        """
        Initialise le processeur PDF

        Args:
            max_pages: Nombre maximum de pages a traiter
            ocr_resolution: Resolution pour l extraction
            api_key: Cle API Gemini (optionnel - fallback classique si absent)
        """
        self.max_pages = max_pages
        self.ocr_resolution = ocr_resolution
        self._colonnes_detectees = None  # Cache : detecte une seule fois par PDF

        # Agent LLM optionnel
        self._agent = None
        if api_key:
            try:
                from utils.llm_agent import LLMAgent
                self._agent = LLMAgent(api_key)
            except Exception:
                self._agent = None

    def _detecter_date(self, texte: str) -> bool:
        if not texte or not isinstance(texte, str):
            return False
        patterns = [
            r'\d{2}[/.-]\d{2}[/.-]\d{4}',
            r'\d{2}[/.-]\d{2}[/.-]\d{2}',
            r'\d{4}[/.-]\d{2}[/.-]\d{2}',
            r'\d{8}',
        ]
        for pattern in patterns:
            if re.match(pattern, texte.strip()):
                return True
        return False

    def _nettoyer_montant(self, texte: str) -> str:
        if not texte or not isinstance(texte, str):
            return ""
        cleaned = texte.strip().replace(' ', '').replace('\xa0', '')
        cleaned = cleaned.replace(',', '.')
        cleaned = re.sub(r'[€$£]', '', cleaned)
        try:
            float(cleaned)
            return cleaned
        except Exception:
            return ""

    def _detecter_montants(self, ligne: List[str]) -> Tuple[str, str]:
        debit = ""
        credit = ""
        montants = []
        for cell in ligne:
            if cell:
                cleaned = self._nettoyer_montant(cell)
                if cleaned:
                    montants.append(cleaned)
        if len(montants) >= 2:
            debit = montants[-2]
            credit = montants[-1]
        elif len(montants) == 1:
            debit = montants[0]
        return debit, credit

    def _formater_avec_colonnes(self, ligne: List[str], colonnes: dict) -> Dict[str, str]:
        """
        Formate une ligne en utilisant les index detectes par le LLM.
        Methode principale quand l agent a reussi.
        """
        def get(index):
            if index is None:
                return ""
            try:
                val = ligne[index]
                return str(val).strip() if val else ""
            except (IndexError, TypeError):
                return ""

        debit_raw = get(colonnes.get("debit"))
        credit_raw = get(colonnes.get("credit"))

        # Regle metier : montant negatif = credit
        debit_clean = self._nettoyer_montant(debit_raw)
        credit_clean = self._nettoyer_montant(credit_raw)

        if debit_clean and float(debit_clean) < 0:
            credit_clean = str(abs(float(debit_clean)))
            debit_clean = ""

        return {
            'Date':    get(colonnes.get("date")),
            'Piece':   '',
            'Compte':  '',
            'Libelle': get(colonnes.get("libelle")),
            'Debit':   debit_clean,
            'Credit':  credit_clean
        }

    def _formater_ligne(self, ligne: List[str]) -> Dict[str, str]:
        """
        Formate une ligne brute.
        Utilise les colonnes LLM si disponibles, sinon logique classique.
        """
        # --- Methode LLM (si colonnes detectees) ---
        if self._colonnes_detectees:
            return self._formater_avec_colonnes(ligne, self._colonnes_detectees)

        # --- Methode classique (fallback) ---
        result = {
            'Date': '',
            'Piece': '',
            'Compte': '',
            'Libelle': '',
            'Debit': '',
            'Credit': ''
        }

        ligne_clean = [str(cell).strip() if cell else "" for cell in ligne]

        for i, cell in enumerate(ligne_clean):
            if self._detecter_date(cell):
                result['Date'] = cell
                ligne_clean[i] = ""
                break

        debit, credit = self._detecter_montants(ligne_clean)
        result['Debit'] = debit
        result['Credit'] = credit

        ligne_clean = [cell for cell in ligne_clean if cell and self._nettoyer_montant(cell) == ""]

        if len(ligne_clean) >= 3:
            result['Piece'] = ligne_clean[0]
            result['Compte'] = ligne_clean[1]
            result['Libelle'] = ' '.join(ligne_clean[2:])
        elif len(ligne_clean) == 2:
            result['Compte'] = ligne_clean[0]
            result['Libelle'] = ligne_clean[1]
        elif len(ligne_clean) == 1:
            result['Libelle'] = ligne_clean[0]

        return result

    def _extraire_table_native(self, page) -> List[List[str]]:
        all_data = []
        tables = page.extract_tables()
        for table in tables:
            if table and len(table) > 1:
                for row in table[1:]:
                    clean_row = [str(cell).strip() if cell else "" for cell in row]
                    if any(clean_row):
                        all_data.append(clean_row)
        return all_data

    def _extraire_texte_simple(self, page) -> List[List[str]]:
        text = page.extract_text()
        if not text:
            return []
        lines = text.split('\n')
        all_data = []
        for line in lines:
            if line.strip():
                cells = re.split(r'\s{2,}', line.strip())
                all_data.append(cells)
        return all_data

    def process_pdf(self, pdf_file) -> Tuple[pd.DataFrame, Dict]:
        """
        Traite un fichier PDF et extrait les donnees comptables.

        Returns:
            Tuple (DataFrame, statistiques)
        """
        start_time = time.time()
        all_data = []
        method_used = "Tableaux natifs"
        llm_used = False

        with pdfplumber.open(pdf_file) as pdf:
            pages_to_process = min(len(pdf.pages), self.max_pages)

            for i, page in enumerate(pdf.pages[:pages_to_process]):
                page_data = self._extraire_table_native(page)

                if not page_data and i == 0:
                    page_data = self._extraire_texte_simple(page)
                    if page_data:
                        method_used = "Extraction texte"

                all_data.extend(page_data)

        # Detection LLM une seule fois sur les premieres lignes
        self._colonnes_detectees = None
        if self._agent and all_data:
            colonnes = self._agent.identifier_colonnes(all_data)
            if colonnes:
                self._colonnes_detectees = colonnes
                llm_used = True
                method_used = "Agent LLM (Gemini)"

        # Formater les donnees
        formatted_data = []
        for ligne in all_data:
            formatted = self._formater_ligne(ligne)
            if any(formatted.values()):
                formatted_data.append(formatted)

        df = pd.DataFrame(formatted_data)

        processing_time = time.time() - start_time
        stats = {
            'pages_processed': pages_to_process,
            'lines_extracted': len(df),
            'method': method_used,
            'processing_time': processing_time,
            'llm_used': llm_used,
            'colonnes_detectees': self._colonnes_detectees
        }

        return df, stats
