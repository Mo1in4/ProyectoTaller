"""
config.py
Configuración general del sistema ASADAS.
"""

# Endpoint de datos abiertos ARESEP
ENDPOINT_URL = "https://datos.aresep.go.cr/ws.datosabiertos/Services/IA/Asadas.svc/ObtenerInformacionUbicacionAsadas"

# Rutas de archivos binarios
ARCHIVO_PRINCIPAL = "data/asadas.bin"
ARCHIVO_ARBOL = "data/arbol_bst.bin"
ARCHIVO_GEOGRAFICO = "data/geografico.bin"
ARCHIVO_METADATA = "data/metadata.json"
ARCHIVO_MAPA = "maps/asadas_mapa.html"

# Configuración del servidor
HOST_SERVIDOR = "0.0.0.0"
PUERTO_SERVIDOR = 9000
MAX_CLIENTES = 10
BUFFER_SIZE = 4096

# Tamaño fijo de campos en el archivo binario principal
TAM_CANTON = 60
TAM_CODIGO_DTA = 20
TAM_CORREO = 80
TAM_DISTRITO = 60
TAM_FAX = 20
TAM_OPERADOR = 100
TAM_PROVINCIA = 40
TAM_TELEFONO = 20
TAM_TIPO_SISTEMA = 40

# Sistema de coordenadas
EPSG_CRTM05 = 5367
EPSG_WGS84 = 4326
