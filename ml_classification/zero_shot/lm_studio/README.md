# Classification Zero-Shot de Documents PDF avec LLM via LM Studio

Ce projet implémente un système de classification **zero-shot** (sans entraînement préalable) des documents PDF d'Avis de l'Autorité Environnementale à propos de la création de parcs photovoltaïques et contenant des informations sur l'occupation des sols, en utilisant des modèles de langage (LLM) via l'API LM Studio. Le système classe chaque document dans une ou plusieurs catégories de type d'occupation du sol.

## 📋 Table des Matières

- [Description](#description)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
  - [Inférence sur un seul modèle](#inférence-sur-un-seul-modèle)
  - [Comparaison de plusieurs modèles (Arena)](#comparaison-de-plusieurs-modèles-arena)
  - [Évaluation des résultats](#évaluation-des-résultats)
- [Structure des fichiers](#structure-des-fichiers)
- [Labels et Catégories](#labels-et-catégories)
- [Paramètres des modèles](#paramètres-des-modèles)
- [Exemples de commandes](#exemples-de-commandes)
- [Sorties](#sorties)

---

## Description

En utilisant l'approche **zero-shot**, les modèles LLM peuvent classer les documents sans nécessiter d'exemples d'exemples d'entraînement préalable, en se basant uniquement sur des prompts et la compréhension contextuelle du texte extrait des PDFs.

## Architecture

Le système est composé de plusieurs modules :

```
ml_classification/zero_shot/lm_studio/
├── llm_zero_shot_classification_arena.py    # Comparaison multi-modèles
├── llm_zero_shot_classification_inference.py  # Inférence sur un seul modèle
├── llm_zero_shot_evaluation.py              # Évaluation des résultats
├── evaluation.py                            # Calcul des métriques
├── config.py                                # Configuration des modèles et labels
├── lm_studio.py                             # Interface avec LM Studio API
└── prompt.md                                # Prompt système pour les LLMs
```

### Flux de travail

1. **Extraction** : Extraction du texte depuis les fichiers PDF
2. **Inférence** : Envoi du texte aux modèles LLM via LM Studio
3. **Classification** : Les modèles attribuent des scores à chaque catégorie
4. **Évaluation** : Calcul des métriques de performance (précision, rappel, F1)

## Installation

### Prérequis

- Python 3.9+
- LM Studio installé et configuré localement
- Modèles LLM téléchargés dans LM Studio

### Dépendances

```bash
uv sync
```

### Configuration de LM Studio

1. Installez [LM Studio](https://lmstudio.ai/) sur votre machine
2. Téléchargez les modèles souhaités via l'interface LM Studio

## Configuration

Le fichier `config.py` contient :

### Modèles configurés

| Modèle                                   | Context Length | Description           |
| ---------------------------------------- | -------------- | --------------------- |
| `mistralai/ministral-3-3b-instruct-2512` | 32768          | Mini Mistral 3B       |
| `nvidia/nemotron-3-nano`                 | 32768          | NVIDIA Nemotron Nano  |
| `euromoe-2.6b-a0.6b-instruct-2512`       | 32768          | EuroMoE 2.6B          |
| `bartowski/meta-llama-3.1-8b-instruct`   | 32768          | Llama 3.1 8B          |
| `liquidai_lfm2-8b-a1b`                   | 32768          | Liquid AI LFM2 8B     |
| `lucie-7b-instruct-v1.1`                 | 22000          | Lucie 7B Instruct     |
| `ministral-3-14b-instruct-2512`          | 32768          | Mini Mistral 14B      |
| `ministral-3-8b-instruct-2512`           | 32768          | Mini Mistral 8B       |
| `llama-3.2-3b-instruct`                  | 32768          | Llama 3.2 3B          |
| `liquid/lfm2.5-1.2b`                     | 32768          | Liquid AI LFM2.5 1.2B |

### Labels de classification

Le système classe les documents en **4 catégories** :

| Label original           | Clé interne                |
| ------------------------ | -------------------------- |
| Surfaces artificialisées | `surfaces_artificialisees` |
| Surfaces naturelles      | `surfaces_naturelles`      |
| Surfaces agricoles       | `surfaces_agricoles`       |
| Surfaces forestières     | `surfaces_forestieres`     |

**Note** : Un document peut appartenir à plusieurs catégories (classification multi-labels).

## Utilisation

### Création d'un fichier de PDF prétraitées

Utilisez le script `ml_classification/zero_shot/dataset_creation.py`.

### Inférence sur un seul modèle

Utilisez `llm_zero_shot_classification_inference.py` pour traiter des PDF avec un modèle spécifique :

```bash
python -m ml_classification.zero_shot.lm_studio.llm_zero_shot_classification_inference \
    /chemin/vers/pdfs \
    /chemin/vers/resultats.parquet \
    --model_id mistralai/ministral-3-3b-instruct-2512
```

L'inférence peut prendre plusieurs heures en fonction du nombre de PDF et de la taille du modèle, si jamais le processus est interrompu, un fichier parquet est créé avec les prédictions déjà réalisées et qui peut servir comme fichier pour reprendre l'inférence (avec l'option `--resume`) en réinjectant le chemin de ce fichier comme fichier de sortie.

#### Options disponibles

| Option                   | Description                                  | Valeur par défaut                        |
| ------------------------ | -------------------------------------------- | ---------------------------------------- |
| `pdfs_path`              | Dossier contenant les fichiers PDF à traiter | (requis)                                 |
| `result_output_filepath` | Chemin du fichier parquet de sortie          | (requis)                                 |
| `--model_id`             | Identifiant du modèle LLM à utiliser         | `mistralai/ministral-3-3b-instruct-2512` |
| `--resume`               | Reprendre une inférence interrompue          | `False`                                  |

### Comparaison de plusieurs modèles (Arena)

Utilisez `llm_zero_shot_classification_arena.py` pour comparer la performance de plusieurs modèles :

```bash
python -m ml_classification.zero_shot.lm_studio.llm_zero_shot_classification_arena \
    /chemin/vers/donnees.parquet \
    /chemin/vers/sortie \
    --models_ids mistralai/ministral-3-3b-instruct-2512,nvidia/nemotron-3-nano
```

#### Options disponibles

| Option                | Description                                              | Valeur par défaut |
| --------------------- | -------------------------------------------------------- | ----------------- |
| `pdf_path`            | Fichier parquet contenant les PDF prétraités avec labels | (requis)          |
| `output_dir`          | Dossier de sortie pour les résultats                     | `llm_results`     |
| `--models_ids`        | Liste des modèles à tester (séparés par virgule)         | Tous les modèles  |
| `--no-auto-threshold` | Désactiver l'ajustement automatique du seuil             | `False`           |

### Évaluation des résultats

Utilisez `llm_zero_shot_evaluation.py` pour calculer les métriques de performance :

```bash
python -m ml_classification.zero_shot.lm_studio.llm_zero_shot_evaluation \
    /chemin/vers/resultats.parquet
```

## Structure des fichiers

### Entrée (PDF preprocessing)

Le fichier parquet d'entrée doit contenir :

| Colonne     | Type         | Description                            |
| ----------- | ------------ | -------------------------------------- |
| `pdf_name`  | string       | Nom du fichier PDF                     |
| `pdf_text`  | string       | Texte extrait du document              |
| `land_type` | list[string] | Catégories réelles (pour l'évaluation) |

### Sortie (Résultats d'inférence)

Le fichier parquet de sortie contient :

| Colonne                          | Type         | Description                              |
| -------------------------------- | ------------ | ---------------------------------------- |
| `pdf_name`                       | string       | Nom du fichier PDF                       |
| `surfaces_artificialisees_score` | float        | Score prédit (0-1)                       |
| `surfaces_naturelles_score`      | float        | Score prédit (0-1)                       |
| `surfaces_agricoles_score`       | float        | Score prédit (0-1)                       |
| `surfaces_forestieres_score`     | float        | Score prédit (0-1)                       |
| `contexts`                       | list[string] | Extraits de texte justifiant la décision |
| `explanation`                    | string       | Explication textuelle du modèle          |
| `prediction_time`                | float        | Temps d'inférence en secondes            |

## Paramètres des modèles

### Schéma de réponse JSON

Les modèles sont contraints à retourner une structure JSON spécifique :

```json
{
  "scores": {
    "Surfaces artificialisées": 0.85,
    "Surfaces naturelles": 0.12,
    "Surfaces agricoles": 0.45,
    "Surfaces forestières": 0.78
  },
  "contexts": ["extrait de texte pertinent"],
  "explanation": "Explication du raisonnement"
}
```

### Paramètres d'inférence

| Paramètre               | Valeur           | Description                                           |
| ----------------------- | ---------------- | ----------------------------------------------------- |
| `temperature`           | 0.05             | Faible température pour des prédictions déterministes |
| `maxTokens`             | 3000             | Nombre maximum de tokens dans la réponse              |
| `contextOverflowPolicy` | `truncateMiddle` | Politique de gestion du débordement de contexte       |

## Exemples de commandes

### Traiter tous les modèles sur un jeu de données

```bash
python -m ml_classification.zero_shot.lm_studio.llm_zero_shot_classification_arena \
    data/preprocessed_pdfs.parquet \
    results/arena_run
```

### Tester un seul modèle spécifique

```bash
python -m ml_classification.zero_shot.lm_studio.llm_zero_shot_classification_inference \
    data/pdfs_to_classify \
    results/ministral_3b.parquet \
    --model_id mistralai/ministral-3-3b-instruct-2512
```

### Reprendre une inférence interrompue

```bash
python -m ml_classification.zero_shot.lm_studio.llm_zero_shot_classification_inference \
    data/pdfs_to_classify \
    results/incomplete_run.parquet \
    --resume
```

### Évaluer avec seuil automatique optimisé

```bash
python -m ml_classification.zero_shot.lm_studio.llm_zero_shot_evaluation \
    results/model_predictions.parquet
```

## Sorties

### Rapport de classification

L'évaluation génère un rapport contenant :

- **Précision** par classe
- **Rappel** par classe
- **F1-Score** (macro et micro)
- **Support** (nombre d'échantillons par classe)
- **Seuil optimal** utilisé pour la classification binaire
- **Temps de prédiction** (total, moyen, écart-type)

### Exemple de rapport JSON

```json
{
  "surfaces_artificialisees": {
    "precision": 0.89,
    "recall": 0.85,
    "f1-score": 0.87,
    "support": 124
  },
  "surfaces_naturelles": {
    "precision": 0.92,
    "recall": 0.88,
    "f1-score": 0.90,
    "support": 98
  },
  ...
  "threshold": 0.45,
  "prediction_time": {
    "total": 342.5,
    "avg": 1.23,
    "std": 0.45
  }
}
```

## Gestion des erreurs

### Contexte trop long

Si le texte extrait dépasse la longueur de contexte du modèle, le système réduit automatiquement le texte par moitié jusqu'à ce qu'il rentre dans les limites.

### Inférence interrompue

L'option `--resume` permet de reprendre une inférence après un crash ou une interruption en sauvegardant périodiquement les résultats traités.

## Limitations connues

1. **Performance** : L'inférence zero-shot est plus lente que des modèles entraînés spécifiquement
2. **Contexte limité** : Les documents très longs peuvent perdre des informations lors du tronquage
3. **Dépendance LM Studio** : Nécessite une installation locale de LM Studio fonctionnelle

## Contribuer

Pour ajouter un nouveau modèle :

1. Ajoutez l'entrée dans `MODELS_CONFIG` dans `config.py`
2. Téléchargez le modèle via LM Studio
3. Testez avec `llm_zero_shot_classification_arena.py` sur un jeu de données test
