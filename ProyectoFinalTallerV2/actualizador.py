"""
actualizador.py
Descarga datos del endpoint ARESEP y gestiona la actualización incremental
comparando la fecha de modificación remota con la registrada localmente.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from modelos import Asada
from config import ENDPOINT_URL, ARCHIVO_METADATA


def _cargarMetadata() -> dict:
    """Carga la metadata local de sincronización."""
    if not os.path.exists(ARCHIVO_METADATA):
        return {"ultimaModificacion": None, "totalRegistros": 0}
    try:
        with open(ARCHIVO_METADATA, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"ultimaModificacion": None, "totalRegistros": 0}


def _guardarMetadata(fechaModificacion: str, totalRegistros: int) -> None:
    """Guarda la metadata de la última sincronización exitosa."""
    os.makedirs(os.path.dirname(ARCHIVO_METADATA), exist_ok=True)
    datos = {
        "ultimaModificacion": fechaModificacion,
        "totalRegistros": totalRegistros,
        "ultimaSincronizacion": datetime.now().isoformat(),
    }
    with open(ARCHIVO_METADATA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def _descargarDatos() -> tuple[list[dict], str]:
    """
    Descarga los datos JSON del endpoint de ARESEP.
    Retorna (lista_de_registros, fecha_modificacion).
    """
    try:
        print(f"[Actualizador] Conectando a: {ENDPOINT_URL}")
        print(f"[Actualizador] Esto puede tardar hasta 2 minutos, por favor espere...")

        req = urllib.request.Request(
            ENDPOINT_URL,
            headers={
                "Accept": "application/json",
                "User-Agent": "ASADAS-Sistema/1.0 (TEC)",
            }
        )

        # Timeout alto porque el endpoint de ARESEP es lento
        with urllib.request.urlopen(req, timeout=120) as respuesta:
            fechaModificacion = respuesta.headers.get("Last-Modified", "")
            print(f"[Actualizador] Conexión establecida. Descargando datos...")
            contenido = respuesta.read().decode("utf-8", errors="replace")

        print(f"[Actualizador] Datos recibidos ({len(contenido)} bytes). Procesando...")

        # El endpoint de ARESEP puede devolver JSON envuelto en un callback
        # o con estructura {"d": [...]}
        contenidoLimpio = contenido.strip()

        # Intentar parsear directamente
        try:
            datos = json.loads(contenidoLimpio)
        except json.JSONDecodeError:
            # A veces viene envuelto como: callback({...}) o similar
            inicio = contenidoLimpio.find('{')
            if inicio == -1:
                inicio = contenidoLimpio.find('[')
            if inicio != -1:
                datos = json.loads(contenidoLimpio[inicio:])
            else:
                print("[Actualizador] No se pudo parsear la respuesta JSON.")
                return [], ""

        # El endpoint puede devolver la lista directamente o envuelta
        if isinstance(datos, list):
            registros = datos
        elif isinstance(datos, dict):
            # Buscar la clave que contiene la lista de registros
            for clave in ("d", "value", "data", "resultado", "asadas",
                          "ObtenerInformacionUbicacionAساdasResult"):
                if clave in datos and isinstance(datos[clave], list):
                    registros = datos[clave]
                    break
            else:
                # Tomar el primer valor que sea lista
                registros = []
                for val in datos.values():
                    if isinstance(val, list) and len(val) > 0:
                        registros = val
                        break
        else:
            registros = []

        print(f"[Actualizador] Descargados {len(registros)} registros.")
        return registros, fechaModificacion

    except urllib.error.URLError as e:
        print(f"[Actualizador] Error de red: {e}")
        return [], ""
    except json.JSONDecodeError as e:
        print(f"[Actualizador] Error al parsear JSON: {e}")
        return [], ""
    except Exception as e:
        print(f"[Actualizador] Error inesperado: {e}")
        return [], ""


def verificarYActualizar(forzar: bool = False) -> tuple[bool, list[Asada]]:
    """
    Verifica si hay cambios en el endpoint y actualiza las estructuras si es necesario.

    Parámetros:
        forzar: Si True, descarga y reconstruye sin comparar fechas.

    Retorna:
        (huboActualizacion, listaAsadas)
    """
    metadata = _cargarMetadata()
    registrosJson, fechaRemota = _descargarDatos()

    if not registrosJson:
        print("[Actualizador] No se obtuvieron datos del endpoint.")
        return False, []

    # Comparar fecha de modificación
    if not forzar and fechaRemota and fechaRemota == metadata.get("ultimaModificacion"):
        print("[Actualizador] Los datos no han cambiado. No se requiere actualización.")
        return False, []

    print("[Actualizador] Cambios detectados. Procesando registros...")

    # Convertir a objetos Asada
    listaAsadas: list[Asada] = []
    for registro in registrosJson:
        try:
            asada = Asada.desdeJson(registro)
            listaAsadas.append(asada)
        except Exception as e:
            print(f"[Actualizador] Error procesando registro: {e}")

    # Ordenar por idAsada para que el árbol BST quede más balanceado
    listaAsadas.sort(key=lambda a: a.idAsada)

    # Persistir archivos binarios
    from archivo_principal import guardarRegistros
    from arbol_bst import ArbolBST
    from archivo_geografico import GestorGeografico

    print("[Actualizador] Guardando archivo principal de registros...")
    guardarRegistros(listaAsadas)

    print("[Actualizador] Construyendo y guardando árbol BST...")
    arbol = ArbolBST()
    arbol.construirDesdeAsadas(listaAsadas)
    arbol.guardar()

    print("[Actualizador] Construyendo y guardando estructura geográfica...")
    geo = GestorGeografico()
    geo.construir(listaAsadas)
    geo.guardar()

    # Actualizar metadata
    _guardarMetadata(fechaRemota, len(listaAsadas))
    print(f"[Actualizador] Actualización completada. {len(listaAsadas)} ASADAS procesadas.")

    return True, listaAsadas
