import streamlit as st
import pdfplumber
import pandas as pd
import easyocr
import numpy as np
import io
import os

# Configuration Sécurité & Interface
st.set_page_config(page_title="ONLY COMPTA - OCR_notaires", layout="wide")
st.title("⚖️ ONLY COMPTA - Extracteur Comptable Notaire")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['fr'])

reader = load_ocr()

def formater_ligne(mots):
    row = [""] * 6
    if not mots or len(mots) < 2: return None
    row[0] = str(mots[0]).strip() # Date
    if len(mots) >= 3:
        row[5] = str(mots[-1]).strip() # Credit
        row[4] = str(mots[-2]).strip() # Debit
        row[3] = " ".join([str(m) for m in mots[1:-2]]).strip() # Libelle
    else:
        row[3] = " ".join([str(m) for m in mots[1:]]).strip()
    return row

uploaded_file = st.file_uploader("Charger le PDF scanné", type="pdf")

if uploaded_file:
    with st.spinner("Analyse en cours..."):
        all_data = []
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                # Utilisation de l'OCR pour la fidélité sur scan
                img = np.array(page.to_image(resolution=300).original)
                # detail=0 pour une lecture par ligne simplifiée
                result = reader.readtext(img, detail=0)
                
                # On traite chaque ligne détectée
                for line in result:
                    mots = line.split()
                    res = formater_ligne(mots)
                    if res: all_data.append(res)

        df = pd.DataFrame(all_data, columns=["Date", "Piece", "Compte", "Libelle", "Debit", "Credit"])
        st.success("Analyse terminée !")
        st.dataframe(df)

        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button("📥 Télécharger l'Excel", output.getvalue(), "releve_compta.xlsx")
