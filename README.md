# ⚖️ OCR Notaires - ONLY COMPTA

Application Streamlit pour convertir automatiquement les relevés PDF de notaires en fichiers Excel formatés pour l'import comptable.

## 🎯 Fonctionnalités

- ✅ **Upload de PDF** : Interface simple de glisser-déposer
- 🔍 **Extraction automatique** : Détection intelligente des tableaux
- 🤖 **OCR de secours** : Pour les PDFs scannés (optionnel)
- 📊 **Export Excel** : Fichier formaté avec colonnes ajustées
- 📄 **Export CSV** : Alternative en CSV avec séparateur point-virgule
- 🔎 **Filtres** : Par date et libellé
- 📈 **Statistiques** : Nombre de pages, lignes, méthode, temps de traitement

## 📋 Format de sortie

L'application extrait 6 colonnes :

| Colonne | Description | Exemple |
|---------|-------------|---------|
| Date | Date de l'opération | 01/01/2024 |
| Piece | Numéro de pièce | VIR001 |
| Compte | Numéro de compte | 512000 |
| Libelle | Libellé de l'opération | Virement client DUPONT |
| Debit | Montant débit | 1000.00 |
| Credit | Montant crédit | 500.00 |

## 🚀 Installation locale

### Prérequis
- Python 3.10 ou supérieur
- pip

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-username/ocr-notaires.git
cd ocr-notaires

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run main.py
```

L'application sera accessible sur `http://localhost:8501`

## 🌐 Déploiement sur Replit

### Méthode 1 : Import depuis GitHub

1. Créez un compte sur [Replit](https://replit.com)
2. Cliquez sur "Create Repl"
3. Sélectionnez "Import from GitHub"
4. Collez l'URL de votre dépôt : `https://github.com/votre-username/ocr-notaires`
5. Cliquez sur "Import from GitHub"
6. Replit va automatiquement :
   - Détecter le projet Python
   - Installer les dépendances
   - Configurer l'environnement
7. Cliquez sur "Run"
8. Votre application sera accessible via une URL publique : `https://ocr-notaires.votre-username.repl.co`

### Méthode 2 : Création directe

1. Sur Replit, cliquez sur "Create Repl"
2. Sélectionnez "Python" comme template
3. Nommez votre Repl "ocr-notaires"
4. Copiez tous les fichiers du projet dans Replit
5. Cliquez sur "Run"

## ☁️ Déploiement sur Streamlit Cloud

1. Poussez votre code sur GitHub
2. Allez sur [share.streamlit.io](https://share.streamlit.io)
3. Cliquez sur "New app"
4. Sélectionnez votre dépôt GitHub
5. Spécifiez :
   - Main file path: `main.py`
   - Python version: 3.10
6. Cliquez sur "Deploy"

L'application sera accessible via une URL type : `https://votre-app.streamlit.app`

## ⚙️ Configuration

### Paramètres disponibles dans l'interface

- **Pages maximum** : Limite le nombre de pages à traiter (par défaut : 30)
- **Résolution OCR** : 150, 200 ou 300 DPI pour l'OCR (par défaut : 200)

### Limites

- Taille maximum du fichier : **50 MB**
- Pages par défaut : **30 pages**
- Formats acceptés : **PDF uniquement**

## 🛠️ Structure du projet

```
ocr-notaires/
├── main.py                 # Application Streamlit principale
├── requirements.txt        # Dépendances Python
├── .replit                 # Configuration Replit
├── replit.nix             # Environnement Nix
├── README.md              # Documentation
├── .gitignore             # Fichiers à ignorer
└── utils/
    ├── __init__.py        # Init du package
    └── pdf_processor.py   # Logique de traitement PDF
```

## 🔧 Technologies utilisées

- **Streamlit** : Interface web
- **pdfplumber** : Extraction de tableaux PDF natifs
- **pandas** : Manipulation de données
- **openpyxl** : Export Excel
- **EasyOCR** : OCR optionnel (non inclus par défaut)

## 📝 Ajouter l'OCR (optionnel)

Si vous traitez beaucoup de PDFs scannés, ajoutez EasyOCR :

```bash
# Ajoutez à requirements.txt
easyocr==1.7.1
torch==2.1.0
torchvision==0.16.0
```

⚠️ **Attention** : EasyOCR est volumineux (~500 MB) et ralentit le déploiement.

## 🐛 Dépannage

### L'application ne démarre pas sur Replit

1. Vérifiez que le fichier `.replit` existe
2. Vérifiez que `requirements.txt` est complet
3. Redémarrez le Repl

### Erreur "Module not found"

```bash
pip install -r requirements.txt --force-reinstall
```

### Le PDF ne s'extrait pas correctement

1. Vérifiez que le PDF n'est pas protégé par mot de passe
2. Augmentez la résolution OCR dans les paramètres
3. Essayez d'activer l'OCR (voir section ci-dessus)

## 📄 Licence

MIT License - Libre d'utilisation et de modification

## 💬 Support

Pour toute question ou suggestion :
- Ouvrez une issue sur GitHub
- Contactez ONLY COMPTA

---

**Développé avec ❤️ pour ONLY COMPTA**
