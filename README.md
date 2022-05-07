# Master's Degree Final Project
## AWS based tool to analyse the spreading of misinformation on Twitter
###### Ángela González Ponce - Telecommunications Engineer

Análisis de tendencias de desinformación, Máster en Ingeniería de Telecomunicaciones. 
Herramienta basada en Amazon Web Services para monitorización de Hashtags o cuentas de usuario en Twitter.
Recuperación de tweets pasados (API search) o en tiempo real (API stream), procesamiento y almacenamiento en Amazon S3. Consultas SQL para 
la creación de tablas en Athena.

This tool allows to collect:
- Past tweets by making requests to Twitter's Search API
- Tweets from the platform in real-time by making requests to Twitter's Stream API

It consists on a modular architecture that combines the following AWS cloud services:
- AWS Lambda
- Amazon CloudWatch Events
- Amazon Kinesis Data Firehose
- Amazon S3
- Amazon Athena 
- AWS Glue

This web app prototype is designed to allow the user to:
- Create huge datasets of tweets (including metadata) matching specific criteria.
- Keep them always accesible in an S3 bucket.
- Analise them by SQL queries, creating custom-made Athena tables. Once you have a table, two options are available:
  - Export as CSV file.
  - Export to a data-mining tool to create helpful visualisation in orden to find hidden patterns (Tableau, Amazon Quicksight,...).


![diseño](https://user-images.githubusercontent.com/71433272/120185269-44899800-c212-11eb-91f9-e14dac6b49ed.png)
![diseño2](https://user-images.githubusercontent.com/71433272/120185292-4bb0a600-c212-11eb-9afc-273ad36a11d7.png)
