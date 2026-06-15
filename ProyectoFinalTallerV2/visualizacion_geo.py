"""
visualizacion_geo.py
Genera mapas HTML con OpenStreetMap usando Folium.
Convierte coordenadas CRTM05 (EPSG:5367) → WGS84 (EPSG:4326) con pyproj.
"""

import os
import webbrowser
from modelos import Asada
from config import ARCHIVO_MAPA


def _convertirCRTM05aWGS84(coordX: float, coordY: float) -> tuple[float, float]:
    """
    Convierte coordenadas planas CRTM05 a latitud/longitud WGS84.
    Retorna (latitud, longitud).
    """
    try:
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:5367", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(coordX, coordY)
        return lat, lon
    except ImportError:
        print("[Mapa] pyproj no está instalado. Usando aproximación manual.")
        # Aproximación para Costa Rica (no recomendada para producción)
        latRef = 9.7489
        lonRef = -83.7534
        escala = 111319.0  # metros por grado aproximado
        lat = latRef + (coordY - 1084000) / escala
        lon = lonRef + (coordX - 500000) / (escala * 0.98)
        return lat, lon
    except Exception as e:
        print(f"[Mapa] Error en conversión de coordenadas: {e}")
        return 0.0, 0.0


def generarMapa(listaAsadas: list[Asada],
                titulo: str = "ASADAS de Costa Rica") -> str:
    """
    Genera un archivo HTML con el mapa de las ASADAS y lo abre en el navegador.
    Retorna la ruta del archivo HTML generado.
    """
    try:
        import folium
    except ImportError:
        print("[Mapa] folium no está instalado. Instale con: pip install folium")
        return ""

    os.makedirs(os.path.dirname(ARCHIVO_MAPA), exist_ok=True)

    # Centro de Costa Rica
    mapa = folium.Map(
        location=[9.7489, -83.7534],
        zoom_start=8,
        tiles="OpenStreetMap",
    )

    # Título como control HTML
    tituloCss = f"""
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                background: white; padding: 8px 16px; border-radius: 6px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3); z-index: 9999;
                font-family: Arial, sans-serif; font-weight: bold; font-size: 15px;">
        {titulo}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(tituloCss))

    marcadoresValidos = 0
    for asada in listaAsadas:
        if asada.coordenadaX == 0.0 and asada.coordenadaY == 0.0:
            continue

        lat, lon = _convertirCRTM05aWGS84(asada.coordenadaX, asada.coordenadaY)

        # Validar que las coordenadas estén dentro de Costa Rica
        if not (7.0 <= lat <= 11.5 and -86.0 <= lon <= -82.5):
            continue

        popup_texto = f"""
        <b>ID ASADA:</b> {asada.idAsada}<br>
        <b>Operador:</b> {asada.operador}<br>
        <b>Provincia:</b> {asada.provincia}<br>
        <b>Cantón:</b> {asada.canton}<br>
        <b>Distrito:</b> {asada.distrito}<br>
        <b>Teléfono:</b> {asada.telefono}<br>
        <b>Correo:</b> {asada.correo}<br>
        <b>Tipo Sistema:</b> {asada.tipoSistema}
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_texto, max_width=300),
            tooltip=f"ASADA {asada.idAsada}: {asada.operador}",
            icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
        ).add_to(mapa)

        marcadoresValidos += 1

    mapa.save(ARCHIVO_MAPA)
    print(f"[Mapa] Mapa generado con {marcadoresValidos} marcadores: {ARCHIVO_MAPA}")

    # Abrir automáticamente en el navegador predeterminado
    rutaAbsoluta = os.path.abspath(ARCHIVO_MAPA)
    webbrowser.open(f"file://{rutaAbsoluta}")

    return ARCHIVO_MAPA


def generarMapaFiltrado(listaAsadas: list[Asada],
                        provincia: str = "",
                        canton: str = "",
                        distrito: str = "") -> str:
    """Genera un mapa filtrado por división política."""
    filtradas = listaAsadas
    if provincia:
        filtradas = [a for a in filtradas if a.provincia.strip().lower() == provincia.strip().lower()]
    if canton:
        filtradas = [a for a in filtradas if a.canton.strip().lower() == canton.strip().lower()]
    if distrito:
        filtradas = [a for a in filtradas if a.distrito.strip().lower() == distrito.strip().lower()]

    tituloMapa = "ASADAS"
    if provincia:
        tituloMapa += f" - {provincia}"
    if canton:
        tituloMapa += f" / {canton}"
    if distrito:
        tituloMapa += f" / {distrito}"

    return generarMapa(filtradas, titulo=tituloMapa)
