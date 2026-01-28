import pdfplumber
import pandas as pd
import re
from typing import Tuple, Dict, List
import time

class PDFProcessor:
    """Classe pour traiter les PDFs et extraire les données comptables"""
    
    def __init__(self, max_pages: int = 30, ocr_resolution: int = 200):
        """
        Initialise le processeur PDF
        
        Args:
            max_pages: Nombre maximum de pages à traiter
            ocr_resolution: Résolution pour l'OCR (150, 200, ou 300 DPI)
        """
        self.max_pages = max_pages
        self.ocr_resolution = ocr_resolution
        self.easyocr_reader = None  # Lazy loading
    
    def _detecter_date(self, texte: str) -> bool:
        """
        Détecte si un texte ressemble à une date
        
        Args:
            texte: Chaîne de caractères à analyser
            
        Returns:
            True si c'est une date, False sinon
        """
        if not texte or not isinstance(texte, str):
            return False
        
        # Patterns de dates courants
        patterns = [
            r'\d{2}[/.-]\d{2}[/.-]\d{4}',  # DD/MM/YYYY
            r'\d{2}[/.-]\d{2}[/.-]\d{2}',  # DD/MM/YY
            r'\d{4}[/.-]\d{2}[/.-]\d{2}',  # YYYY-MM-DD
            r'\d{8}',  # YYYYMMDD
        ]
        
        for pattern in patterns:
            if re.match(pattern, texte.strip()):
                return True
        
        return False
    
    def _nettoyer_montant(self, texte: str) -> str:
        """
        Nettoie et valide un montant
        
        Args:
            texte: Chaîne représentant un montant
            
        Returns:
            Montant nettoyé ou chaîne vide
        """
        if not texte or not isinstance(texte, str):
            return ""
        
        # Retirer les espaces et caractères spéciaux
        cleaned = texte.strip().replace(' ', '').replace('\xa0', '')
        
        # Remplacer la virgule par un point
        cleaned = cleaned.replace(',', '.')
        
        # Retirer les symboles monétaires
        cleaned = re.sub(r'[€$£]', '', cleaned)
        
        # Vérifier si c'est un nombre valide
        try:
            float(cleaned)
            return cleaned
        except:
            return ""
    
    def _detecter_montants(self, ligne: List[str]) -> Tuple[str, str]:
        """
        Détecte les colonnes débit et crédit dans une ligne
        
        Args:
            ligne: Liste de cellules de la ligne
            
        Returns:
            Tuple (debit, credit)
        """
        # Mots-clés pour identifier débit/crédit
        debit_keywords = ['débit', 'debit', 'sortie', 'retrait']
        credit_keywords = ['crédit', 'credit', 'entrée', 'dépôt']
        
        debit = ""
        credit = ""
        
        # Chercher les montants
        montants = []
        for cell in ligne:
            if cell:
                cleaned = self._nettoyer_montant(cell)
                if cleaned:
                    montants.append(cleaned)
        
        # Si 2 montants, assigner débit et crédit
        if len(montants) >= 2:
            debit = montants[-2]
            credit = montants[-1]
        elif len(montants) == 1:
            # Essayer de déterminer si c'est débit ou crédit
            # Par défaut, mettre en débit
            debit = montants[0]
        
        return debit, credit
    
    def _formater_ligne(self, ligne: List[str]) -> Dict[str, str]:
        """
        Formate une ligne brute en dictionnaire structuré
        
        Args:
            ligne: Liste de cellules brutes
            
        Returns:
            Dictionnaire avec les 6 colonnes
        """
        # Initialiser les colonnes
        result = {
            'Date': '',
            'Piece': '',
            'Compte': '',
            'Libelle': '',
            'Debit': '',
            'Credit': ''
        }
        
        # Nettoyer la ligne
        ligne_clean = [str(cell).strip() if cell else "" for cell in ligne]
        
        # Chercher la date (généralement en première position)
        for i, cell in enumerate(ligne_clean):
            if self._detecter_date(cell):
                result['Date'] = cell
                ligne_clean[i] = ""  # Retirer de la liste
                break
        
        # Détecter débit/crédit
        debit, credit = self._detecter_montants(ligne_clean)
        result['Debit'] = debit
        result['Credit'] = credit
        
        # Retirer les montants de la ligne
        ligne_clean = [cell for cell in ligne_clean if cell and self._nettoyer_montant(cell) == ""]
        
        # Les cellules restantes sont: Piece, Compte, Libelle
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
        """
        Extrait les tableaux natifs du PDF
        
        Args:
            page: Page pdfplumber
            
        Returns:
            Liste de lignes (listes de cellules)
        """
        all_data = []
        
        # Extraire les tableaux
        tables = page.extract_tables()
        
        for table in tables:
            if table and len(table) > 1:
                # Ignorer l'en-tête (première ligne)
                for row in table[1:]:
                    # Filtrer les lignes vides
                    clean_row = [str(cell).strip() if cell else "" for cell in row]
                    if any(clean_row):  # Si au moins une cellule non vide
                        all_data.append(clean_row)
        
        return all_data
    
    def _extraire_avec_ocr(self, page) -> List[List[str]]:
        """
        Extrait le texte avec OCR si les tables natives ne fonctionnent pas
        
        Args:
            page: Page pdfplumber
            
        Returns:
            Liste de lignes (listes de cellules)
        """
        # Lazy loading d'EasyOCR
        if self.easyocr_reader is None:
            try:
                import easyocr
                self.easyocr_reader = easyocr.Reader(['fr'], gpu=False)
            except ImportError:
                # Si EasyOCR n'est pas installé, utiliser extraction texte simple
                return self._extraire_texte_simple(page)
        
        # Convertir la page en image
        img = page.to_image(resolution=self.ocr_resolution)
        
        # OCR
        results = self.easyocr_reader.readtext(img.original)
        
        # Grouper les résultats par ligne (basé sur coordonnée Y)
        lines = {}
        for (bbox, text, conf) in results:
            y = int(bbox[0][1])  # Coordonnée Y
            if y not in lines:
                lines[y] = []
            lines[y].append((bbox[0][0], text))  # (X, texte)
        
        # Trier et formater
        all_data = []
        for y in sorted(lines.keys()):
            # Trier par X
            line_items = sorted(lines[y], key=lambda x: x[0])
            line_text = [item[1] for item in line_items]
            all_data.append(line_text)
        
        return all_data
    
    def _extraire_texte_simple(self, page) -> List[List[str]]:
        """
        Extraction texte simple comme fallback
        
        Args:
            page: Page pdfplumber
            
        Returns:
            Liste de lignes (listes de mots)
        """
        text = page.extract_text()
        if not text:
            return []
        
        lines = text.split('\n')
        all_data = []
        
        for line in lines:
            if line.strip():
                # Séparer par espaces multiples
                cells = re.split(r'\s{2,}', line.strip())
                all_data.append(cells)
        
        return all_data
    
    def process_pdf(self, pdf_file) -> Tuple[pd.DataFrame, Dict]:
        """
        Traite un fichier PDF et extrait les données comptables
        
        Args:
            pdf_file: Fichier PDF (UploadedFile de Streamlit)
            
        Returns:
            Tuple (DataFrame, statistiques)
        """
        start_time = time.time()
        all_data = []
        method_used = "Tableaux natifs"
        
        with pdfplumber.open(pdf_file) as pdf:
            # Limiter le nombre de pages
            pages_to_process = min(len(pdf.pages), self.max_pages)
            
            for i, page in enumerate(pdf.pages[:pages_to_process]):
                # Essayer d'abord l'extraction native
                page_data = self._extraire_table_native(page)
                
                # Si pas de données, essayer OCR sur la première page
                if not page_data and i == 0:
                    page_data = self._extraire_avec_ocr(page)
                    if page_data:
                        method_used = "OCR"
                
                all_data.extend(page_data)
        
        # Formater les données
        formatted_data = []
        for ligne in all_data:
            formatted = self._formater_ligne(ligne)
            # Filtrer les lignes complètement vides
            if any(formatted.values()):
                formatted_data.append(formatted)
        
        # Créer le DataFrame
        df = pd.DataFrame(formatted_data)
        
        # Statistiques
        processing_time = time.time() - start_time
        stats = {
            'pages_processed': pages_to_process,
            'lines_extracted': len(df),
            'method': method_used,
            'processing_time': processing_time
        }
        
        return df, stats
