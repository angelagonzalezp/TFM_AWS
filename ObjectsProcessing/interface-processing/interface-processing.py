# -*- coding: utf-8 -*-
"""
Created on Thu Apr  1 15:59:49 2021

@author: Angela

Función Lambda para procesar las consultas realizadas desde la interfaz web.
Adapta las queries al formato necesario para realizar consultas SQL desde Athena.

"""

from os import environ
import boto3, io, re
from flatten_json import flatten
import json

ACCESS_KEY = environ['ACCESS_KEY']
SECRET_KEY = environ['SECRET_KEY']

bucketname = 'consultas-interfaz'       # Trigger bucket (la función Lambda se dispara con un evento PUT en bucketname)
destbucket = 'interface-processed'    # Destino de los objetos procesados

s3 = boto3.resource('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)


def lambda_handler(event, context):
    
    # Listar TODOS los objetos del bucket
    objs = client.list_objects(Bucket='consultas-interfaz')['Contents']
    # Ordenar por RECIENTES
    objs.sort(key=lambda item:item['LastModified'], reverse=True)
    ultimo = objs[0]                    # Último objeto cargado en el bucket

    # Descargar objeto para editarlo:
    bytes_buffer = io.BytesIO()
    client.download_fileobj(Bucket='consultas-interfaz', Key=ultimo['Key'], Fileobj=bytes_buffer)
    byte_value = bytes_buffer.getvalue()
    str_value = byte_value.decode()

    if(str_value[0] == '['):                            # CASO STREAM (contenidos en []])
        # Reemplazar substrings y eliminar corchetes:
        str_modif = str_value.replace('][', '\n')
        str_modif = str_modif[1:-1]
    else:                                               # CASO SEARCH
        # Reemplazar substring }{ -> Cada tweet en una nueva línea
        repStr = re.sub("}{", "} \n{", str_value)
        separados = re.split('\n', repStr)
        str_modif = ""
        for i in range(0, len(separados)):
            d = json.loads(separados[i])
            d = flatten(d)
            str_modif = str_modif + json.dumps(d) + "\n"

    # Crear objeto con el string de caracteres modificado
    processed = s3.Object(destbucket, ultimo['Key'])    # Replicar el prefijo del cubo origen
    processed.put(Body=str_modif.encode('ascii'))