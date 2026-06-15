"""
archivo_geografico.py
Estructura jerárquica geográfica: Provincia → Cantón → Distrito → ASADAS
Implementada mediante listas enlazadas con punteros lógicos en archivo binario.
"""

import struct
import os
from modelos import Asada
from config import ARCHIVO_GEOGRAFICO
from archivo_principal import obtenerPosicionPorIndice

# ------------------------------------------------------------------ #
#  Formatos binarios
# ------------------------------------------------------------------ #
# Cadenas de tamaño fijo en los nodos geográficos
TAM_NOMBRE = 60

# Provincia: nombre(60s), primCanton(i), siguiente(i)
FMT_PROVINCIA = f"={TAM_NOMBRE}sii"
TAM_PROVINCIA = struct.calcsize(FMT_PROVINCIA)

# Cantón: nombre(60s), primDistrito(i), siguienteEnProvincia(i)
FMT_CANTON = f"={TAM_NOMBRE}sii"
TAM_CANTON = struct.calcsize(FMT_CANTON)

# Distrito: nombre(60s), primAsada(i), siguienteEnCanton(i)
FMT_DISTRITO = f"={TAM_NOMBRE}sii"
TAM_DISTRITO = struct.calcsize(FMT_DISTRITO)

# Nodo ASADA geo: idAsada(i), posicion(q), siguiente(i)
FMT_ASADA_GEO = "=iqi"
TAM_ASADA_GEO = struct.calcsize(FMT_ASADA_GEO)

# Cabecera del archivo: (int) índice del primer nodo provincia
FMT_CABECERA = "=i"
TAM_CABECERA = struct.calcsize(FMT_CABECERA)

# Marcadores de tipo de nodo en el archivo
TIPO_PROVINCIA = 0
TIPO_CANTON = 1
TIPO_DISTRITO = 2
TIPO_ASADA_GEO = 3
FMT_TIPO = "=B"   # 1 byte unsigned
TAM_TIPO = 1


def _enc(texto: str) -> bytes:
    return texto.encode("utf-8", errors="replace")[:TAM_NOMBRE].ljust(TAM_NOMBRE, b'\x00')


def _dec(datos: bytes) -> str:
    return datos.rstrip(b'\x00').decode("utf-8", errors="replace")


