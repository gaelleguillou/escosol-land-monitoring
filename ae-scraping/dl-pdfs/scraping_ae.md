# Scraping des sites d'Autorité Environnementale

## Pipeline

Les données csv sont aussi enregistrées sur [Google Sheets](https://docs.google.com/spreadsheets/d/1HuqKUfTc3zOMR3sNk0LgQVhm-WPcfHb8_RzWmWJwb0o/edit?gid=0#gid=0).

Data : region_links_ae.csv (liste des régions et de leurs pages "avis sur projets") -->

Script : extract_links.py (extraction des liens d'avis sur projet par année et région) -->

Data : ae_year_links.csv (liste des pages d'avis sur projets par année et région) -->

Script :

## Stratégie

### Site-wide research

Il existe une recherche site-wide qui nous permettrait de tout faire en une query.
https://www.mrae.developpement-durable.gouv.fr/?typedoc=pdf&recherche=photovolta%C3%AFque&page=recherche&perimetre=all
Le risque est que ça nous permet pas de filtrer les "avis sur projets" précis et qu'on perd potentiellement de la metadonnée (année, région, etc) facilement accessible sur les autres URLs.

### Crawling + scraping (solution choisie)

A partir de la base d'url qui nous a été données, on peut crawl les projets par année et mois (ce qui nous donne déjà de la donnée formatée) en récupérant seulement les PDFs qui indiquent "photovoltaïque" ou "photovoltaique" dans la description.

Les pages avis rendus sur projet ont toujours le même format : un lien par année (dont un pour archives).

Etapes :

1 - Récupérer les URLs uniques par année

2 - Scraper les pages avis / année en filtrant sur photovoltaïque dans la description
