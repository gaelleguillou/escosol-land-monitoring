# AE Labeling - Application Web d'Annotation

Application web Django pour l'annotation et la gestion de documents PDF avec intégration LLM.

## Description

Cette application permet d'importer des documents au format Parquet, de les visualiser et de gérer leurs annotations via une interface web. Elle utilise :

- **Django** comme framework backend
- **PostgreSQL** comme base de données
- **Polars** pour le traitement des fichiers Parquet
- **uv** comme gestionnaire de packages Python

## Prérequis

- Docker et Docker Compose installés
- Un fichier `.env` configuré (voir section Configuration)

## Configuration

Copiez le modèle suivant dans un fichier `.env` à la racine du projet :

```env
# Django Security
DJANGO_SECRET_KEY=votre-cle-secrete-aleatoire-longue
DJANGO_DEBUG=false
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL Configuration
PG_HOST=db
PG_DBNAME=ae_labeling
PG_USER=postgres
PG_PASSWORD=votre-mot-de-passe-securise
```

> **Note** : Remplacez les valeurs par des données sécurisées en production.

## Lancement avec Docker Compose

### 1. Démarrer l'application

```bash
docker compose up --build
```

Ou pour une exécution en arrière-plan :

```bash
docker compose up -d --build
```

L'application sera accessible à l'adresse : **http://localhost:8000**

### 2. Créer un super utilisateur Django

Une fois les conteneurs démarrés, accédez au shell du conteneur web pour créer un administrateur :

```bash
# Accéder au conteneur web
docker compose exec web sh

# Créer le super user
uv run python manage.py createsuperuser
```

Suivez les instructions pour entrer :

- **Email** (peut être laissé vide)
- **Username** (nom d'utilisateur)
- **Password** (mot de passe - sera saisi deux fois)

Vous pouvez maintenant vous connecter à l'interface d'administration Django à : `http://localhost:8000/admin/`

### 3. Importer les documents Parquet

1. Placez votre fichier `.parquet` dans le dossier `./data/` du projet
2. Exécutez la commande d'import depuis le conteneur :

```bash
# Accéder au conteneur web
docker compose exec web sh

# Importer le fichier Parquet
uv run python manage.py import_llm_results_parquet /app/data/votre_fichier.parquet
```

## Structure des données attendue

Le fichier Parquet doit contenir les colonnes suivantes :

| Colonne           | Type    | Description                          |
| ----------------- | ------- | ------------------------------------ |
| `pdf_name`        | string  | Nom unique du PDF (clé primaire)     |
| `pdf_text`        | string  | Texte extrait du PDF                 |
| `pdf_text_raw`    | string  | Texte brut du PDF                    |
| `contexts`        | array   | Contextes d'annotation               |
| `explanation`     | string  | Explication de la prédiction         |
| `prediction_time` | float   | Temps de prédiction en secondes      |
| `{label}_pred`    | boolean | Prédiction pour chaque label         |
| `{label}_score`   | float   | Score de confiance pour chaque label |

Les labels supportés sont :

- `surfaces_agricoles`
- `surfaces_artificialisees`
- `surfaces_forestieres`
- `surfaces_naturelles`

## Commandes Docker utiles

```bash
# Voir les logs des conteneurs
docker compose logs -f

# Arrêter l'application
docker compose down

# Redémarrer avec nettoyage
docker compose down && docker compose up --build

# Accéder au shell du conteneur web
docker compose exec web sh

# Exécuter une commande Django spécifique
docker compose exec web uv run python manage.py migrate

# Vérifier la santé de l'application
curl http://localhost:8000/
```

## Nettoyage

Pour tout nettoyer (y compris les données de la base) :

```bash
docker compose down -v
```

> ⚠️ **Attention** : Cette commande supprime tous les volumes, y compris les données de PostgreSQL.

## Développement local

Si vous souhaitez développer localement sans Docker :

```bash
# Installer uv (si ce n'est pas déjà fait)
pip install uv

# Créer l'environnement virtuel et installer les dépendances
uv sync

# Configurer votre fichier .env

# Lancer les migrations
uv run python manage.py migrate

# Démarrer le serveur de développement
uv run python manage.py runserver
```

## Notes importantes

1. **Persistance des données** : Les fichiers Parquet doivent être placés dans `./data/` qui est monté comme volume Docker
2. **Sécurité** : Ne jamais utiliser les valeurs par défaut de `DJANGO_SECRET_KEY` en production
3. **Performance** : L'application utilise Gunicorn pour servir le contenu statique et gérer plusieurs requêtes
