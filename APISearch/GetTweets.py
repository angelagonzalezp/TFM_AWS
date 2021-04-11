# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 18:29:30 2020

@author: Angela

Función Lambda para cargar tweets de la API de Twitter en un delivery stream 
de Amazon Kinesis Firehose -> tweets2kinesis

"""

import boto3, json, tweepy, sys, time, random
import json
from datetime import datetime
import calendar
from os import environ


# Credenciales de acceso a la API de Twitter:
consumer_key = environ['consumer_key']
consumer_secret = environ['consumer_secret']
access_token = environ['access_token']
access_token_secret = environ['access_token_secret']
# Credenciales AWS:
accessK = environ['aws_access_key_id']
secretK = environ['aws_secret_access_key']

# Nombre del delivery stream de Kinesis Firehose
stream_name = 'twtos3'  

# Conexión Kinesis:
kinesis_client = boto3.client('firehose', 
                              region_name='us-east-1',
                              endpoint_url='https://firehose.us-east-1.amazonaws.com',
                              aws_access_key_id=accessK,  
                              aws_secret_access_key=secretK)

def lambda_handler(event, context):
    
    descargatuits()
    
    return{
        'statusCode': 200,
        'body': json.dumps('Hello World')
    }

def descargatuits():
    
    # Autenticación: 
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True) # Clase API
    
    new_search = "Joe+Biden -filter:retweets" # Eliminar retweets
    resultados = api.search(q = new_search)
    for i in range(0, len(resultados)):
        resultados[i] = resultados[i]._json # Diccionario
        kinesis_client.put_record(DeliveryStreamName=stream_name,
                                Record={
                                    'Data':json.dumps(resultados[i]) # Diccionario a JSON
                                })
            