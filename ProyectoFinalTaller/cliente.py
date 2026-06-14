"""
cliente.py
Cliente TCP para realizar consultas remotas al servidor ASADAS.
"""

import socket
import json
from config import HOST_SERVIDOR, PUERTO_SERVIDOR, BUFFER_SIZE


class ClienteASADAS:
    """Cliente TCP para consultar el servidor ASADAS."""

    def __init__(self, host: str = HOST_SERVIDOR, puerto: int = PUERTO_SERVIDOR):
        self.host = host
        self.puerto = puerto
        self.conexion: socket.socket | None = None

    def conectar(self) -> bool:
        """Establece conexión con el servidor."""
        try:
            self.conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conexion.connect((self.host, self.puerto))
            print(f"[Cliente] Conectado a {self.host}:{self.puerto}")
            return True
        except ConnectionRefusedError:
            print(f"[Cliente] No se pudo conectar a {self.host}:{self.puerto}")
            return False
        except OSError as e:
            print(f"[Cliente] Error de red: {e}")
            return False

    def desconectar(self) -> None:
        if self.conexion:
            self.conexion.close()
            self.conexion = None
            print("[Cliente] Desconectado.")

    def _enviarMensaje(self, datos: dict) -> None:
        contenido = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        longitud = len(contenido).to_bytes(4, "big")
        self.conexion.sendall(longitud + contenido)

    def _recibirMensaje(self) -> dict | None:
        try:
            cabecera = self._recibirExacto(4)
            if not cabecera:
                return None
            longitud = int.from_bytes(cabecera, "big")
            datos = self._recibirExacto(longitud)
            if not datos:
                return None
            return json.loads(datos.decode("utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _recibirExacto(self, n: int) -> bytes | None:
        buffer = b""
        while len(buffer) < n:
            fragmento = self.conexion.recv(n - len(buffer))
            if not fragmento:
                return None
            buffer += fragmento
        return buffer

    def _solicitar(self, solicitud: dict) -> dict | None:
        if not self.conexion:
            print("[Cliente] No hay conexión activa.")
            return None
        try:
            self._enviarMensaje(solicitud)
            return self._recibirMensaje()
        except OSError as e:
            print(f"[Cliente] Error al comunicarse con el servidor: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Métodos de consulta
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica si el servidor está activo."""
        resp = self._solicitar({"accion": "ping"})
        return resp is not None and resp.get("estado") == "ok"

    def buscarPorId(self, idAsada: int) -> dict | None:
        """Busca una ASADA por su identificador."""
        resp = self._solicitar({"accion": "buscarPorId", "idAsada": idAsada})
        if resp and resp.get("estado") == "ok":
            return resp.get("asada")
        return None

    def listarProvincias(self) -> list[str]:
        resp = self._solicitar({"accion": "listarProvincias"})
        if resp and resp.get("estado") == "ok":
            return resp.get("provincias", [])
        return []

    def listarCantones(self, provincia: str) -> list[str]:
        resp = self._solicitar({"accion": "listarCantones", "provincia": provincia})
        if resp and resp.get("estado") == "ok":
            return resp.get("cantones", [])
        return []

    def listarDistritos(self, provincia: str, canton: str) -> list[str]:
        resp = self._solicitar({
            "accion": "listarDistritos",
            "provincia": provincia,
            "canton": canton,
        })
        if resp and resp.get("estado") == "ok":
            return resp.get("distritos", [])
        return []

    def listarAsadasEnDistrito(self, provincia: str, canton: str, distrito: str) -> list[dict]:
        resp = self._solicitar({
            "accion": "listarAsadasDistrito",
            "provincia": provincia,
            "canton": canton,
            "distrito": distrito,
        })
        if resp and resp.get("estado") == "ok":
            return resp.get("asadas", [])
        return []

    def __enter__(self):
        self.conectar()
        return self

    def __exit__(self, *args):
        self.desconectar()
