# Sistema Distribuido de Consulta de ASADAS - Costa Rica
## Taller de Programación IC1803 — TEC San Carlos

---

## Estructura del Proyecto

```
asadas_project/
├── main.py                  # Punto de entrada principal
├── config.py                # Configuración global y constantes
├── modelos.py               # Estructuras de datos (Asada, NodoArbol, etc.)
├── archivo_principal.py     # Archivo binario principal de registros (acceso directo)
├── arbol_bst.py             # Árbol Binario de Búsqueda persistente (índice por id_Asada)
├── archivo_geografico.py    # Listas enlazadas jerárquicas (Provincia→Cantón→Distrito→ASADA)
├── actualizador.py          # Descarga y actualización incremental desde ARESEP
├── servidor.py              # Servidor TCP/IP con hilos concurrentes
├── cliente.py               # Cliente TCP para consultas remotas
├── interfaz.py              # Interfaz gráfica tkinter
├── visualizacion_geo.py     # Mapas con Folium + conversión CRTM05→WGS84
├── requirements.txt         # Dependencias pip
└── data/                    # Archivos binarios generados (creados automáticamente)
    ├── asadas.bin           # Archivo principal de registros
    ├── arbol_bst.bin        # Árbol BST serializado
    ├── geografico.bin       # Estructura geográfica enlazada
    └── metadata.json        # Metadata de sincronización
```

---

## Instalación

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. (Opcional) Verificar instalación
python -c "import folium; import pyproj; print('Dependencias OK')"
```

---

## Modos de Ejecución

### Modo 1: Interfaz Gráfica (Servidor Local)
```bash
python main.py
```
Abre la interfaz completa con acceso local a los datos.
Desde aquí se puede actualizar la información del endpoint ARESEP.

### Modo 2: Servidor TCP (sin interfaz)
```bash
python main.py --servidor
# Con host/puerto específico:
python main.py --servidor --host 0.0.0.0 --puerto 9000
```
Inicia el servidor TCP que atiende clientes remotos con hilos independientes.
**Solo el servidor puede actualizar los datos.**

### Modo 3: Cliente Remoto
```bash
python main.py --cliente --host 192.168.1.100
# Con puerto específico:
python main.py --cliente --host 192.168.1.100 --puerto 9000
```
Abre la interfaz gráfica conectada a un servidor remoto.

### Modo 4: Actualización CLI
```bash
# Actualización incremental (solo si hay cambios en el endpoint)
python main.py --actualizar

# Forzar descarga completa
python main.py --actualizar --forzar
```

---

## Arquitectura Técnica

### Archivo Binario Principal (`asadas.bin`)
- Registros de **tamaño fijo** con padding de cadenas UTF-8
- Acceso directo `O(1)` por posición en bytes
- Tamaño de registro: calculado con `struct.calcsize()`

### Árbol BST (`arbol_bst.bin`)
- Indexado por `id_Asada`
- Almacenado como arreglo de nodos con **punteros lógicos** (índices)
- Búsqueda `O(log n)` promedio
- Cada nodo: `{idAsada, posición_en_archivo_principal, hijo_izq, hijo_der}`

### Listas Enlazadas Geográficas (`geografico.bin`)
- Jerarquía: Provincia → Cantón → Distrito → ASADAS
- Punteros lógicos (índices) entre nodos
- Combos dependientes en la interfaz

### Servidor TCP
- **Protocolo propio**: mensajes JSON con cabecera de 4 bytes de longitud
- Un **hilo independiente** por cliente conectado
- Estructuras protegidas con `threading.Lock` para acceso concurrente

### Visualización Geográfica
- Conversión CRTM05 → WGS84 con `pyproj`
- Mapas HTML interactivos con `folium` + OpenStreetMap
- Abiertos automáticamente con el navegador predeterminado

---

## Protocolo de Comunicación (Sockets)

Las solicitudes y respuestas siguen este formato:

**Cliente → Servidor:**
```json
{
  "accion": "buscarPorId",
  "idAsada": 42
}
```

**Acciones disponibles:**
- `ping` — verificar conexión
- `buscarPorId` — buscar por `idAsada`
- `listarProvincias` — obtener lista de provincias
- `listarCantones` — requiere `provincia`
- `listarDistritos` — requiere `provincia` y `canton`
- `listarAsadasDistrito` — requiere `provincia`, `canton` y `distrito`

**Servidor → Cliente:**
```json
{
  "estado": "ok",
  "asada": { ... }
}
```

---

## Coordenadas CRTM05 → WGS84

Costa Rica utiliza **CRTM05 (EPSG:5367)** como sistema cartográfico oficial.
OpenStreetMap usa **WGS84 (EPSG:4326)** (latitud/longitud).

La conversión se realiza con `pyproj`:
```python
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:5367", "EPSG:4326", always_xy=True)
lon, lat = transformer.transform(coordenadaX, coordenadaY)
```

---

## Notación de Código

Se utiliza **lowerCamelCase** para variables y funciones:
- Variables: `idAsada`, `primerCanton`, `nombreDistrito`
- Funciones: `buscarPorId()`, `listarProvincias()`, `guardarRegistros()`
- Clases: **UpperCamelCase**: `ArbolBST`, `GestorGeografico`, `ManejadorCliente`
