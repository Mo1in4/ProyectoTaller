"""
modelos.py
Definición de las estructuras de datos del sistema ASADAS.
"""

import struct
from dataclasses import dataclass, field
from typing import Optional
from config import *


@dataclass
class Asada:
    """Representa un registro completo de una ASADA."""
    idAsada: int = 0
    idObjeto: int = 0
    canton: str = ""
    codigoDTA: str = ""
    coordenadaX: float = 0.0
    coordenadaY: float = 0.0
    correo: str = ""
    distrito: str = ""
    fax: str = ""
    operador: str = ""
    provincia: str = ""
    telefono: str = ""
    tipoSistema: str = ""

    @staticmethod
    def desdeJson(datos: dict) -> "Asada":
        """Construye un objeto Asada a partir de un diccionario JSON."""
        asada = Asada()
        asada.idAsada = int(datos.get("id_Asada", 0) or 0)
        asada.idObjeto = int(datos.get("id_Objecto", 0) or 0)
        asada.canton = str(datos.get("canton", "") or "")
        asada.codigoDTA = str(datos.get("codigoDTA", "") or "")
        try:
            asada.coordenadaX = float(datos.get("coordenadaX", 0) or 0)
        except (ValueError, TypeError):
            asada.coordenadaX = 0.0
        try:
            asada.coordenadaY = float(datos.get("coordenadaY", 0) or 0)
        except (ValueError, TypeError):
            asada.coordenadaY = 0.0
        asada.correo = str(datos.get("correo", "") or "")
        asada.distrito = str(datos.get("distrito", "") or "")
        asada.fax = str(datos.get("fax", "") or "")
        asada.operador = str(datos.get("operador", "") or "")
        asada.provincia = str(datos.get("provincia", "") or "")
        asada.telefono = str(datos.get("telefono", "") or "")
        asada.tipoSistema = str(datos.get("tipoSistema", "") or "")
        return asada

    def __repr__(self):
        return (f"Asada(id={self.idAsada}, operador='{self.operador}', "
                f"provincia='{self.provincia}', canton='{self.canton}', "
                f"distrito='{self.distrito}')")


@dataclass
class NodoArbol:
    """Nodo del árbol binario de búsqueda indexado por idAsada."""
    idAsada: int = 0
    posicion: int = -1      # Posición en el archivo principal (bytes)
    izquierdo: int = -1     # Índice lógico del hijo izquierdo
    derecho: int = -1       # Índice lógico del hijo derecho

    # Formato binario: idAsada(i), posicion(q), izquierdo(i), derecho(i)
    FORMATO = "=iqi i"
    TAMANO = struct.calcsize("=iqii")

    def aBytes(self) -> bytes:
        return struct.pack("=iqii", self.idAsada, self.posicion,
                           self.izquierdo, self.derecho)

    @staticmethod
    def desdeBytes(datos: bytes) -> "NodoArbol":
        idAsada, posicion, izquierdo, derecho = struct.unpack("=iqii", datos)
        return NodoArbol(idAsada=idAsada, posicion=posicion,
                         izquierdo=izquierdo, derecho=derecho)


@dataclass
class NodoProvincia:
    """Nodo de una provincia en la lista enlazada geográfica."""
    nombre: str = ""
    primCanton: int = -1   # Índice lógico del primer cantón
    siguiente: int = -1    # Siguiente provincia


@dataclass
class NodoCanton:
    """Nodo de un cantón en la lista enlazada geográfica."""
    nombre: str = ""
    primDistrito: int = -1
    siguienteEnProvincia: int = -1


@dataclass
class NodoDistrito:
    """Nodo de un distrito en la lista enlazada geográfica."""
    nombre: str = ""
    primAsada: int = -1
    siguienteEnCanton: int = -1


@dataclass
class NodoAsadaGeo:
    """Nodo que referencia una ASADA dentro de un distrito."""
    idAsada: int = 0
    posicion: int = -1     # Posición en archivo principal
    siguiente: int = -1    # Siguiente ASADA en el distrito
