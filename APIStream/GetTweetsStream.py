# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 18:29:30 2020

@author: Angela

Función Lambda para cargar tweets de la API de Twitter en un delivery stream 
de Amazon Kinesis Firehose.

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
stream_name = 'stream_twtos3'  

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

    
class TweetStreamListener(tweepy.streaming.StreamListener):        
    # on success
    def on_data(self, data):
        # decode json
        tweet = json.loads(data)
        # print(tweet)
        if "text" in tweet.keys():
            payload = {'id': str(tweet['id']),
                    'username': str(tweet['user']['name']),
                    'screen_name': str(tweet['user']['screen_name']),
                    'user_location': str(tweet['user']['location']),
                    'description': str(tweet['user']['description']),
                    'protected_account': str(tweet['user']['protected']),
                    'followers_count': str(tweet['user']['followers_count']),
                    'friends_count': str(tweet['user']['friends_count']),
                    'favourites_count': str(tweet['user']['favourites_count']),
                    'statuses_count': str(tweet['user']['statuses_count']),
                    'verified': str(tweet['user']['verified']),
                    'tweet': str(tweet['text'].encode('utf8', 'replace')),
                    'entities': tweet['entities'],
                    'ts': str(tweet['created_at']),
                    'favs': str(tweet['favorite_count']),
                    'rts': str(tweet['retweet_count']),
                    'reply_count': str(tweet['reply_count']),
                    'in_reply_to_status_id': str(tweet['in_reply_to_status_id']),
                    'in_reply_to_user_id': str(tweet['in_reply_to_user_id']),
                    'in_reply_to_screen_name': str(tweet['in_reply_to_screen_name']),
                    'lang': str(tweet['lang']),
                    'geo': str(tweet['geo']),
                    'coordinates': str(tweet['coordinates']),
                    'place': str(tweet['place']),
            }, # Incluir favorite_count, retweet_count, ...
            print(payload)
            try:
                put_response = kinesis_client.put_record(
                                DeliveryStreamName=stream_name,
                                Record={
                                    'Data':json.dumps(payload)
                                })
                                
            except (AttributeError, Exception) as e:
                print (e)
                pass
        return True
        
    # on failure
    def on_error(self, status):
        print(status)


def descargatuits():
    
    runtime = 45 # Temporizador de 45 segundos
    # Objeto tweepy Listener:
    listener = TweetStreamListener()
    # Autenticación:
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    # Tweepy stream
    stream = tweepy.Stream(auth, listener)
    # Búsqueda con palabras clave
    stream.filter(track=['Joe Biden'], is_async=True)
    time.sleep(runtime) #halts the control for runtime seconds
    stream.disconnect() # Desconectar stream