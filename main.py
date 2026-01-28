"""
ONLY COMPTA - OCR Notaires
Convertisseur de relevés PDF notaires en écritures comptables Excel
"""

import streamlit as st
import pandas as pd
import io
from utils.pdf_processor import PDFProcessor

# Configuration
st.set_page_config(
    page_title="ONLY COMPTA - OCR Notaires",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stAlert {
        background-color: #f0f2f6;
    }
    .upload-text {
        text-align: center;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">⚖️ ONLY COMPTA - OCR Notaires</h1>', unsafe_allow_html=True)
st.markdown('<p class="upload-text">Transformez vos relevés PDF en écritures comptables Excel</p>', unsafe_allow_html=True)

# Sidebar - Informations
with st.sidebar:
    st.header("ℹ️ Informations")
    st.info("""
    **Limites :**
    - Fichiers jusqu'à 50 MB
    - Maximum 30 pages
    - Formats : PDF natif ou scanné
    
    **Format de sortie :**
    6 colonnes Excel :
    - Date
    - Pièce
    - Compte
    - Libellé
    - Débit
    - Crédit
    """)
    
    st.header("🔧 Paramètres")
    max_pages = st.slider("Pages max à traiter", 5, 50, 30)
    resolution_ocr = st.select_slider("Qualité OCR", options=[100, 150, 200, 300], value=150)
    
    st.divider()
    st.caption("Version 1.0.0 - ONLY COMPTA")

# Zone d'upload
uploaded_file = st.file_uploader(
    "📄 Déposez votre relevé PDF ici",
    type=["pdf"],
    help="Fichier PDF de relevé notaire (max 50 MB)"
)

# Traitement
if uploaded_file is not None:
    # Vérification taille
    file_size_mb = uploaded_file.size / (1024 * 1024)
    
    if file_size_mb > 50:
        st.error(f"❌ Fichier trop volumineux : {file_size_mb:.1f} MB (maximum 50 MB)")
        st.stop()
    
    # Affichage infos fichier
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Fichier", uploaded_file.name)
    with col2:
        st.metric("💾 Taille", f"{file_size_mb:.2f} MB")
    with col3:
        st.metric("📅 Type", "PDF")
    
    st.divider()
    
    # Traitement du PDF
    try:
        processor = PDFProcessor(max_pages=max_pages, ocr_resolution=resolution_ocr)
        
        # Lecture du fichier
        file_bytes = uploaded_file.read()
        
        # Traitement avec barre de progression
        with st.spinner('🔄 Analyse du document en cours...'):
            df, stats = processor.process_pdf(file_bytes)
        
        # Affichage des statistiques
        st.success("✅ Traitement terminé avec succès !")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📄 Pages traitées", stats['pages_processed'])
        with col2:
            st.metric("📊 Lignes extraites", stats['lines_extracted'])
        with col3:
            st.metric("🔍 Méthode", stats['method'])
        with col4:
            st.metric("⏱️ Temps", f"{stats['processing_time']:.1f}s")
        
        st.divider()
        
        # Prévisualisation des données
        st.subheader("📊 Aperçu des données extraites")
        
        # Filtres
        col1, col2 = st.columns(2)
        with col1:
            filter_date = st.text_input("🔍 Filtrer par date", placeholder="Ex: 01/01/2024")
        with col2:
            filter_libelle = st.text_input("🔍 Filtrer par libellé", placeholder="Ex: honoraires")
        
        # Application des filtres
        df_filtered = df.copy()
        if filter_date:
            df_filtered = df_filtered[df_filtered['Date'].str.contains(filter_date, na=False)]
        if filter_libelle:
            df_filtered = df_filtered[df_filtered['Libelle'].str.contains(filter_libelle, case=False, na=False)]
        
        # Affichage tableau
        st.dataframe(
            df_filtered,
            use_container_width=True,
            height=400,
            column_config={
                "Date": st.column_config.TextColumn("Date", width="small"),
                "Piece": st.column_config.TextColumn("Pièce", width="small"),
                "Compte": st.column_config.TextColumn("Compte", width="small"),
                "Libelle": st.column_config.TextColumn("Libellé", width="large"),
                "Debit": st.column_config.NumberColumn("Débit", format="%.2f €"),
                "Credit": st.column_config.NumberColumn("Crédit", format="%.2f €"),
            }
        )
        
        # Statistiques tableau
        st.caption(f"Affichage de {len(df_filtered)} ligne(s) sur {len(df)} au total")
        
        st.divider()
        
        # Export Excel
        st.subheader("📥 Téléchargement")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ecritures')
            
            # Formatage Excel
            workbook = writer.book
            worksheet = writer.sheets['Ecritures']
            
            # Largeur des colonnes
            worksheet.column_dimensions['A'].width = 12  # Date
            worksheet.column_dimensions['B'].width = 10  # Pièce
            worksheet.column_dimensions['C'].width = 10  # Compte
            worksheet.column_dimensions['D'].width = 50  # Libellé
            worksheet.column_dimensions['E'].width = 12  # Débit
            worksheet.column_dimensions['F'].width = 12  # Crédit
        
        output.seek(0)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.download_button(
                label="📥 Télécharger le fichier Excel",
                data=output.getvalue(),
                file_name=f"import_compta_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
        with col2:
            # Bouton export CSV (bonus)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📄 Export CSV",
                data=csv,
                file_name=f"import_compta_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
    except Exception as e:
        st.error(f"❌ Erreur lors du traitement : {str(e)}")
        with st.expander("🔍 Détails de l'erreur"):
            st.exception(e)
            st.info("""
            **Suggestions :**
            - Vérifiez que le PDF n'est pas protégé par mot de passe
            - Assurez-vous que le PDF contient du texte (pas seulement des images)
            - Essayez de réduire la taille du fichier
            - Contactez le support si l'erreur persiste
            """)

else:
    # Message d'accueil
    st.info("👆 **Commencez par uploader un fichier PDF de relevé notaire**")
    
    # Instructions d'utilisation
    with st.expander("📖 Mode d'emploi"):
        st.markdown("""
        ### Comment utiliser cet outil ?
        
        1. **Upload** : Cliquez sur "Browse files" et sélectionnez votre PDF
        2. **Traitement** : L'application analyse automatiquement le document
        3. **Vérification** : Consultez l'aperçu des données extraites
        4. **Export** : Téléchargez le fichier Excel généré
        
        ### Format attendu
        
        Le PDF doit contenir un tableau avec :
        - Une colonne **Date**
        - Un **Libellé** de l'opération
        - Des colonnes **Débit** et **Crédit**
        
        ### Formats supportés
        
        - ✅ PDF avec tableaux natifs (meilleure qualité)
        - ✅ PDF scannés (via OCR automatique)
        - ❌ PDF protégés par mot de passe
        """)
    
    # Exemple visuel
    with st.expander("👁️ Exemple de résultat"):
        exemple_data = {
            "Date": ["01/01/2024", "02/01/2024", "03/01/2024"],
            "Piece": ["001", "002", "003"],
            "Compte": ["512000", "512000", "401000"],
            "Libelle": ["Honoraires notaire", "Frais de dossier", "Taxe foncière"],
            "Debit": ["1500.00", "250.00", ""],
            "Credit": ["", "", "850.00"]
        }
        st.dataframe(pd.DataFrame(exemple_data), use_container_width=True)

# Footer
st.divider()
st.caption("© 2024 ONLY COMPTA - Tous droits réservés | Développé avec ❤️ et Streamlit")