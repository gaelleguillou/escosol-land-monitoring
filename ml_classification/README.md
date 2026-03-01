# Classification des PDFs d'avis de l'Autorité Environnementale

Ce package contient différentes expérimentations pour classifier les PDFs d'avis de l'AE (Autorité Environnementale) au sujet de la construction de parcs photovoltaïques.

La tâche consiste à classifier chaque PDF dans une ou plusieurs de ces catégories :

- Surfaces artificialisées
- Surfaces naturelles
- Surfaces agricoles
- Surfaces forestières

La tâche a été approché comme un problème de _multilabel classification_.

## Méthodes testées

### Fine tuning d'un modèle de language

A l'aide d'un petit jeu de données (~50 observations), essayer de fine-tuner un modèle de language. Étant donné le peu de temps et de données annotées, le problème a été transforme en classification binaire (surfaces artificialisées OU surface naturelles).

Les scripts testant cette approche sont situées dans le sous-dossier `fine_tuning` :

- `training_classification.py`: Fine-tune un modèle distilbert à l'aide de Pytorch et de Lightning.
- `training_hg.py`: Fine-tune un modèle distilbert directement avec le framework HuggingFace.
- `training_setfit.py`: Approche utilisant le frmaework [SetFit](https://github.com/huggingface/setfit) pour tester une approche en _few-shot fine-tuning_ d'un modèle Sentence Transformers.

Ces méthodes n'ayant pas permis d'obtenir de résultats satisfaisants, il a été décidé de passer par une approche _zero-shot_ à l'aide d'un LLM (voir section suivante)

### Approche zero-shot

Le sous-dossier `zero_shot` contient les scripts et modules permettant de classifier les documents sans aucune étape d’entraînement ou de fine-tuning.
Le dossier `huggingface` cotient une première expérience utilisant une pipeline HuggingFace Transformers dont les résultats ont été peu concluants.

Le dossier `lm_studio` contient les fichiers relatifs à l'utilisation de LLM de taille modeste (la plupart autour des ~3B de paramètres). Ces LLM sont appelés via [LM Studio](https://lmstudio.ai/) qui agit comme un serveur d'inférence et dont l'installation en local est nécessaire affin de pouvoir reproduire les résultats.
Voir le fichier `zero_shot/lm_studio/README.md` pour plus d'informations.

## Processing des données

Afin de pouvoir utiliser les différents scripts et modules, il est nécessaire d'utiliser le module `dataset_creation.py`. Ce module permet de prétraiter les PDFs et de créer un dataset au format Parquet prêt à être utilisé pour l'entraînement ou l'évaluation des modèles.

### Fonctionnalités principales

Le module `dataset_creation` offre les fonctionnalités suivantes :

- **Extraction de texte** : Extraction du contenu textuel depuis les fichiers PDF en utilisant PyMuPDF
- **Nettoyage du texte** : Suppression des caractères spéciaux, normalisation des espaces et des sauts de ligne
- **Création de dataset** : Génération d'un fichier Parquet contenant les textes prétraités
- **Support des labels** : Intégration optionnelle de données annotées pour créer un dataset prêt à l'entraînement

### Utilisation en ligne de commande

Le module peut être exécuté directement depuis la ligne de commande :

```bash
# Création d'un dataset sans labels (pour inférence zero-shot)
python -m ml_classification.dataset_creation /path/to/pdfs /path/to/output.parquet

# Création d'un dataset avec labels (pour entraînement/évaluation)
python -m ml_classification.dataset_creation /path/to/pdfs /path/to/output.parquet --labels_dataset /path/to/labels.csv
```

### Arguments

- `pdf_path` : Chemin vers le dossier contenant les fichiers PDF à traiter
- `output_path` : Chemin où sera enregistré le fichier Parquet de sortie
- `--labels_dataset` (optionnel) : Chemin vers un fichier CSV contenant les labels pour chaque PDF. Ce fichier doit contenir au minimum une colonne `pdf_name`.

### Format du dataset avec labels

Lorsqu'un fichier de labels est fourni, le dataset généré contient les colonnes suivantes :

- `pdf_name` : Nom du fichier PDF
- `pdf_text` : Texte extrait et nettoyé du document
- `context` : Contexte annoté (séparé par `[SEP]`)
- `contexts` : Liste des contextes nettoyés
- `contexts_locations` : Positions des contextes dans le texte (index de début et longueur)
- `land_type` : Type(s) de surface associé(s) au document
- `labels` : Liste des labels triés

### Utilisation en tant que module Python

Le module peut également être importé et utilisé directement dans du code Python :

```python
from pathlib import Path
import polars as pl
from ml_classification.dataset_creation import create_dataset

# Sans labels
create_dataset(
    pdf_dir=Path("/path/to/pdfs"),
    output_filepath=Path("/path/to/output.parquet")
)

# Avec labels
pdfs_labels_df = pl.read_csv("/path/to/labels.csv")
create_dataset(
    pdf_dir=Path("/path/to/pdfs"),
    output_filepath=Path("/path/to/output.parquet"),
    pdfs_labels_df=pdfs_labels_df
)
```

### Format du fichier CSV de labels

Le fichier CSV contenant les labels doit avoir au minimum la structure suivante :

| pdf_name     | land_type                               | context                                     |
| ------------ | --------------------------------------- | ------------------------------------------- |
| avis_001.pdf | Surfaces agricoles, Surfaces naturelles | Texte du contexte 1[SEP]Texte du contexte 2 |

- `pdf_name` : Nom exact du fichier PDF (doit correspondre aux fichiers dans le dossier)
- `land_type` : Type(s) de surface séparés par `, ` (ex: "Surfaces agricoles, Surfaces naturelles")
- `context` (optionnel) : Extraits de texte annotés séparés par `[SEP]`
