import streamlit as st
import pdfplumber
import pandas as pd
import easyocr
import numpy as np
import io
import re

# Configuration de la page
st.set_page_config(page_title="Extracteur Notaire Pro", layout="wide")

st.title("⚖️ Convertisseur Relevé de Notaire")
st.write("Transformez vos scans PDF en écritures comptables (6 colonnes).")

# Initialisation de l'OCR (mise en cache pour la rapidité)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr'])

reader = load_ocr()

def formater_ligne_notaire(liste_mots):
    row = [""] * 6
    if not liste_mots or len(liste_mots) < 2: return None
    row[0] = str(liste_mots[0]).strip()
    if len(liste_mots) >= 3:
        row[5] = str(liste_mots[-1]).strip() # Crédit
        row[4] = str(liste_mots[-2]).strip() # Débit
        row[3] = " ".join([str(m) for m in liste_mots[1:-2]]).strip() # Libellé
    else:
        row[3] = " ".join([str(m) for m in liste_mots[1:]]).strip()
    return row

def regrouper_par_ligne(ocr_results, seuil_y=15):
    lignes = []
    if not ocr_results: return lignes
    ocr_results.sort(key=lambda x: x[0][0][1])
    ligne_actuelle = []
    y_ref = ocr_results[0][0][0][1]
    for (bbox, texte, prob) in ocr_results:
        y_haut = bbox[0][1]
        if abs(y_haut - y_ref) <= seuil_y:
            ligne_actuelle.append((bbox[0][0], texte))
        else:
            ligne_actuelle.sort(key=lambda x: x[0])
            lignes.append([t for x, t in ligne_actuelle])
            ligne_actuelle = [(bbox[0][0], texte)]
            y_ref = y_haut
    if ligne_actuelle:
        ligne_actuelle.sort(key=lambda x: x[0])
        lignes.append([t for x, t in ligne_actuelle])
    return lignes

# --- INTERFACE UTILISATEUR ---
uploaded_file = st.file_uploader("Déposez votre PDF ici", type="pdf")

if uploaded_file is not None:
    all_data = []
    progress_bar = st.progress(0)
    
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            st.write(f"Analyse de la page {i+1}...")
            
            # Strategie Hybride
            table = page.extract_table()
            if table:
                for ligne in table:
                    clean = [c for c in ligne if c is not None and str(c).strip() != ""]
                    res = formater_ligne_notaire(clean)
                    if res: all_data.append(res)
            else:
                img = np.array(page.to_image(resolution=300).original)
                result_ocr = reader.readtext(img, detail=1)
                lignes = regrouper_par_ligne(result_ocr)
                for l in lignes:
                    res = formater_ligne_notaire(l)
                    if res: all_data.append(res)
            
            progress_bar.progress((i + 1) / total_pages)

    # Affichage des résultats
    df = pd.DataFrame(all_data, columns=["Date", "Piece", "Compte", "Libelle", "Debit", "Credit"])
    df = df[(df['Date'] != "") | (df['Libelle'] != "")]
    
    st.subheader("📊 Aperçu des données")
    st.dataframe(df, use_container_width=True)

    # Bouton de téléchargement
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Télécharger le fichier Excel",
        data=output.getvalue(),
        file_name="import_compta.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
