"""
interfaz.py
Interfaz gráfica del sistema ASADAS usando tkinter.
Combos dependientes para navegación geográfica jerárquica.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import os

from config import HOST_SERVIDOR, PUERTO_SERVIDOR
from arbol_bst import ArbolBST
from archivo_geografico import GestorGeografico
from archivo_principal import leerRegistroPorPosicion
from visualizacion_geo import generarMapa, generarMapaFiltrado
from modelos import Asada


def _asadaATexto(asada: Asada) -> str:
    """Formatea una ASADA para mostrar en la interfaz."""
    return (
        f"{'='*55}\n"
        f"  ID ASADA:       {asada.idAsada}\n"
        f"  Operador:       {asada.operador}\n"
        f"  Tipo Sistema:   {asada.tipoSistema}\n"
        f"  Código DTA:     {asada.codigoDTA}\n"
        f"  Provincia:      {asada.provincia}\n"
        f"  Cantón:         {asada.canton}\n"
        f"  Distrito:       {asada.distrito}\n"
        f"  Teléfono:       {asada.telefono}\n"
        f"  Fax:            {asada.fax}\n"
        f"  Correo:         {asada.correo}\n"
        f"  Coord X:        {asada.coordenadaX:.2f}\n"
        f"  Coord Y:        {asada.coordenadaY:.2f}\n"
        f"{'='*55}\n"
    )


class AplicacionASADAS:
    """Aplicación principal con interfaz gráfica tkinter."""

    def __init__(self, root: tk.Tk, modoCliente: bool = False,
                 hostServidor: str = HOST_SERVIDOR, puertoServidor: int = PUERTO_SERVIDOR):
        self.root = root
        self.modoCliente = modoCliente
        self.hostServidor = hostServidor
        self.puertoServidor = puertoServidor

        # Estructuras locales (modo servidor)
        self.arbol: ArbolBST | None = None
        self.geo: GestorGeografico | None = None

        # Cliente remoto
        self.clienteTcp = None

        self.root.title("Sistema de Consulta de ASADAS - Costa Rica")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        self._configurarEstilo()
        self._construirUI()
        self._inicializarEstructuras()

    def _configurarEstilo(self):
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("TButton", padding=5)
        estilo.configure("Titulo.TLabel", font=("Arial", 14, "bold"))
        estilo.configure("TLabelframe.Label", font=("Arial", 10, "bold"))

    def _construirUI(self):
        """Construye todos los widgets de la interfaz."""
        # Barra superior
        barraTop = ttk.Frame(self.root, padding=10)
        barraTop.pack(fill=tk.X)

        ttk.Label(barraTop, text="Sistema de Consulta de ASADAS de Costa Rica",
                  style="Titulo.TLabel").pack(side=tk.LEFT)

        modoTexto = "MODO CLIENTE (Remoto)" if self.modoCliente else "MODO SERVIDOR (Local)"
        colorModo = "blue" if self.modoCliente else "green"
        self.lblModo = ttk.Label(barraTop, text=modoTexto,
                                 foreground=colorModo, font=("Arial", 9, "bold"))
        self.lblModo.pack(side=tk.RIGHT)

        # Notebook de pestañas
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Pestaña 1: Búsqueda por ID
        tabId = ttk.Frame(nb, padding=10)
        nb.add(tabId, text="Buscar por ID")
        self._construirTabBusquedaId(tabId)

        # Pestaña 2: Consulta geográfica
        tabGeo = ttk.Frame(nb, padding=10)
        nb.add(tabGeo, text="Consulta Geográfica")
        self._construirTabGeografica(tabGeo)

        # Pestaña 3: Actualización (solo servidor)
        if not self.modoCliente:
            tabAct = ttk.Frame(nb, padding=10)
            nb.add(tabAct, text="Actualización de Datos")
            self._construirTabActualizacion(tabAct)

        # Barra de estado
        self.lblEstado = ttk.Label(self.root, text="Listo",
                                   relief=tk.SUNKEN, anchor=tk.W)
        self.lblEstado.pack(fill=tk.X, side=tk.BOTTOM)

    # ------------------------------------------------------------------ #
    #  Pestaña: Búsqueda por ID
    # ------------------------------------------------------------------ #

    def _construirTabBusquedaId(self, parent):
        frBusq = ttk.LabelFrame(parent, text="Búsqueda por Identificador", padding=10)
        frBusq.pack(fill=tk.X, pady=5)

        ttk.Label(frBusq, text="ID ASADA:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.entIdAsada = ttk.Entry(frBusq, width=20)
        self.entIdAsada.grid(row=0, column=1, padx=5)
        self.entIdAsada.bind("<Return>", lambda e: self._buscarPorId())

        ttk.Button(frBusq, text="Buscar", command=self._buscarPorId).grid(
            row=0, column=2, padx=5)
        ttk.Button(frBusq, text="Ver en Mapa", command=self._verAsadaEnMapa).grid(
            row=0, column=3, padx=5)

        frResult = ttk.LabelFrame(parent, text="Resultado", padding=10)
        frResult.pack(fill=tk.BOTH, expand=True, pady=5)

        self.txtResultadoId = scrolledtext.ScrolledText(
            frResult, height=20, font=("Courier", 10), state=tk.DISABLED)
        self.txtResultadoId.pack(fill=tk.BOTH, expand=True)

        self._asadaActual: Asada | None = None

    def _buscarPorId(self):
        texto = self.entIdAsada.get().strip()
        if not texto:
            messagebox.showwarning("Entrada inválida", "Ingrese un ID de ASADA.")
            return
        try:
            idAsada = int(texto)
        except ValueError:
            messagebox.showerror("Error", "El ID debe ser un número entero.")
            return

        self._setEstado(f"Buscando ASADA {idAsada}...")
        self._asadaActual = None

        if self.modoCliente:
            self._buscarPorIdRemoto(idAsada)
        else:
            self._buscarPorIdLocal(idAsada)

    def _buscarPorIdLocal(self, idAsada: int):
        if not self.arbol:
            messagebox.showerror("Error", "Las estructuras no están cargadas.")
            return
        nodo = self.arbol.buscar(idAsada)
        if nodo is None:
            self._mostrarResultadoId(None, idAsada)
            return
        asada = leerRegistroPorPosicion(nodo.posicion)
        self._asadaActual = asada
        self._mostrarResultadoId(asada, idAsada)

    def _buscarPorIdRemoto(self, idAsada: int):
        def tarea():
            from cliente import ClienteASADAS
            with ClienteASADAS(self.hostServidor, self.puertoServidor) as cli:
                if not cli.conexion:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", "No se pudo conectar al servidor."))
                    return
                datos = cli.buscarPorId(idAsada)
            if datos:
                asada = Asada()
                for clave, valor in datos.items():
                    if hasattr(asada, clave):
                        setattr(asada, clave, valor)
                self._asadaActual = asada
                self.root.after(0, lambda: self._mostrarResultadoId(asada, idAsada))
            else:
                self.root.after(0, lambda: self._mostrarResultadoId(None, idAsada))

        threading.Thread(target=tarea, daemon=True).start()

    def _mostrarResultadoId(self, asada: Asada | None, idBuscado: int):
        self.txtResultadoId.config(state=tk.NORMAL)
        self.txtResultadoId.delete("1.0", tk.END)
        if asada:
            self.txtResultadoId.insert(tk.END, _asadaATexto(asada))
            self._setEstado(f"ASADA {idBuscado} encontrada.")
        else:
            self.txtResultadoId.insert(tk.END, f"ASADA con ID {idBuscado} no encontrada.\n")
            self._setEstado(f"ASADA {idBuscado} no encontrada.")
        self.txtResultadoId.config(state=tk.DISABLED)

    def _verAsadaEnMapa(self):
        if not self._asadaActual:
            messagebox.showinfo("Sin selección", "Primero busque una ASADA.")
            return
        self._setEstado("Generando mapa...")
        threading.Thread(
            target=lambda: generarMapa([self._asadaActual],
                                       titulo=f"ASADA {self._asadaActual.idAsada}"),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #
    #  Pestaña: Consulta Geográfica
    # ------------------------------------------------------------------ #

    def _construirTabGeografica(self, parent):
        frCombos = ttk.LabelFrame(parent, text="Filtro por División Política", padding=10)
        frCombos.pack(fill=tk.X, pady=5)

        # Provincia
        ttk.Label(frCombos, text="Provincia:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.cmbProvincia = ttk.Combobox(frCombos, state="readonly", width=25)
        self.cmbProvincia.grid(row=0, column=1, padx=5)
        self.cmbProvincia.bind("<<ComboboxSelected>>", self._onProvinciaSeleccionada)

        # Cantón
        ttk.Label(frCombos, text="Cantón:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.cmbCanton = ttk.Combobox(frCombos, state="disabled", width=25)
        self.cmbCanton.grid(row=0, column=3, padx=5)
        self.cmbCanton.bind("<<ComboboxSelected>>", self._onCantonSeleccionado)

        # Distrito
        ttk.Label(frCombos, text="Distrito:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.cmbDistrito = ttk.Combobox(frCombos, state="disabled", width=25)
        self.cmbDistrito.grid(row=1, column=1, padx=5)
        self.cmbDistrito.bind("<<ComboboxSelected>>", self._onDistritoSeleccionado)

        # Botones de acción
        frBotones = ttk.Frame(frCombos)
        frBotones.grid(row=1, column=2, columnspan=2, padx=5)
        ttk.Button(frBotones, text="Listar ASADAS",
                   command=self._listarAsadasDistrito).pack(side=tk.LEFT, padx=3)
        ttk.Button(frBotones, text="Ver en Mapa",
                   command=self._verFiltradoEnMapa).pack(side=tk.LEFT, padx=3)
        ttk.Button(frBotones, text="Ver Mapa Todo",
                   command=self._verMapaCompleto).pack(side=tk.LEFT, padx=3)

        # Lista de resultados
        frLista = ttk.LabelFrame(parent, text="ASADAS encontradas", padding=10)
        frLista.pack(fill=tk.BOTH, expand=True, pady=5)

        columnas = ("idAsada", "operador", "tipoSistema", "telefono")
        self.tblAsadas = ttk.Treeview(frLista, columns=columnas, show="headings", height=15)
        self.tblAsadas.heading("idAsada", text="ID")
        self.tblAsadas.heading("operador", text="Operador")
        self.tblAsadas.heading("tipoSistema", text="Tipo Sistema")
        self.tblAsadas.heading("telefono", text="Teléfono")
        self.tblAsadas.column("idAsada", width=60)
        self.tblAsadas.column("operador", width=280)
        self.tblAsadas.column("tipoSistema", width=120)
        self.tblAsadas.column("telefono", width=100)

        scrollY = ttk.Scrollbar(frLista, orient=tk.VERTICAL, command=self.tblAsadas.yview)
        self.tblAsadas.configure(yscrollcommand=scrollY.set)
        self.tblAsadas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollY.pack(side=tk.RIGHT, fill=tk.Y)

        self.tblAsadas.bind("<Double-1>", self._onDobleClicAsada)
        self._asadasGeoActuales: list[dict] = []

    def _cargarProvincias(self):
        if self.modoCliente:
            def tarea():
                from cliente import ClienteASADAS
                with ClienteASADAS(self.hostServidor, self.puertoServidor) as cli:
                    if not cli.conexion:
                        return
                    provs = cli.listarProvincias()
                self.root.after(0, lambda: self._llenarComboProvincias(provs))
            threading.Thread(target=tarea, daemon=True).start()
        else:
            if self.geo:
                self._llenarComboProvincias(self.geo.listarProvincias())

    def _llenarComboProvincias(self, provincias: list[str]):
        self.cmbProvincia["values"] = sorted(provincias)
        self.cmbProvincia.set("")

    def _onProvinciaSeleccionada(self, _event=None):
        provincia = self.cmbProvincia.get()
        self.cmbCanton.set("")
        self.cmbDistrito.set("")
        self.cmbCanton["state"] = "disabled"
        self.cmbDistrito["state"] = "disabled"

        if self.modoCliente:
            def tarea():
                from cliente import ClienteASADAS
                with ClienteASADAS(self.hostServidor, self.puertoServidor) as cli:
                    if not cli.conexion:
                        return
                    cantones = cli.listarCantones(provincia)
                self.root.after(0, lambda: self._llenarComboCantones(cantones))
            threading.Thread(target=tarea, daemon=True).start()
        else:
            if self.geo:
                self._llenarComboCantones(self.geo.listarCantones(provincia))

    def _llenarComboCantones(self, cantones: list[str]):
        self.cmbCanton["values"] = sorted(cantones)
        self.cmbCanton["state"] = "readonly"

    def _onCantonSeleccionado(self, _event=None):
        provincia = self.cmbProvincia.get()
        canton = self.cmbCanton.get()
        self.cmbDistrito.set("")
        self.cmbDistrito["state"] = "disabled"

        if self.modoCliente:
            def tarea():
                from cliente import ClienteASADAS
                with ClienteASADAS(self.hostServidor, self.puertoServidor) as cli:
                    if not cli.conexion:
                        return
                    distritos = cli.listarDistritos(provincia, canton)
                self.root.after(0, lambda: self._llenarComboDistritos(distritos))
            threading.Thread(target=tarea, daemon=True).start()
        else:
            if self.geo:
                self._llenarComboDistritos(self.geo.listarDistritos(provincia, canton))

    def _llenarComboDistritos(self, distritos: list[str]):
        self.cmbDistrito["values"] = sorted(distritos)
        self.cmbDistrito["state"] = "readonly"

    def _onDistritoSeleccionado(self, _event=None):
        pass  # La carga se hace al presionar "Listar ASADAS"

    def _listarAsadasDistrito(self):
        provincia = self.cmbProvincia.get()
        canton = self.cmbCanton.get()
        distrito = self.cmbDistrito.get()

        if not provincia or not canton or not distrito:
            messagebox.showwarning("Selección incompleta",
                                   "Seleccione provincia, cantón y distrito.")
            return

        self._setEstado("Cargando ASADAS del distrito...")

        if self.modoCliente:
            def tarea():
                from cliente import ClienteASADAS
                with ClienteASADAS(self.hostServidor, self.puertoServidor) as cli:
                    if not cli.conexion:
                        return
                    asadas = cli.listarAsadasEnDistrito(provincia, canton, distrito)
                self.root.after(0, lambda: self._llenarTablaAsadas(asadas))
            threading.Thread(target=tarea, daemon=True).start()
        else:
            if self.geo:
                refs = self.geo.listarAsadasEnDistrito(provincia, canton, distrito)
                asadas = []
                for ref in refs:
                    a = leerRegistroPorPosicion(ref["posicion"])
                    if a:
                        asadas.append({
                            "idAsada": a.idAsada, "operador": a.operador,
                            "tipoSistema": a.tipoSistema, "telefono": a.telefono,
                            "provincia": a.provincia, "canton": a.canton,
                            "distrito": a.distrito, "correo": a.correo,
                            "coordenadaX": a.coordenadaX, "coordenadaY": a.coordenadaY,
                        })
                self._llenarTablaAsadas(asadas)

    def _llenarTablaAsadas(self, asadas: list[dict]):
        for item in self.tblAsadas.get_children():
            self.tblAsadas.delete(item)
        self._asadasGeoActuales = asadas
        for a in asadas:
            self.tblAsadas.insert("", tk.END, values=(
                a.get("idAsada", ""),
                a.get("operador", ""),
                a.get("tipoSistema", ""),
                a.get("telefono", ""),
            ))
        self._setEstado(f"{len(asadas)} ASADAS encontradas.")

    def _onDobleClicAsada(self, _event=None):
        """Al hacer doble clic en una fila, muestra detalles."""
        seleccion = self.tblAsadas.selection()
        if not seleccion:
            return
        indice = self.tblAsadas.index(seleccion[0])
        if indice < len(self._asadasGeoActuales):
            datos = self._asadasGeoActuales[indice]
            idAsada = datos.get("idAsada")
            if idAsada:
                self.entIdAsada.delete(0, tk.END)
                self.entIdAsada.insert(0, str(idAsada))
                self._buscarPorId()

    def _verFiltradoEnMapa(self):
        provincia = self.cmbProvincia.get()
        canton = self.cmbCanton.get()
        distrito = self.cmbDistrito.get()
        if not provincia:
            messagebox.showwarning("Sin filtro", "Seleccione al menos una provincia.")
            return
        self._setEstado("Generando mapa filtrado...")
        from archivo_principal import leerTodosLosRegistros

        def tarea():
            todas = leerTodosLosRegistros()
            generarMapaFiltrado(todas, provincia, canton, distrito)
        threading.Thread(target=tarea, daemon=True).start()

    def _verMapaCompleto(self):
        self._setEstado("Generando mapa completo (puede tardar)...")
        from archivo_principal import leerTodosLosRegistros

        def tarea():
            todas = leerTodosLosRegistros()
            generarMapa(todas, titulo="Todas las ASADAS de Costa Rica")
        threading.Thread(target=tarea, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Pestaña: Actualización de Datos
    # ------------------------------------------------------------------ #

    def _construirTabActualizacion(self, parent):
        frAcc = ttk.LabelFrame(parent, text="Control de Datos", padding=10)
        frAcc.pack(fill=tk.X, pady=5)

        ttk.Button(frAcc, text="Verificar y Actualizar (Incremental)",
                   command=self._actualizarIncremental).pack(side=tk.LEFT, padx=5)
        ttk.Button(frAcc, text="Forzar Descarga Completa",
                   command=self._actualizarForzado).pack(side=tk.LEFT, padx=5)
        ttk.Button(frAcc, text="Recargar Estructuras en Memoria",
                   command=self._recargarEstructuras).pack(side=tk.LEFT, padx=5)

        frLog = ttk.LabelFrame(parent, text="Log de Actualización", padding=10)
        frLog.pack(fill=tk.BOTH, expand=True, pady=5)

        self.txtLog = scrolledtext.ScrolledText(
            frLog, height=20, font=("Courier", 9), state=tk.DISABLED)
        self.txtLog.pack(fill=tk.BOTH, expand=True)

    def _logActualizacion(self, mensaje: str):
        self.txtLog.config(state=tk.NORMAL)
        self.txtLog.insert(tk.END, mensaje + "\n")
        self.txtLog.see(tk.END)
        self.txtLog.config(state=tk.DISABLED)

    def _actualizarIncremental(self):
        self._setEstado("Verificando cambios...")
        self._logActualizacion("[INFO] Iniciando verificación incremental...")
        threading.Thread(target=self._tareaActualizacion, args=(False,), daemon=True).start()

    def _actualizarForzado(self):
        if not messagebox.askyesno("Confirmar",
                                   "¿Desea forzar la descarga completa de todos los datos?"):
            return
        self._setEstado("Descargando datos completos...")
        self._logActualizacion("[INFO] Iniciando descarga forzada...")
        threading.Thread(target=self._tareaActualizacion, args=(True,), daemon=True).start()

    def _tareaActualizacion(self, forzar: bool):
        import io
        import sys
        from actualizador import verificarYActualizar

        # Capturar prints del actualizador
        captura = io.StringIO()
        sys.stdout = captura
        try:
            actualizado, _ = verificarYActualizar(forzar=forzar)
        finally:
            sys.stdout = sys.__stdout__

        salida = captura.getvalue()
        for linea in salida.splitlines():
            self.root.after(0, lambda l=linea: self._logActualizacion(l))

        if actualizado:
            self.root.after(0, lambda: self._logActualizacion("[OK] Actualización completada."))
            self.root.after(0, self._recargarEstructuras)
        else:
            self.root.after(0, lambda: self._logActualizacion("[INFO] Sin cambios necesarios."))
        self.root.after(0, lambda: self._setEstado("Listo"))

    def _recargarEstructuras(self):
        self._inicializarEstructuras()
        self._logActualizacion("[OK] Estructuras recargadas en memoria.")
        messagebox.showinfo("Recargado", "Las estructuras se recargaron correctamente.")

    # ------------------------------------------------------------------ #
    #  Inicialización de estructuras
    # ------------------------------------------------------------------ #

    def _inicializarEstructuras(self):
        """Carga las estructuras de datos desde los archivos binarios."""
        if self.modoCliente:
            self._setEstado(f"Modo cliente: {self.hostServidor}:{self.puertoServidor}")
        else:
            self.arbol = ArbolBST()
            self.geo = GestorGeografico()
            arbolOk = self.arbol.cargar()
            geoOk = self.geo.cargar()
            if arbolOk and geoOk:
                total = len(self.arbol.nodos)
                self._setEstado(f"Estructuras cargadas: {total} ASADAS en árbol.")
            else:
                self._setEstado("Datos no encontrados. Use 'Actualización de Datos'.")

        self._cargarProvincias()

    def _setEstado(self, mensaje: str):
        self.lblEstado.config(text=mensaje)


def iniciarInterfaz(modoCliente: bool = False,
                    host: str = HOST_SERVIDOR,
                    puerto: int = PUERTO_SERVIDOR):
    """Función principal para lanzar la interfaz gráfica."""
    root = tk.Tk()
    app = AplicacionASADAS(root, modoCliente=modoCliente,
                           hostServidor=host, puertoServidor=puerto)
    root.mainloop()
