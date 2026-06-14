"""
archivo_principal.py
Manejo del archivo binario principal de registros de ASADAS.
Estrategia: registros de tamaño fijo con padding de cadenas.
"""

import struct
import os
from modelos import Asada
from config import *


# Formato de registro fijo
# canton(60s), codigoDTA(20s), coordX(d), coordY(d), correo(80s),
# distrito(60s), fax(20s), idAsada(i), idObjeto(i),
# operador(100s), provincia(40s), telefono(20s), tipoSistema(40s)
FORMATO_REGISTRO = "=60s20sdd80s60s20sii100s40s20s40s"
TAMANO_REGISTRO = struct.calcsize(FORMATO_REGISTRO)


def _codificarCadena(texto: str, longitud: int) -> bytes:
    """Codifica una cadena a bytes con longitud fija."""
    return texto.encode("utf-8", errors="replace")[:longitud].ljust(longitud, b'\x00')


def _decodificarCadena(datos: bytes) -> str:
    """Decodifica bytes a cadena eliminando bytes nulos."""
    return datos.rstrip(b'\x00').decode("utf-8", errors="replace")


def guardarRegistros(listaAsadas: list[Asada]) -> None:
    """
    Escribe todos los registros en el archivo binario principal.
    Cada registro ocupa exactamente TAMANO_REGISTRO bytes.
    """
    os.makedirs(os.path.dirname(ARCHIVO_PRINCIPAL), exist_ok=True)
    with open(ARCHIVO_PRINCIPAL, "wb") as archivo:
        for asada in listaAsadas:
            registro = struct.pack(
                FORMATO_REGISTRO,
                _codificarCadena(asada.canton, TAM_CANTON),
                _codificarCadena(asada.codigoDTA, TAM_CODIGO_DTA),
                asada.coordenadaX,
                asada.coordenadaY,
                _codificarCadena(asada.correo, TAM_CORREO),
                _codificarCadena(asada.distrito, TAM_DISTRITO),
                _codificarCadena(asada.fax, TAM_FAX),
                asada.idAsada,
                asada.idObjeto,
                _codificarCadena(asada.operador, TAM_OPERADOR),
                _codificarCadena(asada.provincia, TAM_PROVINCIA),
                _codificarCadena(asada.telefono, TAM_TELEFONO),
                _codificarCadena(asada.tipoSistema, TAM_TIPO_SISTEMA),
            )
            archivo.write(registro)


def leerRegistroPorPosicion(posicion: int) -> Asada | None:
    """
    Lee un único registro del archivo principal usando su posición en bytes.
    """
    if not os.path.exists(ARCHIVO_PRINCIPAL):
        return None
    with open(ARCHIVO_PRINCIPAL, "rb") as archivo:
        archivo.seek(posicion)
        datos = archivo.read(TAMANO_REGISTRO)
        if len(datos) < TAMANO_REGISTRO:
            return None
        return _parsearRegistro(datos)


def leerTodosLosRegistros() -> list[Asada]:
    """Lee y retorna todos los registros del archivo principal."""
    if not os.path.exists(ARCHIVO_PRINCIPAL):
        return []
    registros = []
    with open(ARCHIVO_PRINCIPAL, "rb") as archivo:
        while True:
            datos = archivo.read(TAMANO_REGISTRO)
            if len(datos) < TAMANO_REGISTRO:
                break
            registros.append(_parsearRegistro(datos))
    return registros


def obtenerPosicionPorIndice(indice: int) -> int:
    """Calcula la posición en bytes de un registro según su índice (0-based)."""
    return indice * TAMANO_REGISTRO


def _parsearRegistro(datos: bytes) -> Asada:
    """Convierte bytes a objeto Asada."""
    campos = struct.unpack(FORMATO_REGISTRO, datos)
    asada = Asada()
    asada.canton = _decodificarCadena(campos[0])
    asada.codigoDTA = _decodificarCadena(campos[1])
    asada.coordenadaX = campos[2]
    asada.coordenadaY = campos[3]
    asada.correo = _decodificarCadena(campos[4])
    asada.distrito = _decodificarCadena(campos[5])
    asada.fax = _decodificarCadena(campos[6])
    asada.idAsada = campos[7]
    asada.idObjeto = campos[8]
    asada.operador = _decodificarCadena(campos[9])
    asada.provincia = _decodificarCadena(campos[10])
    asada.telefono = _decodificarCadena(campos[11])
    asada.tipoSistema = _decodificarCadena(campos[12])
    return asada
