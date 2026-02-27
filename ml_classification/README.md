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
