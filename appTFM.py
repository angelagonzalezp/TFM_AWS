# -*- coding: utf-8 -*-
"""
Created on Wed Mar 17 16:23:06 2021

@author: Angela

Interfaz web para consultas a Twitter

"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import datetime
from pytz import timezone 
import sys, json, secrets, boto3, zipfile
import os.path
import tweepy as tw
import shutil, locale, random, config, io, csv
import pandas as pd

sys.path.append('\Python\Python37\Lib\site-packages')

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)

""" AWS SESSIONS """
c = boto3.client('lambda', region_name='us-east-1',
                  aws_access_key_id=config.aws_access_key_id,  
                  aws_secret_access_key=config.aws_secret_access_key)

events_client = boto3.client('events',region_name='us-east-1',
                    aws_access_key_id=config.aws_access_key_id,  
                    aws_secret_access_key=config.aws_secret_access_key)

kinesis = boto3.client('firehose', region_name='us-east-1',
                endpoint_url='https://firehose.us-east-1.amazonaws.com',
                aws_access_key_id=config.aws_access_key_id,  
                aws_secret_access_key=config.aws_secret_access_key)

clAth = boto3.client('athena',region_name='us-east-1',
                aws_access_key_id=config.aws_access_key_id,  
                aws_secret_access_key=config.aws_secret_access_key)

clientGlue = boto3.client('glue',region_name='us-east-1',
                    aws_access_key_id=config.aws_access_key_id,  
                    aws_secret_access_key=config.aws_secret_access_key)

clientS3 = boto3.client('s3',region_name='us-east-1',
                    aws_access_key_id=config.aws_access_key_id,  
                    aws_secret_access_key=config.aws_secret_access_key)
 
s3 = boto3.resource('s3',region_name='us-east-1',
                    aws_access_key_id=config.aws_access_key_id,  
                    aws_secret_access_key=config.aws_secret_access_key)

""" UTILS """
# Hora ESP:
locale.setlocale(locale.LC_ALL, 'esp')
hoy = datetime.date.today().strftime("%d de %B del %Y")

# Comprimir el contenido de una carpeta (sin la ruta padre):
def zipdir(path, ziph):
    length = len(path)
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        folder = root[length:] # path without "parent"
        for file in files:
            ziph.write(os.path.join(root, file), os.path.join(folder, file))
            
# Crear Kinesis Firehose Delivery Stream que vuelque datos a un bucket de S3   
def create_s3_delivery_stream(client, stream_name, ARNrol, ARNbucket):
    prefijo = stream_name + '/'
    return client.create_delivery_stream(
        DeliveryStreamName=stream_name,
        DeliveryStreamType="DirectPut",
        S3DestinationConfiguration={
            'RoleARN': ARNrol,
            'BucketARN': ARNbucket,
            'Prefix': prefijo,
            'BufferingHints': {
                'SizeInMBs': 1,
                'IntervalInSeconds': 60
            },
            'CompressionFormat': 'UNCOMPRESSED',
            'EncryptionConfiguration': {
                'NoEncryptionConfig': 'NoEncryption',
            },
            'CloudWatchLoggingOptions': {
                'Enabled': False}
        })     
    
# Crear regla en CloudWatch Events (nombre_reg) y asociar a función Lambda (nombreFun) 
def create_asociate_rule(clienteCW, nombre_reg, frecuencia, clienteLAMB, nombreFun, arnFUN, tarID):
    # Crear nueva regla "nombre_reg", programada cada x tiempo (frecuencia)
    clienteCW.put_rule(Name=nombre_reg, ScheduleExpression=frecuencia, State='ENABLED')
    # Obtener sus características (queremos el ARN)
    response = clienteCW.describe_rule(Name=nombre_reg)
    # Dar permiso a la regla para invocar a la función nombreFun (indicando el ARN de la regla)
    clienteLAMB.add_permission(FunctionName=nombreFun,
                StatementId="Event-".format(nombreFun),
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=response['Arn'],)
    # Asociar regla creada a la función Lambda
    clienteCW.put_targets(Rule=nombre_reg,
                Targets=[{
                    'Id': tarID,
                    'Arn': arnFUN,},])  
    
# Pasar la frecuencia de la regla al formato requerido por boto3
def rule_freq(numero,unidad):
    if(unidad == 'minutos'):
        if(numero == '1'):
            freqr = "rate(" + numero + " minute)"
        else:
            freqr = "rate(" + numero + " minutes)"
    if(unidad == 'horas'):
        if(numero == '1'):
            freqr = "rate(" + numero + " hour)"
        else:
            freqr = "rate(" + numero + " hours)"
   
    return freqr

# Comprobar que no hay otra función Lambda con el mismo nombre:
def check_function_exists(cliente, funcion):
    response = cliente.list_functions()
    funciones = response['Functions']
    nombresFun = []
    exists = False
    for i in range(0,len(funciones)):
        nombresFun.append(funciones[i]['FunctionName'])
    if(funcion in nombresFun):
        exists = True
        
    return exists

""" APLICACIÓN WEB """

@app.route("/", methods =["GET", "POST"])
def index():
    consulta = request.form.get("res")                      # Tipo de consulta: SEARCH/STREAM
    if consulta is not None:                                # Mostrar formulario solicitado
        if(consulta=='str'):
            return render_template('index_stream.html')
        if(consulta=='se'):
            return render_template('index_search.html')
    else:
        return render_template('index.html')
        
@app.route("/index_search", methods =["GET", "POST"])
def index_search():
    # Coger datos del formulario (parámetros de la consulta)
    query_params = {'keyW': request.form.get("que"),
        'ISOCode': request.form.get("lengua"),
        'resultType': request.form.get("res"), 
        'fechaLim': request.form.get("unt"),
        'contador': request.form.get("cont"),
        'nombreFun': request.form.get("fname"), 
        'ruleFreq': request.form.get("frec"),
        'unidadTiempo': request.form.get("frec_regla"), 
        'descripcion': request.form.get("descr")}
    # El nombre del stream va a coincidir con el de la función:
    query_params.update( {'DStream': query_params['nombreFun']} )
    dictParams = {'query_params': query_params}
    # Escribir el diccionario en un bloc de notas (json.dumps) y guardar en el package
    save_path = 'get-tuits-pack/'
    filename = 'parametrosconsulta'
    completeName = os.path.join(save_path, filename+".txt")    
    with open(completeName, 'w') as file:
        file.write(json.dumps(dictParams)) # use 'json.loads' to do the reverse
            
    # Crear el deployment package (el zip que contiene el código de la función Lambda):
    zipf = zipfile.ZipFile('consulta-package.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir('./get-tuits-pack/', zipf)
    zipf.close()
    
    # Cuando se envíe el formulario relleno:
    if(query_params['keyW'] is not None):
        # Comprobar que no existe otra función con ese nombre
        existe = check_function_exists(c, query_params['nombreFun'])
        if existe:
            mensaje = 'Ya existe una función llamada ' + query_params['nombreFun'] + '.'
            flash(mensaje, 'error')
        else:
            nombre = query_params['nombreFun']
            # Si el usuario no indica descripción se pone una por defecto
            if(query_params['descripcion']==''):
                descr = 'Función Lambda creada con Boto3 el ' + hoy +'. Búsqueda: ' + query_params['keyW']
            else:
                descr = query_params['descripcion']
            # Crear Delivery Stream:
            ARNIam = 'arn:aws:iam::189517003434:role/service-role/KinesisFirehoseServiceRole-consultas-str-us-east-1-1616433604848'
            ARNCubo = 'arn:aws:s3:::consultas-interfaz'
            create_s3_delivery_stream(kinesis, query_params['DStream'], ARNIam, ARNCubo)
            # Con el zip del código, generar la función Lambda
            response = c.create_function(
                Code={'ZipFile': open('./consulta-package.zip', 'rb').read()},
                Runtime="python3.7",
                Timeout=10,
                Handler="GetTweets.lambda_handler",
                Description=descr,
                FunctionName=nombre,
                Environment={
                    'Variables': {
                        'consumer_key': config.consumer_key,
                        'consumer_secret': config.consumer_secret,
                        'access_token': config.access_token,
                        'access_token_secret': config.access_token_secret,
                        'aws_access_key_id': config.aws_access_key_id,
                        'aws_secret_access_key': config.aws_secret_access_key
                        },
                    },  
                Role='arn:aws:iam::189517003434:role/tweets-to-kinesis-role')
            fnARN = response['FunctionArn']
            os.remove('consulta-package.zip') # Una vez creada la función Lambda, borrar zip
            # Crear regla en CloudWatch 
            rn = random.randint(0, 1000)
            target_id = nombre + str(rn)
            
            # Si no se especifica frecuencia -> por defecto cada 2h
            if(query_params['ruleFreq'] == ''):
                freqr = "rate(2 hours)"
            else:
                #flash('Creando regla de invocación...','proceso')
                freqr = rule_freq(query_params['ruleFreq'],query_params['unidadTiempo'])
                        
            namer = "rule_" + nombre
            # Crear regla:    
            create_asociate_rule(events_client, namer, freqr, c, nombre, fnARN, target_id)
                
            mensaje1 = 'Generados con éxito: ' 
            flash(mensaje1,'success')
            mensaje2 = 'Función Lambda ' + nombre
            flash(mensaje2,'success')
            mensaje3 = 'Delivery stream ' + nombre
            flash(mensaje3, 'success')
            mensaje4 = 'Regla (disparador) ' + nombre  
            flash(mensaje4,'success')     
            
        return render_template('index_search.html')

@app.route("/index_stream", methods =["GET", "POST"])
def index_stream():
    # Coger datos del formulario -> parámetros de la consulta
    query_params = {
        'keyW': request.form.get("que"),
        'ISOCode': request.form.get("lengua"),
        'nombreFun': request.form.get("fname"),
        'ruleFreq': request.form.get("frec"),
        'unidadTiempo': request.form.get("frec_regla"), # Si no se elige ninguna: None
        'descripcion': request.form.get("descr")}
    # El nombre del stream va a coincidir con el de la función:
    query_params.update( {'DStream': query_params['nombreFun']} )
    dictParams = {'query_params': query_params}
    # Escribir el diccionario en un bloc de notas (json.dumps) y guardar en el package
    save_path = 'GetTwStream-pack/'
    filename = 'parametrosconsulta'
    completeName = os.path.join(save_path, filename+".txt")    
    with open(completeName, 'w') as file:
        file.write(json.dumps(dictParams)) # use 'json.loads' to do the reverse
        
    # Crear el deployment package (el zip que contiene el código de la función Lambda):
    zipf = zipfile.ZipFile('consulta-package.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir('./GetTwStream-pack/', zipf)
    zipf.close()
    
    # Cuando se envíe el formulario relleno:
    if(query_params['keyW'] is not None):
        # Comprobar que no existe otra función con ese nombre
        existe = check_function_exists(c, query_params['nombreFun'])
        if existe:
            mensaje = 'Ya existe una función llamada ' + query_params['nombreFun'] + '.'
            flash(mensaje, 'error')
        else:
            nombre = query_params['nombreFun']
            # Si el usuario no indica descripción se pone una por defecto
            if(query_params['descripcion']==''):
                descr = 'Función Lambda creada con Boto3 el ' + hoy +'. Búsqueda: ' + query_params['keyW']
            else:
                descr = query_params['descripcion']
            
            # Crear Delivery Stream:
            ARNIam = 'arn:aws:iam::189517003434:role/service-role/KinesisFirehoseServiceRole-consultas-str-us-east-1-1616433604848'
            ARNCubo = 'arn:aws:s3:::consultas-interfaz'
            create_s3_delivery_stream(kinesis, query_params['DStream'], ARNIam, ARNCubo)
            # Con el zip del código, generar la función Lambda
            response = c.create_function(
                Code={'ZipFile': open('./consulta-package.zip', 'rb').read()},
                Runtime="python3.7",
                Timeout=60,
                Handler="GetTweetsStream.lambda_handler",
                Description=descr,
                FunctionName=nombre,
                Environment={
                    'Variables': {
                        'consumer_key': config.consumer_key,
                        'consumer_secret': config.consumer_secret,
                        'access_token': config.access_token,
                        'access_token_secret': config.access_token_secret,
                        'aws_access_key_id': config.aws_access_key_id,
                        'aws_secret_access_key': config.aws_secret_access_key
                        },
                    },  
                Role='arn:aws:iam::189517003434:role/tweets-to-kinesis-role')
            fnARN = response['FunctionArn']
            os.remove('consulta-package.zip') # Una vez creada la función Lambda, borrar zip
            # Crear regla en CloudWatch 
            rn = random.randint(0, 1000)
            target_id = nombre + str(rn)
            
            if(query_params['ruleFreq'] == ''):
                freqr = "rate(2 hours)"  # Si no se especifica frecuencia, por defecto cada 2h           
            else:
                freqr = rule_freq(query_params['ruleFreq'],query_params['unidadTiempo']) 
                       
            namer = "rule_" + nombre
            create_asociate_rule(events_client, namer, freqr, c, nombre, fnARN, target_id)
            
            mensaje1 = 'Generados con éxito: ' 
            flash(mensaje1,'success')
            mensaje2 = 'Función Lambda ' + nombre
            flash(mensaje2,'success')
            mensaje3 = 'Delivery stream ' + nombre
            flash(mensaje3, 'success')
            mensaje4 = 'Regla (disparador) ' + nombre  
            flash(mensaje4,'success')  
            
        return render_template('index_stream.html')

@app.route("/procesos", methods =["GET", "POST"])
def procesos():
    response = c.list_functions()
    funciones = response['Functions']
    procesoDEL = request.form.get("proc")   # Borrar función Lambda
    procesoQUE = request.form.get("athe")   # Tabla Athena
    
    # Formato fechas:
    for i in range(0,len(funciones)):
        fecha = funciones[i]['LastModified']
        funciones[i]['LastModified'] = fecha[:fecha.find('T')]
    # Borrar función Lambda:
    if procesoDEL is not None:
        namer = "rule_" + procesoDEL    
        # Borrar la regla (disparador de la función) -> Disociarla de la funcióno                    
        response = events_client.list_targets_by_rule(Rule=namer)
        ident = response['Targets'][0]['Id']
        events_client.remove_targets(Rule=namer, Ids=[ident])
        c.delete_function(FunctionName=procesoDEL)                      # Borrar función Lambda
        events_client.delete_rule(Name=namer)
        kinesis.delete_delivery_stream(DeliveryStreamName=procesoDEL)   # Borrar delivery stream
        response = c.list_functions()
        funciones = response['Functions']
        
    # Almacenado en bucket:
    prefijos = []
    prefijos.append('twitterdemoparsed')    # Prefijos existentes con anterioridad
    prefijos.append('streammethodparsed')
    # Prefijos procedentes de la interfaz:
    bucket = s3.Bucket('interface-processed')
    result = bucket.meta.client.list_objects(Bucket=bucket.name, Delimiter='/')
    for o in result.get('CommonPrefixes'):
        pref = o.get('Prefix')[:-1]
        prefijos.append(pref)
    
    # Tabla Athena:   
    if procesoQUE is not None:
        # Conformar prefijo para el rastreador
        if(procesoQUE == 'twitterdemoparsed' or procesoQUE == 'streammethodparsed'):
            newPrefix = 's3://' + procesoQUE + '/'
        else:
            newPrefix = 's3://interface-processed/' + procesoQUE + '/'
            
        # Cambiar prefijo del Crawler a la carpeta de interés:
        clientGlue.update_crawler(
        Name='interface-crawler',
        Targets={
            'S3Targets': [{'Path': newPrefix},],
            })
        # Ejecutar crawler -> CREACIÓN DE TABLA
        clientGlue.start_crawler(Name='interface-crawler')
        
    return render_template('procesos.html', fun=funciones, cubo = prefijos)

@app.route("/athena", methods =["GET", "POST"])
def athena():
    
    tablaDOWN = request.form.get("downl") 
    
    # Listar las tablas existentes:
    tablas = clAth.list_table_metadata(CatalogName='AwsDataCatalog', DatabaseName='default')
    metadatos = tablas['TableMetadataList']         # Metadatos de las tablas
    # Formato fechas (de datetime a string legible en español)
    for i in range(0,len(metadatos)):
        metadatos[i]['CreateTime'] = metadatos[i]['CreateTime'].strftime("%d de %B del %Y (%H:%M:%S)")
        metadatos[i]['LastAccessTime'] = metadatos[i]['LastAccessTime'].strftime("%d de %B del %Y (%H:%M:%S)")
        
    # Funcionalidad del botón "Descargar"
    if tablaDOWN is not None:   
        # Query Athena
        query = 'SELECT * FROM "default"."' + tablaDOWN + '";' # Descargar tabla completa
        clAth.start_query_execution(QueryString=query,
                                    ResultConfiguration={'OutputLocation': 's3://athenaresults-tfm/'})
        # Listar TODOS los objetos del bucket donde se ha almacenado la Query
        objs = clientS3.list_objects(Bucket='athenaresults-tfm')['Contents']
        # Ordenar por RECIENTES
        objs.sort(key=lambda item:item['LastModified'], reverse=True)
        ultimo = objs[0]                   
        # Descargar el último (el csv que acabamos de generar)
        obj = clientS3.get_object(Bucket='athenaresults-tfm', Key=ultimo['Key'])
        # Convertir a Dataframe y después a CSV -> descarga en navegador (make_response)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()), encoding='utf8')
        resp = make_response(df.to_csv(sep=';', encoding='utf-8',index=False))
        resp.headers["Content-Disposition"] = "attachment; filename=tabla.csv"
        resp.headers["Content-Type"] = "text/csv"
        return resp
     
    return render_template('athena.html', tablas = metadatos)

if __name__ == "__main__":
    app.debug = True
    app.run()