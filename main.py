import streamlit as st
import pandas as pd
from datetime import datetime
import io
from utils.pdf_processor import PDFProcessor

st.set_page_config(
    page_title="OCR Notaires - ONLY COMPTA",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f4788; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #666; text-align: center; margin-bottom: 2rem; }
    .metric-container { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
    .success-box { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
    .warning-box { background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
    .error-box { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
    .llm-box { background-color: #e8f4fd; border: 1px solid #bee5eb; color: #0c5460; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
    .footer { text-align: center; color: #888; padding: 2rem 0 1rem 0; margin-top: 3rem; border-top: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⚖️ ONLY COMPTA - OCR Notaires</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Convertissez vos relevés PDF en écritures comptables Excel</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("ℹ️ Informations")
    st.info("""
    **Format de sortie :**
    - Date
    - Piece
    - Compte
    - Libellé
    - Débit
    - Crédit

    **Limites :**
    - Taille max : 50 MB
    - Pages par défaut : 30
    - Format : PDF uniquement
    """)

    st.header("⚙️ Paramètres")
    max_pages = st.number_input(
        "Pages maximum à traiter",
        min_value=1, max_value=100, value=30,
        help="Limite le nombre de pages pour accélérer le traitement"
    )
    ocr_resolution = st.selectbox(
        "Résolution OCR (si nécessaire)",
        options=[150, 200, 300], index=1,
        help="Plus élevé = meilleure qualité mais plus lent"
    )

    st.header("🤖 Agent IA")
    st.markdown("""
    L'agent IA (Gemini) identifie automatiquement les colonnes de chaque relevé,
    même si leur ordre ou leur nom varie d'un notaire à l'autre.

    **Sans clé** : extraction classique (colonnes fixes)
    **Avec clé** : extraction intelligente (colonnes adaptatives)

    Obtenez une clé gratuite sur [Google AI Studio](https://aistudio.google.com/app/apikey).
    """)

    gemini_key = st.text_input(
        "Clé API Gemini (optionnel)",
        type="password",
        placeholder="AIza...",
        help="Laissez vide pour utiliser l'extraction classique"
    )

    # Priorité : champ sidebar > secrets Replit
    try:
        api_key = gemini_key.strip() if gemini_key.strip() else st.secrets.get("GEMINI_API_KEY", None)
    except Exception:
        api_key = gemini_key.strip() or None

uploaded_file = st.file_uploader(
    "📄 Sélectionnez votre relevé PDF",
    type=["pdf"],
    help="Glissez-déposez votre fichier ou cliquez pour parcourir"
)

if uploaded_file is not None:
    file_size = len(uploaded_file.getvalue()) / (1024 * 1024)

    if file_size > 50:
        st.markdown(f"""
            <div class="error-box">
                <strong>⚠️ Fichier trop volumineux</strong><br>
                Taille actuelle: {file_size:.1f} MB — Limite: 50 MB
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="success-box">
                <strong>✅ Fichier chargé</strong><br>
                Nom: {uploaded_file.name} — Taille: {file_size:.2f} MB
            </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Lancer l'extraction", type="primary", use_container_width=True):
            with st.spinner("🔄 Traitement en cours..."):
                try:
                    processor = PDFProcessor(
                        max_pages=max_pages,
                        ocr_resolution=ocr_resolution,
                        api_key=api_key
                    )

                    df, stats = processor.process_pdf(uploaded_file)

                    # Afficher infos LLM si utilisé
                    if stats.get('llm_used'):
                        colonnes = stats.get('colonnes_detectees', {})
                        st.markdown(f"""
                            <div class="llm-box">
                                <strong>🤖 Agent IA activé</strong><br>
                                Colonnes détectées automatiquement :
                                date → col {colonnes.get('date', '?')} |
                                libellé → col {colonnes.get('libelle', '?')} |
                                débit → col {colonnes.get('debit', '?')} |
                                crédit → col {colonnes.get('credit', '?')}
                            </div>
                        """, unsafe_allow_html=True)
                    elif api_key and stats.get('llm_error'):
                        st.markdown(f"""
                            <div class="warning-box">
                                <strong>⚠️ Agent IA non utilisé</strong><br>
                                {stats['llm_error']}
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("### 📊 Résultats")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Pages traitées", stats['pages_processed'])
                    with col2:
                        st.metric("Lignes extraites", stats['lines_extracted'])
                    with col3:
                        st.metric("Méthode", stats['method'])
                    with col4:
                        st.metric("Temps", f"{stats['processing_time']:.1f}s")

                    if len(df) > 0:
                        st.markdown("### 👁️ Aperçu des données")

                        col_filter1, col_filter2 = st.columns(2)
                        with col_filter1:
                            filter_date = st.text_input("🔍 Filtrer par date", placeholder="Ex: 01/01/2024")
                        with col_filter2:
                            filter_libelle = st.text_input("🔍 Filtrer par libellé", placeholder="Ex: virement")

                        df_filtered = df.copy()
                        if filter_date:
                            df_filtered = df_filtered[df_filtered['Date'].str.contains(filter_date, na=False, case=False)]
                        if filter_libelle:
                            df_filtered = df_filtered[df_filtered['Libelle'].str.contains(filter_libelle, na=False, case=False)]

                        st.dataframe(
                            df_filtered,
                            use_container_width=True,
                            column_config={
                                "Date": st.column_config.TextColumn("Date", width="small"),
                                "Piece": st.column_config.TextColumn("Pièce", width="small"),
                                "Compte": st.column_config.TextColumn("Compte", width="small"),
                                "Libelle": st.column_config.TextColumn("Libellé", width="large"),
                                "Debit": st.column_config.NumberColumn("Débit", format="%.2f"),
                                "Credit": st.column_config.NumberColumn("Crédit", format="%.2f")
                            }
                        )

                        st.info(f"📌 Affichage de {len(df_filtered)} lignes sur {len(df)} au total")

                        st.markdown("### 📥 Téléchargement")

                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Ecritures')
                            worksheet = writer.sheets['Ecritures']
                            worksheet.column_dimensions['A'].width = 12
                            worksheet.column_dimensions['B'].width = 12
                            worksheet.column_dimensions['C'].width = 12
                            worksheet.column_dimensions['D'].width = 50
                            worksheet.column_dimensions['E'].width = 15
                            worksheet.column_dimensions['F'].width = 15
                        output.seek(0)

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.download_button(
                                label="📊 Télécharger Excel",
                                data=output.getvalue(),
                                file_name=f"import_compta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        with col_dl2:
                            csv_data = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
                            st.download_button(
                                label="📄 Télécharger CSV",
                                data=csv_data,
                                file_name=f"import_compta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.markdown("""
                            <div class="warning-box">
                                <strong>⚠️ Aucune donnée extraite</strong><br>
                                Le PDF ne semble pas contenir de tableau structuré.<br>
                                Essayez d'augmenter la résolution OCR dans les paramètres.
                            </div>
                        """, unsafe_allow_html=True)

                except Exception as e:
                    st.markdown(f"""
                        <div class="error-box">
                            <strong>❌ Erreur lors du traitement</strong><br>
                            {str(e)}
                        </div>
                    """, unsafe_allow_html=True)
                    with st.expander("🔍 Détails de l'erreur"):
                        st.code(str(e), language="text")

else:
    st.markdown("### 🎯 Comment ça marche ?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**1️⃣ Chargement**\n- Glissez votre PDF\n- Max 50 MB\n- Format PDF uniquement")
    with col2:
        st.markdown("**2️⃣ Extraction**\n- Détection automatique\n- Agent IA si clé fournie\n- Formatage intelligent")
    with col3:
        st.markdown("**3️⃣ Export**\n- Téléchargement Excel\n- Option CSV disponible\n- Prêt pour import compta")

    st.markdown("---")
    st.markdown("### 📋 Exemple de résultat")
    exemple_data = {
        'Date': ['01/01/2024', '02/01/2024', '03/01/2024'],
        'Piece': ['VIR001', 'CHQ002', 'VIR003'],
        'Compte': ['512000', '401000', '445660'],
        'Libelle': ['Virement client DUPONT', 'Cheque fournisseur MARTIN', 'TVA deductible'],
        'Debit': [1000.00, 0.00, 200.00],
        'Credit': [0.00, 500.00, 0.00]
    }
    st.dataframe(pd.DataFrame(exemple_data), use_container_width=True)

st.markdown("""
    <div class="footer">
        ⚖️ <strong>ONLY COMPTA</strong> - OCR Notaires<br>
        Solution d'extraction automatique de relevés comptables
    </div>
""", unsafe_allow_html=True)