class GestorGeografico:
    """
    Construye y consulta la jerarquía geográfica en memoria,
    y la persiste en un archivo binario.
    """

    def __init__(self):
        # Listas en memoria
        self.provincias: list[dict] = []   # {nombre, primCanton, siguiente}
        self.cantones: list[dict] = []
        self.distritos: list[dict] = []
        self.asadasGeo: list[dict] = []    # {idAsada, posicion, siguiente}

    # ------------------------------------------------------------------ #
    #  Construcción desde lista de ASADAS
    # ------------------------------------------------------------------ #

    def construir(self, listaAsadas: list[Asada]) -> None:
        """Construye la estructura jerárquica desde una lista de ASADAS."""
        self.provincias.clear()
        self.cantones.clear()
        self.distritos.clear()
        self.asadasGeo.clear()

        # Índices de búsqueda rápida: nombre → índice en lista
        idxProvincia: dict[str, int] = {}
        idxCanton: dict[tuple, int] = {}
        idxDistrito: dict[tuple, int] = {}

        for indiceAsada, asada in enumerate(listaAsadas):
            posicion = obtenerPosicionPorIndice(indiceAsada)
            nomProv = asada.provincia.strip()
            nomCant = asada.canton.strip()
            nomDist = asada.distrito.strip()

            # Provincia
            if nomProv not in idxProvincia:
                idxProvincia[nomProv] = len(self.provincias)
                self.provincias.append({
                    "nombre": nomProv,
                    "primCanton": -1,
                    "siguiente": -1,
                })

            iProv = idxProvincia[nomProv]

            # Cantón
            claveCanton = (nomProv, nomCant)
            if claveCanton not in idxCanton:
                iCant = len(self.cantones)
                idxCanton[claveCanton] = iCant
                self.cantones.append({
                    "nombre": nomCant,
                    "primDistrito": -1,
                    "siguienteEnProvincia": -1,
                })
                # Enlazar cantón en la provincia
                self._enlazarCanton(iProv, iCant)

            iCant = idxCanton[claveCanton]

            # Distrito
            claveDist = (nomProv, nomCant, nomDist)
            if claveDist not in idxDistrito:
                iDist = len(self.distritos)
                idxDistrito[claveDist] = iDist
                self.distritos.append({
                    "nombre": nomDist,
                    "primAsada": -1,
                    "siguienteEnCanton": -1,
                })
                self._enlazarDistrito(iCant, iDist)

            iDist = idxDistrito[claveDist]

            # ASADA geo
            iAsadaGeo = len(self.asadasGeo)
            self.asadasGeo.append({
                "idAsada": asada.idAsada,
                "posicion": posicion,
                "siguiente": -1,
            })
            self._enlazarAsada(iDist, iAsadaGeo)

        # Enlazar provincias entre sí
        for i in range(len(self.provincias) - 1):
            self.provincias[i]["siguiente"] = i + 1

    def _enlazarCanton(self, iProv: int, iCant: int) -> None:
        prov = self.provincias[iProv]
        if prov["primCanton"] == -1:
            prov["primCanton"] = iCant
        else:
            actual = prov["primCanton"]
            while self.cantones[actual]["siguienteEnProvincia"] != -1:
                actual = self.cantones[actual]["siguienteEnProvincia"]
            self.cantones[actual]["siguienteEnProvincia"] = iCant

    def _enlazarDistrito(self, iCant: int, iDist: int) -> None:
        cant = self.cantones[iCant]
        if cant["primDistrito"] == -1:
            cant["primDistrito"] = iDist
        else:
            actual = cant["primDistrito"]
            while self.distritos[actual]["siguienteEnCanton"] != -1:
                actual = self.distritos[actual]["siguienteEnCanton"]
            self.distritos[actual]["siguienteEnCanton"] = iDist

    def _enlazarAsada(self, iDist: int, iAsadaGeo: int) -> None:
        dist = self.distritos[iDist]
        if dist["primAsada"] == -1:
            dist["primAsada"] = iAsadaGeo
        else:
            actual = dist["primAsada"]
            while self.asadasGeo[actual]["siguiente"] != -1:
                actual = self.asadasGeo[actual]["siguiente"]
            self.asadasGeo[actual]["siguiente"] = iAsadaGeo

    # ------------------------------------------------------------------ #
    #  Persistencia
    # ------------------------------------------------------------------ #

    def guardar(self) -> None:
        """Guarda toda la estructura en el archivo binario geográfico."""
        os.makedirs(os.path.dirname(ARCHIVO_GEOGRAFICO), exist_ok=True)
        with open(ARCHIVO_GEOGRAFICO, "wb") as f:
            # Cabecera: cantidad de cada tipo
            f.write(struct.pack("=iiii",
                                len(self.provincias),
                                len(self.cantones),
                                len(self.distritos),
                                len(self.asadasGeo)))
            # Provincias
            for p in self.provincias:
                f.write(struct.pack(FMT_PROVINCIA,
                                    _enc(p["nombre"]),
                                    p["primCanton"],
                                    p["siguiente"]))
            # Cantones
            for c in self.cantones:
                f.write(struct.pack(FMT_CANTON,
                                    _enc(c["nombre"]),
                                    c["primDistrito"],
                                    c["siguienteEnProvincia"]))
            # Distritos
            for d in self.distritos:
                f.write(struct.pack(FMT_DISTRITO,
                                    _enc(d["nombre"]),
                                    d["primAsada"],
                                    d["siguienteEnCanton"]))
            # ASADAS geo
            for a in self.asadasGeo:
                f.write(struct.pack(FMT_ASADA_GEO,
                                    a["idAsada"],
                                    a["posicion"],
                                    a["siguiente"]))

    def cargar(self) -> bool:
        """Carga la estructura desde el archivo binario. Retorna True si tuvo éxito."""
        if not os.path.exists(ARCHIVO_GEOGRAFICO):
            return False
        self.provincias.clear()
        self.cantones.clear()
        self.distritos.clear()
        self.asadasGeo.clear()

        with open(ARCHIVO_GEOGRAFICO, "rb") as f:
            cab = f.read(16)
            if len(cab) < 16:
                return False
            numProv, numCant, numDist, numAsada = struct.unpack("=iiii", cab)

            for _ in range(numProv):
                datos = f.read(TAM_PROVINCIA)
                nombre_b, primCanton, siguiente = struct.unpack(FMT_PROVINCIA, datos)
                self.provincias.append({
                    "nombre": _dec(nombre_b),
                    "primCanton": primCanton,
                    "siguiente": siguiente,
                })
            for _ in range(numCant):
                datos = f.read(TAM_CANTON)
                nombre_b, primDistrito, siguienteEnProvincia = struct.unpack(FMT_CANTON, datos)
                self.cantones.append({
                    "nombre": _dec(nombre_b),
                    "primDistrito": primDistrito,
                    "siguienteEnProvincia": siguienteEnProvincia,
                })
            for _ in range(numDist):
                datos = f.read(TAM_DISTRITO)
                nombre_b, primAsada, siguienteEnCanton = struct.unpack(FMT_DISTRITO, datos)
                self.distritos.append({
                    "nombre": _dec(nombre_b),
                    "primAsada": primAsada,
                    "siguienteEnCanton": siguienteEnCanton,
                })
            for _ in range(numAsada):
                datos = f.read(TAM_ASADA_GEO)
                idAsada, posicion, siguiente = struct.unpack(FMT_ASADA_GEO, datos)
                self.asadasGeo.append({
                    "idAsada": idAsada,
                    "posicion": posicion,
                    "siguiente": siguiente,
                })
        return True

    # ------------------------------------------------------------------ #
    #  Consultas
    # ------------------------------------------------------------------ #

    def listarProvincias(self) -> list[str]:
        """Retorna lista de nombres de provincias."""
        resultado = []
        indice = 0 if self.provincias else -1
        while indice != -1:
            resultado.append(self.provincias[indice]["nombre"])
            indice = self.provincias[indice]["siguiente"]
        return resultado

    def listarCantones(self, nombreProvincia: str) -> list[str]:
        """Retorna cantones de una provincia."""
        iProv = self._buscarProvincia(nombreProvincia)
        if iProv == -1:
            return []
        resultado = []
        iCant = self.provincias[iProv]["primCanton"]
        while iCant != -1:
            resultado.append(self.cantones[iCant]["nombre"])
            iCant = self.cantones[iCant]["siguienteEnProvincia"]
        return resultado

    def listarDistritos(self, nombreProvincia: str, nombreCanton: str) -> list[str]:
        """Retorna distritos de un cantón específico."""
        iProv = self._buscarProvincia(nombreProvincia)
        if iProv == -1:
            return []
        iCant = self._buscarCanton(iProv, nombreCanton)
        if iCant == -1:
            return []
        resultado = []
        iDist = self.cantones[iCant]["primDistrito"]
        while iDist != -1:
            resultado.append(self.distritos[iDist]["nombre"])
            iDist = self.distritos[iDist]["siguienteEnCanton"]
        return resultado

    def listarAsadasEnDistrito(self, nomProv: str, nomCant: str, nomDist: str) -> list[dict]:
        """Retorna lista de {idAsada, posicion} en un distrito, ordenadas por idAsada."""
        iProv = self._buscarProvincia(nomProv)
        if iProv == -1:
            return []
        iCant = self._buscarCanton(iProv, nomCant)
        if iCant == -1:
            return []
        iDist = self._buscarDistrito(iCant, nomDist)
        if iDist == -1:
            return []
        resultado = []
        iAsada = self.distritos[iDist]["primAsada"]
        while iAsada != -1:
            nodo = self.asadasGeo[iAsada]
            resultado.append({"idAsada": nodo["idAsada"], "posicion": nodo["posicion"]})
            iAsada = nodo["siguiente"]
        return sorted(resultado, key=lambda x: x["idAsada"])

    def _buscarProvincia(self, nombre: str) -> int:
        for i, p in enumerate(self.provincias):
            if p["nombre"].strip().lower() == nombre.strip().lower():
                return i
        return -1

    def _buscarCanton(self, iProv: int, nombre: str) -> int:
        iCant = self.provincias[iProv]["primCanton"]
        while iCant != -1:
            if self.cantones[iCant]["nombre"].strip().lower() == nombre.strip().lower():
                return iCant
            iCant = self.cantones[iCant]["siguienteEnProvincia"]
        return -1

    def _buscarDistrito(self, iCant: int, nombre: str) -> int:
        iDist = self.cantones[iCant]["primDistrito"]
        while iDist != -1:
            if self.distritos[iDist]["nombre"].strip().lower() == nombre.strip().lower():
                return iDist
            iDist = self.distritos[iDist]["siguienteEnCanton"]
        return -1
