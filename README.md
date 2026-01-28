# ⚖️ ONLY COMPTA - OCR Notaires

Application web de conversion de relevés PDF notaires en écritures comptables Excel.

## 🚀 Fonctionnalités

- ✅ Upload de PDF (natif ou scanné)
- ✅ Extraction automatique des données
- ✅ OCR intelligent si nécessaire
- ✅ Export Excel formaté (6 colonnes)
- ✅ Export CSV bonus
- ✅ Filtres et prévisualisation
- ✅ Interface intuitive

## 📊 Format de sortie

L'application génère un fichier Excel avec 6 colonnes :

| Date | Pièce | Compte | Libellé | Débit | Crédit |
|------|-------|--------|---------|-------|--------|

## 🛠️ Installation locale
```bash
# Cloner le repo
git clone https://github.com/votre-username/ocr-notaires.git
cd ocr-notaires

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run main.py
```

## 🌐 Déploiement

### Sur Replit

1. Importez ce repo sur Replit
2. Cliquez sur "Run"
3. L'application démarre automatiquement !

### Sur Streamlit Cloud

1. Connectez votre repo GitHub
2. Sélectionnez `main.py` comme fichier principal
3. Déployez !

## 📋 Limites

- Maximum 50 MB par fichier
- Maximum 30 pages par défaut (configurable)
- Formats supportés : PDF uniquement

## 🔧 Configuration

Les paramètres sont ajustables dans la sidebar :
- Nombre de pages max
- Qualité de l'OCR (résolution)

## 📝 Licence

© 2024 ONLY COMPTA - Tous droits réservés

## 🤝 Support

Pour toute question ou problème, ouvrez une issue sur GitHub.

---

Développé avec ❤️ et Streamlit