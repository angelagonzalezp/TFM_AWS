# -*- coding: utf-8 -*-
"""
Created on Fri Apr  2 15:42:17 2021

@author: Angela

Fichero con mis credenciales (variables de entorno)
"""
from os import getenv

""" CREDENCIALES AWS """
aws_access_key_id = getenv('aws_access_key_id', None)
assert aws_access_key_id

aws_secret_access_key = getenv('aws_secret_access_key', None)
assert aws_secret_access_key

""" CREDENCIALES TWITTER """
consumer_key = getenv('consumer_key', None)
assert consumer_key

consumer_secret = getenv('consumer_secret', None)
assert consumer_secret

access_token = getenv('access_token', None)
assert access_token

access_token_secret = getenv('access_token_secret', None)
assert access_token_secret