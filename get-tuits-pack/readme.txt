
get-tuits-package.zip -> contiene el código + librerías de la función Lambda tweets2kinesis

Se podían haber construido Layers para incluir las librerías en la función Lambda

Usa el método "search" [http://docs.tweepy.org/en/latest/api.html#API.search]: no mantiene abierta ninguna conexión, sino que obtiene los datos de la API de Twitter y cierra