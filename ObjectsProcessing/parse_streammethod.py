# -*- coding: utf-8 -*-
"""
Created on Sat Jan 23 17:16:00 2021

@author: Angela

Función Lambda invocada por la carga de un objeto en el bucket twitterdemotfm.
Accede a la ruta del nuevo objeto, lo edita y lo sube al bucket twitterdemoparsed
para evitar invocaciones recurrentes.

"""

from os import environ
from datetime import datetime, timedelta
import boto3, io, re
from pytz import timezone 

ACCESS_KEY = environ['ACCESS_KEY']
SECRET_KEY = environ['SECRET_KEY']

bucketname = 'streammethod'
destbucket = 'streammethodparsed'

s3 = boto3.resource('s3')
client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY)

def getprefix():
    
    cet = timezone('Europe/Madrid')
    dateTimeObj = datetime.now(cet)
    datestring = datetime.strftime(dateTimeObj, '%c %p')
    AMPM = datestring[-2] # AMPM = A si es AM, AMPM = P si es PM

    pathdate = dateTimeObj-timedelta(hours=1) # El objeto de las 5 se sube a las 6:46 hora CET, el de las 7 a las 8:46 hora CET,...
    if(len(str(pathdate.month))==1):
        mes = '0'+str(pathdate.month)
    else:
        mes = str(pathdate.month)
    if(len(str(pathdate.day))==1):
        dia = '0'+str(pathdate.day)
    else:
        dia = str(pathdate.day)
    if(dateTimeObj.hour==0):
        hora = '23'
    elif(len(str(pathdate.hour))==1): 
        hora = '0'+str(pathdate.hour)
    else:
        hora = str(pathdate.hour)
        
    path = str(dateTimeObj.year)+'/'+mes+'/'+dia+'/'+hora+'/'
    
    return path


def lambda_handler(event, context):
    
    ruta = getprefix()
    # Sólo hay un fichero por carpeta del bucket:
    file = client.list_objects(Bucket=bucketname, Prefix=ruta).get('Contents', [])[0]['Key']
    # Descargar objeto para editarlo:
    bytes_buffer = io.BytesIO()
    client.download_fileobj(Bucket=bucketname, Key=file, Fileobj=bytes_buffer)
    byte_value = bytes_buffer.getvalue()
    str_value = byte_value.decode()
    # Reemplazar substrings y eliminar corchetes:
    str_modif = str_value.replace('][', '\n')
    str_modif = str_modif[1:-1]
    # Sobreescribir objeto en el bucket
    newobj = s3.Object(destbucket, file)
    newobj.put(Body=str_modif.encode('ascii'))
    
    return{
        'statusCode': 200,
    }
    
