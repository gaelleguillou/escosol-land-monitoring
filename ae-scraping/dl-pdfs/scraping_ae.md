# Scraping des sites d'Autorité Environnementale

## Pipeline

J'ai séparé au max les étapes pour éviter de se faire reconnaître comme un robot par les sites du gouvernement.
Les scripts n'ont a priori pas à être relancés, ils sont là pour archivage.

Les données csv sont aussi enregistrées sur [Google Sheets](https://docs.google.com/spreadsheets/d/1HuqKUfTc3zOMR3sNk0LgQVhm-WPcfHb8_RzWmWJwb0o/edit?gid=0#gid=0).

Data : region_links_ae.csv (18 rows) (liste des régions et de leurs pages "avis sur projets") -->

Script : extract_year_links.py (extraction des liens d'avis sur projet par année et région) -->

Data : ae_year_links.csv (143 rows) (liste des pages d'avis sur projets par année et région) -->

Script : extract_relevant_pdf_links.py -->

Data : metadata_pdfs.csv (1945 rows) (liste des liens de PDF + leurs descriptions qui sont concernés par le *voltaïque)

NB : quelques liens n'ont donné aucun résultat. Ils sont stockés sur google sheet sous la feuille url_wo_relevant_pdfs.

Pour plusieurs raisons : certains sont ceux de 2026, donc n'ont pas d'avis publiés, d'autres n'ont pas d'avis pertinents, ou encore renvoient à un autre lien.

## Stratégie

### Site-wide research

Il existe une recherche site-wide qui nous permettrait de tout faire en une query de ce type :

https://www.mrae.developpement-durable.gouv.fr/?typedoc=pdf&recherche=photovolta%C3%AFque&page=recherche&perimetre=all

Le risque est que ça nous permet pas de filtrer les "avis sur projets" précis et qu'on perd potentiellement de la metadonnée (année, région, etc) facilement accessible sur les autres URLs.

### Crawling + scraping (solution choisie)

A partir de la base d'url qui nous a été données, on peut crawl les projets par année et mois (ce qui nous donne déjà de la donnée formatée) en récupérant seulement les PDFs qui indiquent "photovoltaïque" ou "photovoltaique" dans la description.

Les pages avis rendus sur projet ont toujours le même format : un lien par année (dont un pour archives).

Etapes :

1 - Récupérer les URLs uniques par année

2 - Récupérer les URLs des PDFs pertinents (avec voltaïque dans la description)

Ici, je garde la description et le titre qui nous permettront de récupérer facilement des métadonnées (date de l'avis, type de projet etc) plus tard

3 - Télécharger les PDFs pertinents (env. 2000)
