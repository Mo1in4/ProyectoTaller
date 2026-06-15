"""
arbol_bst.py
Árbol Binario de Búsqueda (BST) persistente indexado por idAsada.
Se almacena en un archivo binario como un arreglo de nodos con punteros lógicos (índices).
Todos los métodos son iterativos para evitar RecursionError con grandes volúmenes de datos.
"""

import struct
import os
from modelos import NodoArbol, Asada
from config import ARCHIVO_ARBOL

# Formato binario del nodo: idAsada(i), posicion(q), izquierdo(i), derecho(i)
FORMATO_NODO = "=iqii"
TAMANO_NODO = struct.calcsize(FORMATO_NODO)


class ArbolBST:
    """
    BST en memoria construido desde el archivo binario.
    Los punteros son índices lógicos dentro del arreglo de nodos.
    """

    def __init__(self):
        self.nodos: list[NodoArbol] = []
        self.raiz: int = -1

    # ------------------------------------------------------------------ #
    #  Construcción (iterativa)
    # ------------------------------------------------------------------ #

    def insertar(self, idAsada: int, posicion: int) -> None:
        """Inserta un nodo con idAsada y posición física en el archivo principal (iterativo)."""
        nuevoIndice = len(self.nodos)
        self.nodos.append(NodoArbol(idAsada=idAsada, posicion=posicion))
        if self.raiz == -1:
            self.raiz = nuevoIndice
            return

        indiceActual = self.raiz
        while True:
            actual = self.nodos[indiceActual]
            if idAsada < actual.idAsada:
                if actual.izquierdo == -1:
                    actual.izquierdo = nuevoIndice
                    break
                else:
                    indiceActual = actual.izquierdo
            else:
                if actual.derecho == -1:
                    actual.derecho = nuevoIndice
                    break
                else:
                    indiceActual = actual.derecho

    # ------------------------------------------------------------------ #
    #  Búsqueda (iterativa)
    # ------------------------------------------------------------------ #

    def buscar(self, idAsada: int) -> NodoArbol | None:
        """Retorna el nodo con el idAsada indicado o None si no existe (iterativo)."""
        indice = self.raiz
        while indice != -1:
            nodo = self.nodos[indice]
            if idAsada == nodo.idAsada:
                return nodo
            elif idAsada < nodo.idAsada:
                indice = nodo.izquierdo
            else:
                indice = nodo.derecho
        return None

    # ------------------------------------------------------------------ #
    #  Persistencia
    # ------------------------------------------------------------------ #

    def guardar(self) -> None:
        """Serializa el árbol al archivo binario."""
        os.makedirs(os.path.dirname(ARCHIVO_ARBOL), exist_ok=True)
        with open(ARCHIVO_ARBOL, "wb") as archivo:
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
        """Retorna los nodos en orden ascendente por idAsada (iterativo con pila)."""
        resultado = []
        pila = []
        indice = self.raiz
        while pila or indice != -1:
            while indice != -1:
                pila.append(indice)
                indice = self.nodos[indice].izquierdo
            indice = pila.pop()
            resultado.append(self.nodos[indice])
            indice = self.nodos[indice].derecho
        return resultado

    def construirDesdeAsadas(self, listaAsadas: list[Asada]) -> None:
        """Reconstruye el árbol completo desde una lista de ASADAS."""
        self.nodos.clear()
        self.raiz = -1
        from archivo_principal import obtenerPosicionPorIndice
        for indice, asada in enumerate(listaAsadas):
            posicion = obtenerPosicionPorIndice(indice)
            self.insertar(asada.idAsada, posicion)
