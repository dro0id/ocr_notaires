import streamlit as st
import pdfplumber
import pandas as pd
import easyocr
import numpy as np
import io
import re
from typing import List, Optional

st.set_page_config(page_title="ONLY COMPTA - OCR_NOTAIRES", layout="wide")
st.title("⚖️ Convertisseur Relevé de Notaire")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr'], gpu=False)  # Spécifier GPU explicitement

def nettoyer_montant(texte: str) -> str:
    """Nettoie et valide un montant"""
    if not texte:
        return ""
    # Remplace virgule par point, retire espaces
    cleaned = texte.replace(',', '.').replace(' ', '').strip()
    # Valide le format nombre
    try:
        float(cleaned)
        return cleaned
    except:
        return ""

def detecter_colonnes_montants(mots: List[str]) -> tuple:
    """Détecte automatiquement quels éléments sont des montants"""
    debit, credit = "", ""
    pattern_montant = r'^-?\d+[,.]?\d*$'
    
    montants = [(i, m) for i, m in enumerate(mots) 
                if re.match(pattern_montant, m.replace(' ', ''))]
    
    if len(montants) >= 2:
        debit = nettoyer_montant(montants[-2][1])
        credit = nettoyer_montant(montants[-1][1])
    elif len(montants) == 1:
        # Détecter signe ou position
        montant = nettoyer_montant(montants[0][1])
        if montant.startswith('-'):
            debit = montant
        else:
            credit = montant
    
    return debit, credit

def formater_ligne_notaire(liste_mots: List[str]) -> Optional[List[str]]:
    """Formate une ligne en 6 colonnes avec détection intelligente"""
    if not liste_mots or len(liste_mots) < 2:
        return None
    
    row = [""] * 6
    row[0] = str(liste_mots[0]).strip()  # Date
    
    # Détection automatique des montants
    debit, credit = detecter_colonnes_montants(liste_mots[1:])
    row[4] = debit
    row[5] = credit
    
    # Le reste = libellé (exclut date et montants)
    libelle_parts = []
    for mot in liste_mots[1:]:
        if mot not in [debit.replace('.', ','), credit.replace('.', ',')]:
            libelle_parts.append(str(mot))
    
    row[3] = " ".join(libelle_parts).strip()
    
    return row

def regrouper_par_ligne(ocr_results, seuil_y_relatif=0.4):
    """Regroupe avec seuil adaptatif basé sur la hauteur médiane"""
    if not ocr_results:
        return []
    
    # Calcul hauteur médiane des boîtes
    hauteurs = [bbox[2][1] - bbox[0][1] for bbox, _, _ in ocr_results]
    hauteur_mediane = np.median(hauteurs) if hauteurs else 20
    seuil_y = hauteur_mediane * seuil_y_relatif
    
    ocr_results.sort(key=lambda x: x[0][0][1])
    lignes = []
    ligne_actuelle = []
    y_ref = ocr_results[0][0][0][1]
    
    for (bbox, texte, prob) in ocr_results:
        y_haut = bbox[0][1]
        if abs(y_haut - y_ref) <= seuil_y:
            ligne_actuelle.append((bbox[0][0], texte))
        else:
            if ligne_actuelle:
                ligne_actuelle.sort(key=lambda x: x[0])
                lignes.append([t for x, t in ligne_actuelle])
            ligne_actuelle = [(bbox[0][0], texte)]
            y_ref = y_haut
    
    if ligne_actuelle:
        ligne_actuelle.sort(key=lambda x: x[0])
        lignes.append([t for x, t in ligne_actuelle])
    
    return lignes

# --- INTERFACE ---
reader = load_ocr()

uploaded_file = st.file_uploader("Déposez votre PDF ici", type="pdf")

if uploaded_file is not None:
    try:
        all_data = []
        file_bytes = uploaded_file.read()  # ✅ Lecture unique
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            total_pages = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                status_text.text(f"📄 Analyse page {i+1}/{total_pages}...")
                
                # 1. Tentative extraction tableau
                table = page.extract_table()
                if table and len(table) > 1:  # Au moins header + 1 ligne
                    for ligne in table[1:]:  # Skip header
                        clean = [c for c in ligne if c and str(c).strip()]
                        res = formater_ligne_notaire(clean)
                        if res:
                            all_data.append(res)
                else:
                    # 2. Fallback OCR
                    img = np.array(page.to_image(resolution=200).original)  # 200 DPI suffit
                    result_ocr = reader.readtext(img, detail=1)
                    lignes = regrouper_par_ligne(result_ocr)
                    
                    for l in lignes:
                        res = formater_ligne_notaire(l)
                        if res:
                            all_data.append(res)
                
                progress_bar.progress((i + 1) / total_pages)
        
        status_text.text("✅ Traitement terminé !")
        
        # Construction DataFrame
        df = pd.DataFrame(all_data, columns=["Date", "Piece", "Compte", "Libelle", "Debit", "Credit"])
        df = df[(df['Date'].str.strip() != "") | (df['Libelle'].str.strip() != "")]
        
        # Nettoyage montants
        df['Debit'] = df['Debit'].apply(nettoyer_montant)
        df['Credit'] = df['Credit'].apply(nettoyer_montant)
        
        st.subheader(f"📊 {len(df)} lignes extraites")
        st.dataframe(df, use_container_width=True)
        
        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ecritures')
        
        st.download_button(
            label="📥 Télécharger Excel",
            data=output.getvalue(),
            file_name="import_compta.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"❌ Erreur : {str(e)}")
        st.exception(e)
