import io
import pdfplumber
import pandas as pd
import re
from typing import Tuple, Dict, List, Optional
import time

class PDFProcessor:
    """Classe pour traiter les PDFs et extraire les donnees comptables"""

    def __init__(self, max_pages: int = 30, ocr_resolution: int = 200, api_key: str = None):
        self.max_pages = max_pages
        self.ocr_resolution = ocr_resolution
        self._colonnes_detectees = None
        self._headers = []

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
        """Nettoie un montant en gérant les formats français (1.234,56 ou 1 234,56)."""
        if not texte or not isinstance(texte, str):
            return ""
        cleaned = re.sub(r'[€$£\xa0]', '', texte).strip()
        if not cleaned:
            return ""

        negative = cleaned.startswith('-')
        if negative:
            cleaned = cleaned[1:].strip()

        # Format avec point ET virgule : le dernier est le séparateur décimal
        if '.' in cleaned and ',' in cleaned:
            last_dot = cleaned.rfind('.')
            last_comma = cleaned.rfind(',')
            if last_comma > last_dot:
                # 1.234,56 → décimal = virgule
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # 1,234.56 → décimal = point
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Uniquement virgule → séparateur décimal (format français)
            cleaned = cleaned.replace(',', '.')

        # Supprimer espaces restants (séparateur milliers)
        cleaned = cleaned.replace(' ', '')

        if negative:
            cleaned = '-' + cleaned

        try:
            float(cleaned)
            return cleaned
        except Exception:
            return ""

    def _detecter_montants(self, ligne: List[str]) -> Tuple[str, str]:
        """Détecte débit et crédit dans une ligne sans colonnes connues."""
        debit = ""
        credit = ""
        montants = []
        for cell in ligne:
            if cell:
                cleaned = self._nettoyer_montant(cell)
                if cleaned:
                    montants.append(cleaned)

        if len(montants) >= 2:
            # Dernier montant non-nul = crédit, avant-dernier = débit
            # Sauf si l'un est négatif
            m1, m2 = montants[-2], montants[-1]
            if float(m1) < 0:
                credit = str(abs(float(m1)))
            else:
                debit = m1
            if float(m2) < 0:
                credit = str(abs(float(m2)))
            else:
                if not debit:
                    debit = m2
                else:
                    credit = m2
        elif len(montants) == 1:
            val = float(montants[0])
            if val < 0:
                credit = str(abs(val))
            else:
                debit = montants[0]
        return debit, credit

    def _formater_avec_colonnes(self, ligne: List[str], colonnes: dict) -> Dict[str, str]:
        """Formate une ligne en utilisant les index détectés par le LLM."""
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

        debit_clean = self._nettoyer_montant(debit_raw)
        credit_clean = self._nettoyer_montant(credit_raw)

        # Montant négatif dans colonne débit = crédit
        if debit_clean and float(debit_clean) < 0:
            credit_clean = str(abs(float(debit_clean)))
            debit_clean = ""

        # Montant négatif dans colonne crédit = valeur absolue
        if credit_clean and float(credit_clean) < 0:
            credit_clean = str(abs(float(credit_clean)))

        return {
            'Date':    get(colonnes.get("date")),
            'Piece':   '',
            'Compte':  '',
            'Libelle': get(colonnes.get("libelle")),
            'Debit':   debit_clean,
            'Credit':  credit_clean
        }

    def _formater_ligne(self, ligne: List[str]) -> Dict[str, str]:
        if self._colonnes_detectees:
            return self._formater_avec_colonnes(ligne, self._colonnes_detectees)

        result = {
            'Date': '', 'Piece': '', 'Compte': '',
            'Libelle': '', 'Debit': '', 'Credit': ''
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

    def _extraire_table_native(self, page) -> Tuple[List[str], List[List[str]]]:
        """Retourne (en-têtes, lignes_données) depuis les tables natives."""
        headers = []
        data_rows = []
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            # Première ligne = en-tête
            if not headers and len(table) > 0:
                headers = [str(cell).strip() if cell else "" for cell in table[0]]
            # Reste = données
            for row in table[1:]:
                clean_row = [str(cell).strip() if cell else "" for cell in row]
                if any(clean_row):
                    data_rows.append(clean_row)
        return headers, data_rows

    def _extraire_texte_simple(self, page) -> List[List[str]]:
        text = page.extract_text()
        if not text:
            return []
        all_data = []
        for line in text.split('\n'):
            if line.strip():
                cells = re.split(r'\s{2,}', line.strip())
                all_data.append(cells)
        return all_data

    def _page_en_image(self, fitz_doc, page_index: int) -> bytes:
        """Convertit une page PDF en PNG via PyMuPDF."""
        import fitz
        page = fitz_doc[page_index]
        mat = fitz.Matrix(self.ocr_resolution / 72, self.ocr_resolution / 72)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")

    def process_pdf(self, pdf_file) -> Tuple[pd.DataFrame, Dict]:
        start_time = time.time()
        all_data = []
        all_headers = []
        method_used = "Tableaux natifs"
        llm_used = False
        ocr_used = False
        ocr_error = None
        fitz_available = False

        # Lire les bytes — getvalue() est toujours disponible sur UploadedFile Streamlit
        # et ne dépend pas de la position du curseur (contrairement à read())
        if hasattr(pdf_file, 'getvalue'):
            pdf_bytes = pdf_file.getvalue()
        else:
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()

        # Vérifier si PyMuPDF est disponible
        try:
            import fitz
            fitz_available = True
        except ImportError:
            fitz_available = False

        # Ouvrir PyMuPDF si dispo + clé API présente
        fitz_doc = None
        if self._agent and fitz_available:
            try:
                import fitz
                fitz_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            except Exception as e:
                ocr_error = f"Erreur ouverture PyMuPDF : {e}"

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_to_process = min(len(pdf.pages), self.max_pages)
            pages_scannees = 0

            for i, page in enumerate(pdf.pages[:pages_to_process]):
                headers, page_data = self._extraire_table_native(page)

                if headers and not all_headers:
                    all_headers = headers

                if not page_data:
                    page_data = self._extraire_texte_simple(page)
                    if page_data and method_used == "Tableaux natifs":
                        method_used = "Extraction texte"

                # Vérifier si les données extraites sont réellement utiles :
                # une ligne doit contenir AU MOINS une date ET un montant
                data_utile = any(
                    any(self._detecter_date(str(cell)) for cell in row if cell)
                    and
                    any(bool(self._nettoyer_montant(str(cell))) for cell in row if cell)
                    for row in page_data
                ) if page_data else False

                # Si pas de données utiles → page scannée ou extraction garbage
                if not data_utile:
                    pages_scannees += 1
                    page_data = []  # ignorer les données garbage
                    if fitz_doc:
                        try:
                            img_bytes = self._page_en_image(fitz_doc, i)
                            ocr_data = self._agent.ocr_page(img_bytes)
                            if ocr_data:
                                if not all_headers and len(ocr_data) > 1:
                                    all_headers = ocr_data[0]
                                    page_data = ocr_data[1:]
                                else:
                                    page_data = ocr_data
                                ocr_used = True
                        except Exception as e:
                            ocr_error = f"Erreur OCR page {i+1} : {e}"

                all_data.extend(page_data)

        if fitz_doc:
            fitz_doc.close()

        # Si pages scannées détectées mais pas d'OCR possible → expliquer pourquoi
        if pages_scannees > 0 and not ocr_used and not ocr_error:
            if not self._agent:
                ocr_error = (
                    f"PDF scanné détecté ({pages_scannees} page(s) sans texte). "
                    "Ajoutez une clé API Gemini dans la sidebar pour activer l'OCR automatique."
                )
            elif not fitz_available:
                ocr_error = (
                    f"PDF scanné détecté ({pages_scannees} page(s) sans texte). "
                    "PyMuPDF non disponible — redéployez l'application pour installer les dépendances."
                )

        # Formatage
        formatted_data = []
        for ligne in all_data:
            formatted = self._formater_ligne(ligne)
            if any(formatted.values()):
                formatted_data.append(formatted)

        # Si aucune donnée formatée → message d'aide contextuel
        if not formatted_data and not ocr_error:
            if not self._agent:
                ocr_error = (
                    "Aucune donnée comptable trouvée. "
                    "Si le PDF est scanné, ajoutez une clé API Gemini dans la sidebar pour activer l'OCR."
                )
            elif not fitz_available:
                ocr_error = (
                    "Aucune donnée comptable trouvée. "
                    "PyMuPDF non disponible — redéployez l'application pour installer les dépendances."
                )

        # Détection LLM avec en-têtes + premières lignes
        self._colonnes_detectees = None
        llm_error = None
        if ocr_used:
            method_used = "OCR Vision (Gemini)"
        if self._agent and all_data:
            colonnes = self._agent.identifier_colonnes(all_data, all_headers)
            if colonnes:
                self._colonnes_detectees = colonnes
                llm_used = True
                method_used = "OCR + Agent LLM (Gemini)" if ocr_used else "Agent LLM (Gemini)"
            else:
                llm_error = getattr(self._agent, 'last_error', None)

        df = pd.DataFrame(formatted_data)

        if not df.empty:
            for col in ['Debit', 'Credit']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        processing_time = time.time() - start_time
        stats = {
            'pages_processed': pages_to_process,
            'lines_extracted': len(df),
            'method': method_used,
            'processing_time': processing_time,
            'llm_used': llm_used,
            'llm_error': llm_error,
            'ocr_error': ocr_error,
            'colonnes_detectees': self._colonnes_detectees
        }

        return df, stats
