"""
Classe de traitement des PDF de relevés notaires
"""

import pdfplumber
import pandas as pd
import numpy as np
import io
import re
import time
from typing import List, Optional, Tuple, Dict

class PDFProcessor:
    """Traite les PDF de relevés notaires et extrait les données comptables"""
    
    def __init__(self, max_pages: int = 30, ocr_resolution: int = 150):
        """
        Initialise le processeur PDF
        
        Args:
            max_pages: Nombre maximum de pages à traiter
            ocr_resolution: Résolution pour l'OCR (si nécessaire)
        """
        self.max_pages = max_pages
        self.ocr_resolution = ocr_resolution
        self.ocr_reader = None
    
    def _load_ocr(self):
        """Charge l'OCR seulement si nécessaire (lazy loading)"""
        if self.ocr_reader is None:
            try:
                import easyocr
                self.ocr_reader = easyocr.Reader(['fr'], gpu=False, verbose=False)
            except ImportError:
                raise ImportError("EasyOCR non installé. Ajoutez 'easyocr' dans requirements.txt")
        return self.ocr_reader
    
    def _detecter_date(self, texte: str) -> bool:
        """Vérifie si le texte ressemble à une date"""
        patterns = [
            r'\d{2}[/-]\d{2}[/-]\d{2,4}',
            r'\d{2}\.\d{2}\.\d{2,4}',
            r'\d{8}'
        ]
        return any(re.match(p, str(texte).replace(' ', '')) for p in patterns)
    
    def _nettoyer_montant(self, texte: str) -> str:
        """Nettoie et valide un montant"""
        if not texte:
            return ""
        
        # Retire tous les caractères sauf chiffres, virgule, point, moins
        cleaned = re.sub(r'[^\d,.-]', '', str(texte))
        cleaned = cleaned.replace(',', '.').strip()
        
        try:
            float(cleaned)
            return cleaned
        except:
            return ""
    
    def _detecter_montants(self, liste_mots: List[str]) -> Tuple[str, str]:
        """Détecte automatiquement les colonnes débit/crédit"""
        debit, credit = "", ""
        pattern_montant = r'^-?\d+[,.]?\d*$'
        
        montants = [
            (i, m) for i, m in enumerate(liste_mots)
            if re.match(pattern_montant, str(m).replace(' ', '').replace('€', ''))
        ]
        
        if len(montants) >= 2:
            debit = self._nettoyer_montant(montants[-2][1])
            credit = self._nettoyer_montant(montants[-1][1])
        elif len(montants) == 1:
            montant = self._nettoyer_montant(montants[0][1])
            if montant.startswith('-'):
                debit = montant
            else:
                credit = montant
        
        return debit, credit
    
    def _formater_ligne(self, liste_mots: List[str]) -> Optional[List[str]]:
        """
        Formate une ligne en 6 colonnes : Date, Piece, Compte, Libelle, Debit, Credit
        """
        if not liste_mots or len(liste_mots) < 2:
            return None
        
        row = [""] * 6
        
        # Détection date (premier élément qui ressemble à une date)
        date_found = False
        for i, mot in enumerate(liste_mots[:3]):
            if self._detecter_date(str(mot)):
                row[0] = str(mot).strip()
                liste_mots = liste_mots[:i] + liste_mots[i+1:]
                date_found = True
                break
        
        # Détection montants
        debit, credit = self._detecter_montants(liste_mots)
        row[4] = debit
        row[5] = credit
        
        # Le reste = libellé (exclut montants détectés)
        libelle_parts = []
        for mot in liste_mots:
            mot_str = str(mot).strip()
            # N'ajoute pas au libellé si c'est un montant
            if mot_str not in [debit.replace('.', ','), credit.replace('.', ',')]:
                libelle_parts.append(mot_str)
        
        row[3] = " ".join(libelle_parts).strip()
        
        # Retourne seulement si on a au moins un libellé ou un montant
        if row[3] or row[4] or row[5]:
            return row
        return None
    
    def _extraire_table_native(self, page) -> List[List[str]]:
        """Extrait les données via tables PDF natives"""
        data = []
        
        table = page.extract_table()
        if table and len(table) > 1:
            for ligne in table[1:]:  # Skip header
                clean = [str(c).strip() if c else "" for c in ligne]
                if any(clean):  # Si au moins une cellule non vide
                    res = self._formater_ligne(clean)
                    if res:
                        data.append(res)
        
        return data
    
    def _extraire_avec_ocr(self, page) -> List[List[str]]:
        """Extrait les données via OCR (fallback)"""
        data = []
        
        try:
            reader = self._load_ocr()
            img = np.array(page.to_image(resolution=self.ocr_resolution).original)
            result_ocr = reader.readtext(img, detail=1)
            
            # Regroupement par ligne (basé sur coordonnée Y)
            result_ocr.sort(key=lambda x: x[0][0][1])
            
            ligne_actuelle = []
            y_ref = result_ocr[0][0][0][1] if result_ocr else 0
            seuil_y = 20  # Pixels de tolérance
            
            for (bbox, texte, _) in result_ocr:
                y_haut = bbox[0][1]
                
                if abs(y_haut - y_ref) <= seuil_y:
                    ligne_actuelle.append(texte)
                else:
                    if ligne_actuelle:
                        res = self._formater_ligne(ligne_actuelle)
                        if res:
                            data.append(res)
                    ligne_actuelle = [texte]
                    y_ref = y_haut
            
            # Dernière ligne
            if ligne_actuelle:
                res = self._formater_ligne(ligne_actuelle)
                if res:
                    data.append(res)
        
        except Exception as e:
            print(f"Erreur OCR : {e}")
        
        return data
    
    def process_pdf(self, file_bytes: bytes) -> Tuple[pd.DataFrame, Dict]:
        """
        Traite un PDF et retourne un DataFrame + statistiques
        
        Args:
            file_bytes: Contenu du PDF en bytes
            
        Returns:
            Tuple (DataFrame, dict de statistiques)
        """
        start_time = time.time()
        all_data = []
        method_used = "Table native"
        needs_ocr = False
        
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            total_pages = min(len(pdf.pages), self.max_pages)
            
            # Test si OCR nécessaire (première page)
            test_data = self._extraire_table_native(pdf.pages[0])
            if not test_data:
                needs_ocr = True
                method_used = "OCR"
            
            # Traitement de toutes les pages
            for i, page in enumerate(pdf.pages[:total_pages]):
                if needs_ocr:
                    data = self._extraire_avec_ocr(page)
                else:
                    data = self._extraire_table_native(page)
                
                all_data.extend(data)
        
        # Création DataFrame
        df = pd.DataFrame(all_data, columns=["Date", "Piece", "Compte", "Libelle", "Debit", "Credit"])
        
        # Nettoyage
        df = df[df['Libelle'].str.strip() != ""]
        df['Debit'] = df['Debit'].apply(self._nettoyer_montant)
        df['Credit'] = df['Credit'].apply(self._nettoyer_montant)
        
        # Statistiques
        stats = {
            'pages_processed': total_pages,
            'lines_extracted': len(df),
            'method': method_used,
            'processing_time': time.time() - start_time
        }
        
        return df, stats