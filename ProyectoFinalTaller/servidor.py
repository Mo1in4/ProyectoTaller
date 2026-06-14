"""
servidor.py
Servidor TCP/IP con hilos para atención concurrente de clientes remotos.
Solo el servidor central puede actualizar datos.
Protocolo de comunicación basado en mensajes JSON.
"""

import socket
import threading
import json
import os
import sys

from config import HOST_SERVIDOR, PUERTO_SERVIDOR, MAX_CLIENTES, BUFFER_SIZE
from arbol_bst import ArbolBST
from archivo_geografico import GestorGeografico
from archivo_principal import leerRegistroPorPosicion
from modelos import Asada


def _asadaADict(asada: Asada) -> dict:
    """Serializa una ASADA a diccionario."""
    return {
        "idAsada": asada.idAsada,
        "idObjeto": asada.idObjeto,
        "canton": asada.canton,
        "codigoDTA": asada.codigoDTA,
        "coordenadaX": asada.coordenadaX,
        "coordenadaY": asada.coordenadaY,
        "correo": asada.correo,
        "distrito": asada.distrito,
        "fax": asada.fax,
        "operador": asada.operador,
        "provincia": asada.provincia,
        "telefono": asada.telefono,
        "tipoSistema": asada.tipoSistema,
    }


