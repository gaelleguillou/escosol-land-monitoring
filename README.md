# Escosol Land Monitoring
Objectif : Développer une cartographie pour connaitre les consommations d’espaces naturels agricoles et forestier (ENAF) et artificialisés par le photovoltaïque.  

# Setup

## Package manager

We use uv as the package and project manager for its speed. If you need to install it, refer to their [installation guide](https://docs.astral.sh/uv/getting-started/installation/).

To run scripts : `uv run example.py`

To add packages : `uv add examplepackage`

## Pre-commit

We use [pre-commit](https://pre-commit.com/#install) to ensure code quality.

# Data Sources

## IGN

[à compléter]

## Autorités Environnementales Régionales

On récupère les avis sur projets en PDF de chaque région. Pour cela, on a recours à du scraping.

Les méthodes utilisées sont détaillées dans `ae-scraping/README_scraping.md`.
