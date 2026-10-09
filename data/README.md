# Data
Run `make download-data` to acquire the nine original CSVs from Olist's public Kaggle endpoint. `make load-data` validates and loads them to PostgreSQL. Raw data is excluded from Git; checksums and provenance are in docs. Database staging replaces redundant disk staging copies. Aggregated exports live in reports alongside their analytical interpretation.

Source: Olist, Brazilian E-Commerce Public Dataset, https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce . CC BY-NC-SA 4.0; noncommercial use, attribution, and share-alike obligations apply. Code licensing is separate.
