"""
arbol_bst.py
Árbol Binario de Búsqueda (BST) persistente indexado por idAsada.
Se almacena en un archivo binario como un arreglo de nodos con punteros lógicos (índices).
"""

import struct
import os
from modelos import NodoArbol, Asada
from config import ARCHIVO_ARBOL

# Formato binario del nodo: idAsada(i), posicion(q), izquierdo(i), derecho(i)
FORMATO_NODO = "=iqii"
TAMANO_NODO = struct.calcsize(FORMATO_NODO)
RAIZ_INDEX = 0   # El primer nodo escrito siempre es la raíz


class ArbolBST:
    """
    BST en memoria construido desde el archivo binario.
    Los punteros son índices lógicos dentro del arreglo de nodos.
    """

    def __init__(self):
        self.nodos: list[NodoArbol] = []
        self.raiz: int = -1   # Índice del nodo raíz

    # ------------------------------------------------------------------ #
    #  Construcción
    # ------------------------------------------------------------------ #

    def insertar(self, idAsada: int, posicion: int) -> None:
        """Inserta un nodo con idAsada y posición física en el archivo principal."""
        nuevoIndice = len(self.nodos)
        self.nodos.append(NodoArbol(idAsada=idAsada, posicion=posicion))
        if self.raiz == -1:
            self.raiz = nuevoIndice
        else:
            self._insertarRecursivo(self.raiz, nuevoIndice)

    def _insertarRecursivo(self, indiceActual: int, nuevoIndice: int) -> None:
        actual = self.nodos[indiceActual]
        nuevo = self.nodos[nuevoIndice]
        if nuevo.idAsada < actual.idAsada:
            if actual.izquierdo == -1:
                actual.izquierdo = nuevoIndice
            else:
                self._insertarRecursivo(actual.izquierdo, nuevoIndice)
        else:
            if actual.derecho == -1:
                actual.derecho = nuevoIndice
            else:
                self._insertarRecursivo(actual.derecho, nuevoIndice)

    # ------------------------------------------------------------------ #
    #  Búsqueda
    # ------------------------------------------------------------------ #

    def buscar(self, idAsada: int) -> NodoArbol | None:
        """Retorna el nodo con el idAsada indicado o None si no existe."""
        return self._buscarRecursivo(self.raiz, idAsada)

    def _buscarRecursivo(self, indice: int, idAsada: int) -> NodoArbol | None:
        if indice == -1:
            return None
        nodo = self.nodos[indice]
        if idAsada == nodo.idAsada:
            return nodo
        elif idAsada < nodo.idAsada:
            return self._buscarRecursivo(nodo.izquierdo, idAsada)
        else:
            return self._buscarRecursivo(nodo.derecho, idAsada)

    # ------------------------------------------------------------------ #
    #  Persistencia
    # ------------------------------------------------------------------ #

    def guardar(self) -> None:
        """Serializa el árbol al archivo binario."""
        os.makedirs(os.path.dirname(ARCHIVO_ARBOL), exist_ok=True)
        with open(ARCHIVO_ARBOL, "wb") as archivo:
            # Primer entero: índice de la raíz
            archivo.write(struct.pack("=i", self.raiz))
            for nodo in self.nodos:
                archivo.write(struct.pack(
                    FORMATO_NODO,
                    nodo.idAsada,
                    nodo.posicion,
                    nodo.izquierdo,
                    nodo.derecho,
                ))

    def cargar(self) -> bool:
        """Carga el árbol desde el archivo binario. Retorna True si tuvo éxito."""
        if not os.path.exists(ARCHIVO_ARBOL):
            return False
        self.nodos.clear()
        with open(ARCHIVO_ARBOL, "rb") as archivo:
            cabecera = archivo.read(4)
            if len(cabecera) < 4:
                return False
            self.raiz = struct.unpack("=i", cabecera)[0]
            while True:
                datos = archivo.read(TAMANO_NODO)
                if len(datos) < TAMANO_NODO:
                    break
                idAsada, posicion, izquierdo, derecho = struct.unpack(FORMATO_NODO, datos)
                self.nodos.append(NodoArbol(
                    idAsada=idAsada,
                    posicion=posicion,
                    izquierdo=izquierdo,
                    derecho=derecho,
                ))
        return True

    # ------------------------------------------------------------------ #
    #  Utilidades
    # ------------------------------------------------------------------ #

    def inorden(self) -> list[NodoArbol]:
        """Retorna los nodos en orden ascendente por idAsada."""
        resultado = []
        self._inordenRecursivo(self.raiz, resultado)
        return resultado

    def _inordenRecursivo(self, indice: int, resultado: list) -> None:
        if indice == -1:
            return
        nodo = self.nodos[indice]
        self._inordenRecursivo(nodo.izquierdo, resultado)
        resultado.append(nodo)
        self._inordenRecursivo(nodo.derecho, resultado)

    def construirDesdeAsadas(self, listaAsadas: list[Asada]) -> None:
        """Reconstruye el árbol completo desde una lista de ASADAS ordenada."""
        self.nodos.clear()
        self.raiz = -1
        from archivo_principal import obtenerPosicionPorIndice
        for indice, asada in enumerate(listaAsadas):
            posicion = obtenerPosicionPorIndice(indice)
            self.insertar(asada.idAsada, posicion)