class ManejadorCliente(threading.Thread):
    """Hilo independiente para atender a un cliente conectado."""

    def __init__(self, conexion: socket.socket, direccion: tuple,
                 arbol: ArbolBST, geo: GestorGeografico, bloqueo: threading.Lock):
        super().__init__(daemon=True)
        self.conexion = conexion
        self.direccion = direccion
        self.arbol = arbol
        self.geo = geo
        self.bloqueo = bloqueo

    def run(self):
        print(f"[Servidor] Cliente conectado: {self.direccion}")
        try:
            while True:
                datos = self._recibirMensaje()
                if datos is None:
                    break
                respuesta = self._procesarSolicitud(datos)
                self._enviarMensaje(respuesta)
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self.conexion.close()
            print(f"[Servidor] Cliente desconectado: {self.direccion}")

    def _recibirMensaje(self) -> dict | None:
        """Recibe un mensaje JSON precedido por 4 bytes de longitud."""
        try:
            cabecera = self._recibirExacto(4)
            if not cabecera:
                return None
            longitud = int.from_bytes(cabecera, "big")
            if longitud <= 0 or longitud > 1_000_000:
                return None
            datos = self._recibirExacto(longitud)
            if not datos:
                return None
            return json.loads(datos.decode("utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _recibirExacto(self, n: int) -> bytes | None:
        """Recibe exactamente n bytes del socket."""
        buffer = b""
        while len(buffer) < n:
            fragmento = self.conexion.recv(n - len(buffer))
            if not fragmento:
                return None
            buffer += fragmento
        return buffer

    def _enviarMensaje(self, datos: dict) -> None:
        """Envía un mensaje JSON precedido por 4 bytes de longitud."""
        contenido = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        longitud = len(contenido).to_bytes(4, "big")
        self.conexion.sendall(longitud + contenido)

    def _procesarSolicitud(self, solicitud: dict) -> dict:
        """Procesa la solicitud del cliente y retorna la respuesta."""
        accion = solicitud.get("accion", "")

        if accion == "buscarPorId":
            return self._buscarPorId(solicitud)
        elif accion == "listarProvincias":
            return self._listarProvincias()
        elif accion == "listarCantones":
            return self._listarCantones(solicitud)
        elif accion == "listarDistritos":
            return self._listarDistritos(solicitud)
        elif accion == "listarAsadasDistrito":
            return self._listarAsadasDistrito(solicitud)
        elif accion == "ping":
            return {"estado": "ok", "mensaje": "Servidor ASADAS activo"}
        else:
            return {"estado": "error", "mensaje": f"Acción desconocida: {accion}"}

    def _buscarPorId(self, solicitud: dict) -> dict:
        try:
            idAsada = int(solicitud.get("idAsada", 0))
        except (ValueError, TypeError):
            return {"estado": "error", "mensaje": "idAsada inválido"}

        with self.bloqueo:
            nodo = self.arbol.buscar(idAsada)

        if nodo is None:
            return {"estado": "notFound", "mensaje": f"ASADA {idAsada} no encontrada"}

        asada = leerRegistroPorPosicion(nodo.posicion)
        if asada is None:
            return {"estado": "error", "mensaje": "Error al leer el archivo principal"}

        return {"estado": "ok", "asada": _asadaADict(asada)}

    def _listarProvincias(self) -> dict:
        with self.bloqueo:
            provincias = self.geo.listarProvincias()
        return {"estado": "ok", "provincias": provincias}

    def _listarCantones(self, solicitud: dict) -> dict:
        provincia = solicitud.get("provincia", "")
        with self.bloqueo:
            cantones = self.geo.listarCantones(provincia)
        return {"estado": "ok", "cantones": cantones}

    def _listarDistritos(self, solicitud: dict) -> dict:
        provincia = solicitud.get("provincia", "")
        canton = solicitud.get("canton", "")
        with self.bloqueo:
            distritos = self.geo.listarDistritos(provincia, canton)
        return {"estado": "ok", "distritos": distritos}

    def _listarAsadasDistrito(self, solicitud: dict) -> dict:
        provincia = solicitud.get("provincia", "")
        canton = solicitud.get("canton", "")
        distrito = solicitud.get("distrito", "")
        with self.bloqueo:
            refs = self.geo.listarAsadasEnDistrito(provincia, canton, distrito)

        asadas = []
        for ref in refs:
            asada = leerRegistroPorPosicion(ref["posicion"])
            if asada:
                asadas.append(_asadaADict(asada))

        return {"estado": "ok", "asadas": asadas}


class Servidor:
    """Servidor principal que acepta conexiones y crea hilos por cliente."""

    def __init__(self):
        self.arbol = ArbolBST()
        self.geo = GestorGeografico()
        self.bloqueo = threading.Lock()
        self.socketServidor: socket.socket | None = None
        self.activo = False

    def cargarEstructuras(self) -> bool:
        """Carga las estructuras desde archivos binarios."""
        arbolOk = self.arbol.cargar()
        geoOk = self.geo.cargar()
        if not arbolOk or not geoOk:
            print("[Servidor] ADVERTENCIA: No se encontraron archivos de datos.")
            print("[Servidor] Ejecute la actualización de datos primero.")
            return False
        print(f"[Servidor] Estructuras cargadas: {len(self.arbol.nodos)} ASADAS en árbol.")
        return True

    def recargarEstructuras(self) -> None:
        """Recarga las estructuras en caliente (thread-safe)."""
        nuevoArbol = ArbolBST()
        nuevoGeo = GestorGeografico()
        nuevoArbol.cargar()
        nuevoGeo.cargar()
        with self.bloqueo:
            self.arbol = nuevoArbol
            self.geo = nuevoGeo
        print("[Servidor] Estructuras recargadas.")

    def iniciar(self, host: str = HOST_SERVIDOR, puerto: int = PUERTO_SERVIDOR) -> None:
        """Inicia el servidor TCP y entra al bucle de aceptación."""
        self.cargarEstructuras()
        self.socketServidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socketServidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socketServidor.bind((host, puerto))
        self.socketServidor.listen(MAX_CLIENTES)
        self.activo = True

        print(f"[Servidor] Escuchando en {host}:{puerto}")
        print("[Servidor] Presione Ctrl+C para detener.")

        try:
            while self.activo:
                try:
                    conexion, direccion = self.socketServidor.accept()
                    hilo = ManejadorCliente(
                        conexion, direccion,
                        self.arbol, self.geo, self.bloqueo
                    )
                    hilo.start()
                except OSError:
                    break
        except KeyboardInterrupt:
            print("\n[Servidor] Deteniendo servidor...")
        finally:
            self.detener()

    def detener(self) -> None:
        self.activo = False
        if self.socketServidor:
            self.socketServidor.close()
        print("[Servidor] Servidor detenido.")


if __name__ == "__main__":
    srv = Servidor()
    srv.iniciar()
