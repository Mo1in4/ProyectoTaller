"""
main.py
Punto de entrada principal del Sistema de Consulta de ASADAS.

Modos de ejecución:
  python main.py                    -> Interfaz gráfica modo servidor (local)
  python main.py --servidor         -> Servidor TCP sin interfaz
  python main.py --cliente          -> Interfaz gráfica modo cliente
  python main.py --cliente --host X -> Conectar a host específico
  python main.py --actualizar       -> Descargar/actualizar datos (CLI)
  python main.py --actualizar --forzar -> Forzar descarga completa
"""

import argparse
import sys
import os

# Asegurar que el directorio del proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOST_SERVIDOR, PUERTO_SERVIDOR


def main():
    parser = argparse.ArgumentParser(
        description="Sistema Distribuido de Consulta de ASADAS - TEC San Carlos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--servidor", action="store_true",
                       help="Iniciar en modo servidor TCP (sin interfaz gráfica)")
    grupo.add_argument("--cliente", action="store_true",
                       help="Iniciar en modo cliente remoto")
    grupo.add_argument("--actualizar", action="store_true",
                       help="Actualizar datos desde el endpoint (modo CLI)")

    parser.add_argument("--host", default=HOST_SERVIDOR,
                        help=f"Host del servidor (default: {HOST_SERVIDOR})")
    parser.add_argument("--puerto", type=int, default=PUERTO_SERVIDOR,
                        help=f"Puerto del servidor (default: {PUERTO_SERVIDOR})")
    parser.add_argument("--forzar", action="store_true",
                        help="Forzar descarga completa (usado con --actualizar)")

    args = parser.parse_args()

    if args.servidor:
        _iniciarServidor(args.host, args.puerto)
    elif args.cliente:
        _iniciarInterfazCliente(args.host, args.puerto)
    elif args.actualizar:
        _actualizarDatos(args.forzar)
    else:
        # Modo predeterminado: interfaz gráfica como servidor local
        _iniciarInterfazServidor()


def _iniciarServidor(host: str, puerto: int):
    """Inicia el servidor TCP en modo consola."""
    print("=" * 60)
    print("  Sistema ASADAS - Servidor TCP")
    print("  Instituto Tecnológico de Costa Rica")
    print("  Campus San Carlos")
    print("=" * 60)

    from servidor import Servidor
    srv = Servidor()
    srv.iniciar(host, puerto)


def _iniciarInterfazServidor():
    """Inicia la interfaz gráfica en modo servidor (acceso local)."""
    print("[Main] Iniciando interfaz gráfica en modo servidor...")
    from interfaz import iniciarInterfaz
    iniciarInterfaz(modoCliente=False)


def _iniciarInterfazCliente(host: str, puerto: int):
    """Inicia la interfaz gráfica en modo cliente remoto."""
    print(f"[Main] Iniciando interfaz gráfica en modo cliente → {host}:{puerto}")
    from interfaz import iniciarInterfaz
    iniciarInterfaz(modoCliente=True, host=host, puerto=puerto)


def _actualizarDatos(forzar: bool):
    """Ejecuta la actualización de datos desde la línea de comandos."""
    print("=" * 60)
    print("  Sistema ASADAS - Actualización de Datos")
    print("=" * 60)

    from actualizador import verificarYActualizar
    actualizado, listaAsadas = verificarYActualizar(forzar=forzar)

    if actualizado:
        print(f"\n✓ Datos actualizados correctamente: {len(listaAsadas)} ASADAS.")
    else:
        if listaAsadas:
            print("\n✓ Los datos ya están al día.")
        else:
            print("\n✗ No se pudieron obtener los datos del endpoint.")
            sys.exit(1)


if __name__ == "__main__":
    main()
