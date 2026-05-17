# ML Project for "Artificial Intelligence Technologies" course at Uni

This project aims to collect recipe URLs from [foodnetwork.co.uk](https://foodnetwork.co.uk) website, parse each one of them, create and prepsrocess dataset and finally - train and test ML model to predict expected cooking time of each dish.

The design document containing all the artifatcs required by the project rules (artifacts_doc.md) is included in the repo (it's written in russian because ain't no way i'm translating all that text from presentation into english by myself). EDA as well as all the intermediate commentary regarding the possible question of "what's even going on there" is inclued in the code (see EDA in "main_train.py file").

### Important note!
This repo contains only executable files (.py files), list of URLs to be parsed (foodnetwork_uk_urls.txt), raw dataset (df_parsed_recipes.csv), ready-to-use dataset (df_ready.csv) and some pics (.png files) with plots. If you wish to run full pipeline (collecting URLs -> parsing each website page -> preprocessing data -> training and testing the model), please, use terminal and run files in the following order: 
1. main.py
2. main_preprocess.py
3. main_train.py

Note that running full pipeline will generate >2000 rows and may take more than an hour to complete!

If you wish to only train and test ML model and output prediction metrics without parsing, please, consider running ONLY main_train.py file. Make sure that df_ready.csv is available at the same directory as main_train.py.
