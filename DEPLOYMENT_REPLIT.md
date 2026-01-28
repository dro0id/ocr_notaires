# 🚀 Guide de déploiement Replit - 5 minutes chrono

## Méthode 1 : Depuis GitHub (RECOMMANDÉ)

### Étape 1 : Pousser sur GitHub

```bash
# Initialiser le dépôt Git
git init

# Ajouter tous les fichiers
git add .

# Créer le premier commit
git commit -m "Initial commit - OCR Notaires"

# Renommer la branche en main
git branch -M main

# Ajouter l'origine GitHub (remplacez USERNAME)
git remote add origin https://github.com/USERNAME/ocr-notaires.git

# Pousser le code
git push -u origin main
```

### Étape 2 : Importer sur Replit

1. Allez sur https://replit.com
2. Cliquez sur **"Create Repl"**
3. Sélectionnez **"Import from GitHub"**
4. Collez l'URL : `https://github.com/USERNAME/ocr-notaires`
5. Cliquez sur **"Import from GitHub"**
6. Attendez que Replit détecte automatiquement :
   - Le fichier `.replit`
   - Les dépendances dans `requirements.txt`
   - L'environnement Python

### Étape 3 : Lancer l'application

1. Cliquez sur le bouton **"Run"** (grand bouton vert en haut)
2. Replit va :
   - Installer toutes les dépendances (~30-60 secondes)
   - Lancer Streamlit automatiquement
   - Générer une URL publique

### Étape 4 : Accéder à l'application

Une fois lancée, vous verrez :
- **URL locale** : `https://ocr-notaires.USERNAME.repl.co` (dans l'interface Replit)
- **URL publique** : Cliquez sur l'icône "Open in new tab" en haut à droite

🎉 **C'est fini !** Votre application est en ligne et accessible publiquement.

---

## Méthode 2 : Création manuelle directe sur Replit

Si vous ne voulez pas utiliser GitHub :

### Étape 1 : Créer un nouveau Repl

1. Allez sur https://replit.com
2. Cliquez sur **"Create Repl"**
3. Sélectionnez **"Python"** comme template
4. Nommez le Repl : `ocr-notaires`
5. Cliquez sur **"Create Repl"**

### Étape 2 : Copier les fichiers

Créez les fichiers suivants en cliquant sur "+" à côté de "Files" :

1. **main.py** - Copiez le contenu depuis votre fichier local
2. **requirements.txt** - Copiez le contenu
3. **.replit** - Copiez le contenu
4. **replit.nix** - Copiez le contenu
5. **README.md** - Optionnel
6. **.gitignore** - Optionnel

### Étape 3 : Créer le dossier utils

1. Cliquez sur "+" à côté de "Files"
2. Sélectionnez "Folder"
3. Nommez-le `utils`
4. Dans ce dossier, créez :
   - `__init__.py` - Copiez le contenu
   - `pdf_processor.py` - Copiez le contenu

### Étape 4 : Lancer

Cliquez sur **"Run"** - Replit détectera automatiquement la configuration.

---

## 🔧 Configuration automatique Replit

Le fichier `.replit` contient déjà tout :

```toml
run = "streamlit run main.py --server.headless true --server.port 8080 --server.address 0.0.0.0"
```

Replit va automatiquement :
- ✅ Installer Python 3.10
- ✅ Installer toutes les dépendances
- ✅ Configurer le port 8080
- ✅ Générer une URL publique
- ✅ Redémarrer l'app en cas de modification

---

## 📊 Vérification du déploiement

### Checklist de réussite

- [ ] L'URL s'ouvre sans erreur
- [ ] L'interface Streamlit s'affiche
- [ ] Vous pouvez uploader un PDF
- [ ] L'extraction fonctionne
- [ ] Le téléchargement Excel fonctionne

### Si l'application ne démarre pas

**Erreur : "Module not found"**

1. Ouvrez la console Shell (en bas)
2. Tapez :
```bash
pip install -r requirements.txt --force-reinstall
```

**Erreur : "Port already in use"**

1. Arrêtez l'application (bouton Stop)
2. Relancez (bouton Run)

**Erreur : "No module named 'utils'"**

Vérifiez que la structure est correcte :
```
ocr-notaires/
├── main.py
├── requirements.txt
└── utils/
    ├── __init__.py
    └── pdf_processor.py
```

---

## 🌍 Partager votre application

### URL publique permanente

Une fois déployée, votre application aura une URL permanente :

```
https://ocr-notaires.USERNAME.repl.co
```

Vous pouvez :
- ✅ Partager cette URL avec vos collègues
- ✅ L'intégrer dans un site web
- ✅ La mettre en favori
- ✅ La protéger par mot de passe (via Replit Pro)

### Limites du plan gratuit Replit

- ⏰ L'app s'arrête après 1h d'inactivité (redémarre au prochain accès)
- 💾 500 MB de stockage
- 🔒 Pas de protection par mot de passe (nécessite Replit Pro)

### Upgrader vers Replit Pro (optionnel)

Avantages :
- ⏰ Always-on (app toujours active)
- 🔐 Mot de passe personnalisé
- 🚀 Plus de ressources (CPU/RAM)
- 📦 Plus de stockage

Prix : ~7$/mois

---

## 🎯 Utilisation quotidienne

### Modifier l'application

1. Ouvrez votre Repl
2. Modifiez les fichiers directement dans l'éditeur
3. Replit redémarre automatiquement l'application
4. Rafraîchissez l'URL pour voir les changements

### Mettre à jour depuis GitHub

Si vous avez utilisé la Méthode 1 :

1. Faites vos modifications localement
2. Poussez sur GitHub :
```bash
git add .
git commit -m "Mise à jour"
git push
```
3. Dans Replit, cliquez sur "Version Control" (icône de branche)
4. Cliquez sur "Pull" pour récupérer les changements

---

## 📈 Monitoring

### Voir les logs

1. Ouvrez votre Repl
2. Cliquez sur "Console" en bas
3. Les logs Streamlit s'affichent en temps réel

### Statistiques d'utilisation

Replit ne fournit pas de statistiques détaillées en plan gratuit.

Pour du monitoring avancé, utilisez Streamlit Cloud à la place.

---

## 🆘 Support

**Problèmes avec Replit ?**
- Documentation Replit : https://docs.replit.com
- Forum Replit : https://ask.replit.com

**Problèmes avec l'application ?**
- Ouvrez une issue sur GitHub
- Contactez ONLY COMPTA

---

## 🎉 Félicitations !

Votre application OCR Notaires est maintenant déployée et accessible publiquement sur Replit !

**URL à retenir** : `https://ocr-notaires.USERNAME.repl.co`

Temps total : **~5 minutes** ⏱️
