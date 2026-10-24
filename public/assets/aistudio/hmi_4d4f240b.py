import csv
import hashlib
import json
import os
import random
import re
import socket
import threading
import time
import uuid
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .client import MIP1000Client

# Intentar importar OpenCV y PIL para la visualización RTSP real
try:
    import cv2
    from PIL import Image, ImageTk
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    Image = ImageTk = None
    OPENCV_AVAILABLE = False

# Dependencias opcionales para SIP / Red (con fallback nativo si no están instaladas)
try:
    import pjsua2 as pj  # type: ignore[import-not-found]
    PJSUA2_AVAILABLE = True
except ImportError:
    pj = None
    PJSUA2_AVAILABLE = False

try:
    import pyshark
    PYSHARK_AVAILABLE = True
except ImportError:
    pyshark = None
    PYSHARK_AVAILABLE = False

try:
    from scapy.all import sniff, IP, IPv6, UDP, TCP, Raw
    SCAPY_AVAILABLE = True
except ImportError:
    sniff = IP = IPv6 = UDP = TCP = Raw = None
    SCAPY_AVAILABLE = False

if PJSUA2_AVAILABLE:
    class _HmiSipCall(pj.Call):
        """Llamada PJSUA2; notifica a Tkinter usando una cola segura entre hilos."""
        def __init__(self, account, endpoint, notify, call_id=-1):
            super().__init__(account, call_id)
            self._endpoint = endpoint
            self._notify = notify

        def onCallState(self, prm):
            try:
                info = self.getInfo()
                state = str(info.stateText)
                self._notify("sip_call_status", state)
                if info.state == pj.PJSIP_INV_STATE_DISCONNECTED:
                    self._notify("sip_call_disconnected", state)
            except Exception as exc:
                self._notify("sip_tool_status", f"No se pudo leer el estado de la llamada: {exc}")

        def onCallMediaState(self, prm):
            try:
                info = self.getInfo()
                manager = self._endpoint.audDevManager()
                for index, media in enumerate(info.media):
                    if media.type == pj.PJMEDIA_TYPE_AUDIO and media.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                        audio = self.getAudioMedia(index)
                        manager.getCaptureDevMedia().startTransmit(audio)
                        audio.startTransmit(manager.getPlaybackDevMedia())
                        self._notify("sip_tool_status", "Audio conectado: micrófono y altavoz activos.")
            except Exception as exc:
                self._notify("sip_tool_status", f"Señalización activa, pero no se pudo enrutar el audio: {exc}")

    class _HmiSipAccount(pj.Account):
        def __init__(self, notify):
            super().__init__()
            self._notify = notify

        def onRegState(self, prm):
            try:
                info = self.getInfo()
                self._notify("sip_register_status", (int(info.regStatus), str(info.regStatusText)))
            except Exception as exc:
                self._notify("sip_register_status", (0, str(exc)))

TEMPLATES_FILE = "user_templates.json"

I18N: Dict[str, Dict[str, str]] = {
    "ES": {
        "app_title": "Intelbras MIP 1000 IP - Consola de Integracion y Control (Protocolo V2) V.2.0",
        "conn_frame": " 1. Conexion TCP RAW (MIP 1000 IP) y Puertos RTSP de Camaras ",
        "ip_lbl": "IP del MIP:",
        "port_lbl": "Puerto:",
        "login_lbl": "Login:",
        "pass_lbl": "Senha:",
        "fmt_lbl": "Header:",
        "lang_lbl": "Idioma:",
        "btn_connect": "Conectar",
        "btn_disconnect": "Desconectar",
        "st_disc": "[DESCONECTADO]",
        "st_conn": "[CONECTADO]",
        "rtsp1_lbl": "Cam 1 RTSP:",
        "rtsp2_lbl": "Cam 2 RTSP:",
        "btn_r1_conn": "Ver Cam 1",
        "btn_r1_disc": "Detener",
        "btn_r2_conn": "Ver Cam 2",
        "btn_r2_disc": "Detener",
        "tab_dashboard": "Dashboard",
        "tab_create": "Crear Usuario",
        "tab_edit": "Editar Usuario",
        "tab_tpl": "Plantillas",
        "tab_search": "Consultas",
        "tab_events": "Eventos por Apto",
        "tab_online": "Online",
        "tab_ai": "Analisis IA",
        "tab_detail": "Detalle Medios",
        "tab_sip_network": "SIP / Red",
        "asr_box": " Accionar Salida Remotamente - ASR (0x18) ",
        "dev_addr": "Direccion Dispositivo (1=MIP, 2..24=RS485):",
        "out_num": "Salida / Rele (1..2 MIP/XPE/XLT, 1..8 REMOTE):",
        "btn_open_door": "ABRIR PUERTA / ACTIVAR RELE AHORA",
        "cfg_box": " Configuraciones Rapidas del MIP (0x08 / 0x22 / 0x32) ",
        "btn_sync_time": "Sincronizar Fecha y Hora con este PC (CD - 0x08)",
        "btn_get_uid": "Consultar UID, MAC y Firmware (UID - 0x32)",
        "idle_msg": "Mensaje Display (max 20 chars):",
        "btn_set_msg": "Actualizar Mensaje de Descanso (MG - 0x22)",
        "vs_box": " Estado de Base de Datos - Verificar Sincronismo (VS - 0x17) ",
        "btn_get_vs": "Actualizar Contadores del MIP",
        "u_personal": " 1. Datos Personales y Ubicacion (MU - 0x01) ",
        "u_access": " 2. Permisos, Contrasenas y Dispositivos Liberados (1..24) ",
        "u_media": " 3. Vehiculo, Tarjeta RFID (XID) y Control Remoto (XTR) ",
        "btn_send_all": "ENVIAR NUEVO USUARIO AL MIP (1-CLIC)",
        "btn_goto_edit": "Ir a Editar Usuario",
        "btn_save_changes": "Guardar Cambios en el MIP (ALTERAR)",
        "btn_clear_form": "Limpiar Formulario",
        "btn_read_tag_form": "Capturar TAG en MIP (0x1C)",
        "btn_read_rf_form": "Capturar Control RF (0x26)",
        "tpl_box": " Seleccionar y Aplicar Plantilla Rapida ",
        "btn_apply_tpl": "Cargar Plantilla en el Formulario",
        "btn_apply_and_send": "Cargar y Enviar Directo al MIP",
        "btn_save_tpl": "Guardar Formulario como Plantilla",
        "log_frame": " Consola de Tramas Hexadecimales (TX / RX) y Diagnostico ",
    },
    "PT": {
        "app_title": "Intelbras MIP 1000 IP - Console de Integração e Controle (Protocolo V2)",
        "conn_frame": " 1. Conexao TCP RAW (MIP 1000 IP) e Portas RTSP ",
        "ip_lbl": "IP do MIP:",
        "port_lbl": "Porta:",
        "login_lbl": "Login:",
        "pass_lbl": "Senha:",
        "fmt_lbl": "Header:",
        "lang_lbl": "Idioma:",
        "btn_connect": "Conectar",
        "btn_disconnect": "Desconectar",
        "st_disc": "[DESCONECTADO]",
        "st_conn": "[CONECTADO]",
        "rtsp1_lbl": "Cam 1 RTSP:",
        "rtsp2_lbl": "Cam 2 RTSP:",
        "btn_r1_conn": "Ver Cam 1",
        "btn_r1_disc": "Parar",
        "btn_r2_conn": "Ver Cam 2",
        "btn_r2_disc": "Parar",
        "tab_dashboard": "Dashboard",
        "tab_create": "Criar Usuario",
        "tab_edit": "Editar Usuario",
        "tab_tpl": "Modelos",
        "tab_search": "Consultas",
        "tab_events": "Eventos por Apto",
        "tab_online": "Online",
        "tab_ai": "Analise IA",
        "tab_detail": "Detalhe Meios",
        "tab_sip_network": "SIP / Rede",
        "asr_box": " Acionar Saida Remotamente - ASR (0x18) ",
        "dev_addr": "Endereco Dispositivo (1=MIP, 2..24=RS485):",
        "out_num": "Saida / Rele (1..2 MIP/XPE/XLT, 1..8 REMOTE):",
        "btn_open_door": "ABRIR PORTA / ACIONAR SAIDA AGORA",
        "cfg_box": " Configuracoes Rapidas do MIP (0x08 / 0x22 / 0x32) ",
        "btn_sync_time": "Sincronizar Data e Hora com o PC (CD - 0x08)",
        "btn_get_uid": "Consultar UID, MAC e Firmware (UID - 0x32)",
        "idle_msg": "Mensagem Display (max 20 chars):",
        "btn_set_msg": "Atualizar Mensagem de Descanso (MG - 0x22)",
        "vs_box": " Status do Banco de Dados - Verificar Sincronismo (VS - 0x17) ",
        "btn_get_vs": "Atualizar Contadores do MIP",
        "u_personal": " 1. Dados Pessoais e Apartamento (MU - 0x01) ",
        "u_access": " 2. Permissoes, Senhas e Dispositivos Liberados (1..24) ",
        "u_media": " 3. Veiculo, Chaveiro RFID (XID) e Controle (XTR) ",
        "btn_send_all": "ENVIAR NOVO USUARIO AO MIP (1-CLIQUE)",
        "btn_goto_edit": "Ir para Editar Usuario",
        "btn_save_changes": "Salvar Alteracoes no MIP (ALTERAR)",
        "btn_clear_form": "Limpar Formulario",
        "btn_read_tag_form": "Ler TAG no MIP (0x1C)",
        "btn_read_rf_form": "Ler Controle RF (0x26)",
        "tpl_box": " Selecionar e Aplicar Modelo Rapido ",
        "btn_apply_tpl": "Carregar Modelo no Formulario",
        "btn_apply_and_send": "Carregar e Enviar Direto ao MIP",
        "btn_save_tpl": "Salvar Formulario como Novo Modelo",
        "log_frame": " Console de Pacotes Hexadecimais (TX / RX) e Diagnóstico ",
    },
    "EN": {
        "app_title": "Intelbras MIP 1000 IP - Integration & Control HMI (Protocol V2)",
        "conn_frame": " 1. RAW TCP Connection (MIP 1000 IP) & RTSP Cameras ",
        "ip_lbl": "MIP IP:",
        "port_lbl": "Port:",
        "login_lbl": "Login:",
        "pass_lbl": "Password:",
        "fmt_lbl": "Header:",
        "lang_lbl": "Language:",
        "btn_connect": "Connect",
        "btn_disconnect": "Disconnect",
        "st_disc": "[DISCONNECTED]",
        "st_conn": "[CONNECTED]",
        "rtsp1_lbl": "Cam 1 RTSP:",
        "rtsp2_lbl": "Cam 2 RTSP:",
        "btn_r1_conn": "View Cam 1",
        "btn_r1_disc": "Stop",
        "btn_r2_conn": "View Cam 2",
        "btn_r2_disc": "Stop",
        "tab_dashboard": "Dashboard",
        "tab_create": "Create User",
        "tab_edit": "Edit User",
        "tab_tpl": "Templates",
        "tab_search": "Search",
        "tab_events": "Events by Apt",
        "tab_online": "Online",
        "tab_ai": "AI Analysis",
        "tab_detail": "Access Media",
        "tab_sip_network": "SIP / Network",
        "asr_box": " Trigger Remote Output - ASR (0x18) ",
        "dev_addr": "Device Address (1=MIP, 2..24=RS485):",
        "out_num": "Output / Relay (1..2 MIP/XPE/XLT, 1..8 REMOTE):",
        "btn_open_door": "OPEN DOOR / TRIGGER RELAY NOW",
        "cfg_box": " Quick MIP Settings (0x08 / 0x22 / 0x32) ",
        "btn_sync_time": "Sync Date & Time with PC (CD - 0x08)",
        "btn_get_uid": "Read UID, MAC & Firmware (UID - 0x32)",
        "idle_msg": "Idle Message (max 20 chars):",
        "btn_set_msg": "Update Idle Display Message (MG - 0x22)",
        "vs_box": " Database Counters - Verify Sync (VS - 0x17) ",
        "btn_get_vs": "Refresh MIP Counters",
        "u_personal": " 1. Personal & Apartment Info (MU - 0x01) ",
        "u_access": " 2. Permissions, Passwords & Allowed Devices (1..24) ",
        "u_media": " 3. Vehicle, RFID Tag (XID) & RF Remote (XTR) ",
        "btn_send_all": "SEND NEW USER TO MIP (1-CLICK)",
        "btn_goto_edit": "Go to Edit User",
        "btn_save_changes": "Save Changes to MIP (ALTERAR)",
        "btn_clear_form": "Clear Form",
        "btn_read_tag_form": "Read TAG on MIP (0x1C)",
        "btn_read_rf_form": "Read RF Remote (0x26)",
        "tpl_box": " Select & Apply User Template ",
        "btn_apply_tpl": "Load Template into Form",
        "btn_apply_and_send": "Load & Send Directly to MIP",
        "btn_save_tpl": "Save Form as Template",
        "log_frame": " Hexadecimal Frame Console (TX / RX) & Diagnostics ",
    },
}

DEFAULT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "Residente Estandar (Morador Peatonal)": {
        "categoria": 0, "nivel": 1, "nome": "RESIDENTE ESTANDAR", "apto": "101", "bloco": "A",
        "cpf": "", "rg": "", "email": "residente@condominio.com", "tel_res": "", "tel_cel": "3001234567",
        "senha_3dig": "123", "senha_sec": "", "dispositivos": [1, 2, 3], "dias_semana": 255,
        "modelo": "", "marca": "", "placa": "", "cor": "",
    },
    "Residente Vehicular": {
        "categoria": 0, "nivel": 1, "nome": "PROPIETARIO VEHICULO", "apto": "205", "bloco": "B",
        "cpf": "", "rg": "", "email": "vehiculo@condominio.com", "tel_res": "", "tel_cel": "3109876543",
        "senha_3dig": "456", "senha_sec": "", "dispositivos": [1, 2, 3, 4, 5], "dias_semana": 255,
        "modelo": "COROLLA", "marca": "TOYOTA", "placa": "ABC123", "cor": "PLATA",
    },
    "Visitante Temporal": {
        "categoria": 2, "nivel": 1, "nome": "VISITANTE AUTORIZADO", "apto": "302", "bloco": "A",
        "cpf": "", "rg": "", "email": "", "tel_res": "", "tel_cel": "3201112233",
        "senha_3dig": "789", "senha_sec": "", "dispositivos": [1, 2], "dias_semana": 127,
        "modelo": "", "marca": "", "placa": "", "cor": "",
    },
}


class MIP1000HMI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = "ES"
        self.title(I18N[self.lang]["app_title"])
        self.geometry("1280x740")
        self.minsize(1000, 650)
        self.configure(bg="#eef2f5")

        self.templates: Dict[str, Dict[str, Any]] = self._load_templates()
        self.ui_queue: "queue.Queue[ tuple[str, Any] ]" = queue.Queue()
        self.client = MIP1000Client(
            log_callback=lambda msg: self.ui_queue.put(("log", msg)),
            event_callback=lambda ev: self.ui_queue.put(("online_event", ev)),
        )

        self.rtsp1_running = False
        self.rtsp2_running = False

        # Variables para el monitoreo Online en Tiempo Real
        self.online_polling_active = False
        self.last_polled_event_id: int = -1
        self.busy_lock = threading.Lock()
        self.found_apto_users: Dict[str, Dict[str, Any]] = {}
        self.last_day_counts: Dict[str, int] = {}

        # Estado de las herramientas SIP (PJSUA2 + Fallback Socket UDP Nativo) y Captura de Red
        self.sip_endpoint = None
        self.sip_account = None
        self.sip_call = None
        self.raw_sip_socket = None
        self.raw_sip_call_id = f"{random.randint(100000, 999999)}@mip1000.local"
        self.raw_sip_cseq = 1
        self.capture_stop_event = threading.Event()
        self.capture_thread = None
        self.capture_handle = None
        self.capture_packet_count = 0

        self._build_ui()
        self.after(100, self._process_ui_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        data = dict(DEFAULT_TEMPLATES)
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                    custom = json.load(f)
                    if isinstance(custom, dict):
                        data.update(custom)
            except Exception:
                pass
        return data

    def _save_templates_to_disk(self) -> None:
        try:
            with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.templates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.client.log(f"Error guardando plantillas: {e}")

    def _info_label(self, parent, text: str) -> tk.Label:
        """Crea un label explicativo estilizado con ajuste automático de línea."""
        lbl = tk.Label(
            parent, text=f"ℹ️ {text}", bg=parent["bg"], fg="#4a5568",
            font=("Segoe UI", 8, "italic"), anchor="w", justify="left"
        )
        lbl.bind("<Configure>", lambda e: lbl.config(wraplength=max(220, e.width - 12)))
        return lbl

    def _textured_button(self, parent, text: str, command, color: str = "blue", width: int = 0, state: str = "normal") -> tk.Button:
        palettes = {
            "green": ("#1b8a4b", "#126335", "#ffffff"),
            "blue": ("#1f5fa8", "#154278", "#ffffff"),
            "orange": ("#d96b14", "#a34e0b", "#ffffff"),
            "red": ("#b82c2c", "#821d1d", "#ffffff"),
            "gray": ("#4a5568", "#2d3748", "#ffffff"),
            "purple": ("#6b46c1", "#553c9a", "#ffffff"),
            "teal": ("#2b6cb0", "#2c5282", "#ffffff"),
            "disabled": ("#cbd5e0", "#cbd5e0", "#a0aec0"),
        }
        if state == "disabled":
            bg, active_bg, fg = palettes["disabled"]
        else:
            bg, active_bg, fg = palettes.get(color, palettes["blue"])

        btn = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=active_bg, activeforeground=fg,
            relief="raised", bd=3, overrelief="ridge",
            font=("Segoe UI", 8, "bold"), cursor="hand2" if state == "normal" else "arrow",
            padx=6, pady=2, state=state,
        )
        if width > 0:
            btn.config(width=width)
        return btn

    def _build_ui(self) -> None:
        t = I18N[self.lang]

        # 1. Barra superior Conexion y Camaras RTSP
        self.conn_frame = tk.LabelFrame(self, text=t["conn_frame"], bg="#eef2f5", font=("Segoe UI", 9, "bold"), padx=6, pady=4)
        self.conn_frame.pack(fill="x", padx=10, pady=4)
        self.conn_frame.columnconfigure(3, weight=1)
        self.conn_frame.columnconfigure(11, weight=1)

        # Fila 0: MIP 1000 IP (Valores originales probados)
        tk.Label(self.conn_frame, text=t["ip_lbl"], bg="#eef2f5").grid(row=0, column=0, padx=1, sticky="e")
        self.ip_var = tk.StringVar(value="179.33.25.101")
        ttk.Entry(self.conn_frame, textvariable=self.ip_var, width=14).grid(row=0, column=1, padx=1, sticky="w")

        tk.Label(self.conn_frame, text=t["port_lbl"], bg="#eef2f5").grid(row=0, column=2, padx=1, sticky="e")
        self.port_var = tk.StringVar(value="9080")
        ttk.Entry(self.conn_frame, textvariable=self.port_var, width=6).grid(row=0, column=3, padx=1, sticky="w")

        tk.Label(self.conn_frame, text=t["login_lbl"], bg="#eef2f5").grid(row=0, column=4, padx=1, sticky="e")
        self.login_var = tk.StringVar(value="admin")
        ttk.Entry(self.conn_frame, textvariable=self.login_var, width=8).grid(row=0, column=5, padx=1)

        tk.Label(self.conn_frame, text=t["pass_lbl"], bg="#eef2f5").grid(row=0, column=6, padx=1, sticky="e")
        self.pass_var = tk.StringVar(value="123456")
        ttk.Entry(self.conn_frame, textvariable=self.pass_var, show="*", width=8).grid(row=0, column=7, padx=1)

        tk.Label(self.conn_frame, text=t["fmt_lbl"], bg="#eef2f5").grid(row=0, column=8, padx=1, sticky="e")
        self.pmode_var = tk.StringVar(value="bcd")
        ttk.Combobox(self.conn_frame, textvariable=self.pmode_var, values=["bcd", "int_le", "zero"], width=5, state="readonly").grid(row=0, column=9, padx=1)

        self.btn_connect = self._textured_button(self.conn_frame, t["btn_connect"], self._on_connect, color="green")
        self.btn_connect.grid(row=0, column=10, padx=3)

        self.btn_disconnect = self._textured_button(self.conn_frame, t["btn_disconnect"], self._on_disconnect, color="red")
        self.btn_disconnect.config(state="disabled")
        self.btn_disconnect.grid(row=0, column=11, padx=2, sticky="w")

        self.lbl_status = tk.Label(self.conn_frame, text=t["st_disc"], fg="#c53030", bg="#eef2f5", font=("Segoe UI", 8, "bold"))
        self.lbl_status.grid(row=0, column=12, padx=4)

        tk.Label(self.conn_frame, text=t["lang_lbl"], bg="#eef2f5", font=("Segoe UI", 8, "bold")).grid(row=0, column=13, padx=1, sticky="e")
        self.lang_var = tk.StringVar(value="ES")
        cb_lang = ttk.Combobox(self.conn_frame, textvariable=self.lang_var, values=["ES", "PT", "EN"], width=4, state="readonly")
        cb_lang.grid(row=0, column=14, padx=1)
        cb_lang.bind("<<ComboboxSelected>>", self._on_change_language)

        # Fila 1: Cámaras RTSP 1 y 2
        tk.Label(self.conn_frame, text=t["rtsp1_lbl"], bg="#eef2f5", font=("Segoe UI", 8, "bold")).grid(row=1, column=0, columnspan=2, sticky="e", pady=3)
        self.rtsp1_var = tk.StringVar(value="rtsp://admin:Vigilamos3014@179.33.25.101:554/ISAPI/streaming/Channels/1102")
        ttk.Entry(self.conn_frame, textvariable=self.rtsp1_var, width=30).grid(row=1, column=2, columnspan=4, sticky="ew", pady=3)
        self.btn_r1_conn = self._textured_button(self.conn_frame, t["btn_r1_conn"], self._connect_rtsp_1, color="blue")
        self.btn_r1_conn.grid(row=1, column=6, padx=1, pady=3)
        self.btn_r1_disc = self._textured_button(self.conn_frame, t["btn_r1_disc"], self._disconnect_rtsp_1, color="gray")
        self.btn_r1_disc.grid(row=1, column=7, padx=1, pady=3)

        tk.Label(self.conn_frame, text=t["rtsp2_lbl"], bg="#eef2f5", font=("Segoe UI", 8, "bold")).grid(row=1, column=8, columnspan=2, sticky="e", pady=3)
        self.rtsp2_var = tk.StringVar(value="rtsp://admin:123456@192.168.1.201:554/cam/realmonitor?channel=1&subtype=0")
        ttk.Entry(self.conn_frame, textvariable=self.rtsp2_var, width=24).grid(row=1, column=10, columnspan=3, sticky="ew", pady=3)
        self.btn_r2_conn = self._textured_button(self.conn_frame, t["btn_r2_conn"], self._connect_rtsp_2, color="blue")
        self.btn_r2_conn.grid(row=1, column=13, padx=1, pady=3)
        self.btn_r2_disc = self._textured_button(self.conn_frame, t["btn_r2_disc"], self._disconnect_rtsp_2, color="gray")
        self.btn_r2_disc.grid(row=1, column=14, padx=1, pady=3)

        # Fila 2: Nota explicativa de conexión
        tk.Label(
            self.conn_frame,
            text="ℹ️ Parámetros TCP: Ingrese la IP/Puerto configurados en el MIP 1000 IP. 'Header: bcd' es el formato estándar del protocolo V2.",
            bg="#eef2f5", fg="#4a5568", font=("Segoe UI", 8, "italic")
        ).grid(row=2, column=0, columnspan=15, sticky="w", pady=(2, 0))

        # 2. Consola Inferior Hexadecimal
        self.log_frame = tk.LabelFrame(self, text=t["log_frame"], bg="#eef2f5", font=("Segoe UI", 9, "bold"), padx=6, pady=4)
        self.log_frame.pack(side="bottom", fill="x", padx=10, pady=4)

        self.txt_log = tk.Text(self.log_frame, height=4, bg="#141820", fg="#00ff9d", font=("Consolas", 9))
        self.txt_log.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(self.log_frame, command=self.txt_log.yview)
        scroll.pack(side="right", fill="y")
        self.txt_log.config(yscrollcommand=scroll.set)

        # 3. Notebook Principal (10 Pestañas)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=4)

        self.tab_dashboard = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_create = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_edit = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_tpl = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_search = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_events = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_online = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_ai = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_detail = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)
        self.tab_sip_network = tk.Frame(self.notebook, bg="#f8fafc", padx=8, pady=6)

        self.notebook.add(self.tab_dashboard, text=t["tab_dashboard"])
        self.notebook.add(self.tab_create, text=t["tab_create"])
        self.notebook.add(self.tab_edit, text=t["tab_edit"])
        self.notebook.add(self.tab_tpl, text=t["tab_tpl"])
        self.notebook.add(self.tab_search, text=t["tab_search"])
        self.notebook.add(self.tab_events, text=t["tab_events"])
        self.notebook.add(self.tab_online, text=t["tab_online"])
        self.notebook.add(self.tab_ai, text=t["tab_ai"])
        self.notebook.add(self.tab_detail, text=t["tab_detail"])
        self.notebook.add(self.tab_sip_network, text=t["tab_sip_network"])

        self._build_tab_dashboard()
        self._build_tab_create_user()
        self._build_tab_edit_user()
        self._build_tab_templates()
        self._build_tab_search()
        self._build_tab_events()
        self._build_tab_online()
        self._build_tab_ai()
        self._build_tab_detail()
        self._build_tab_sip_network()

    # Pestaña 1: Dashboard (Con IP editable en Testeo de Puertos y Botones XRE blindados)
    def _build_tab_dashboard(self) -> None:
        t = I18N[self.lang]

        left_pane = tk.Frame(self.tab_dashboard, bg="#f8fafc")
        left_pane.pack(side="left", fill="y", padx=5, pady=2)

        self.asr_box = tk.LabelFrame(left_pane, text=t["asr_box"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        self.asr_box.pack(fill="x", pady=4)

        self._info_label(
            self.asr_box,
            "Seleccione Dir 1 para el MIP o 2..24 para módulos RS-485 (XRE/XPE/XLT)."
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        tk.Label(self.asr_box, text=t["dev_addr"], bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=3)
        self.dev_addr_var = tk.IntVar(value=1)
        ttk.Spinbox(self.asr_box, from_=1, to=24, textvariable=self.dev_addr_var, width=8).grid(row=1, column=1, pady=3, padx=6)

        tk.Label(self.asr_box, text=t["out_num"], bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=3)
        self.out_num_var = tk.IntVar(value=1)
        ttk.Spinbox(self.asr_box, from_=1, to=8, textvariable=self.out_num_var, width=8).grid(row=2, column=1, pady=3, padx=6)

        self.btn_open_door = self._textured_button(self.asr_box, t["btn_open_door"], self._cmd_open_door, color="green")
        self.btn_open_door.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8, ipady=2)

        self.cfg_box = tk.LabelFrame(left_pane, text=t["cfg_box"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        self.cfg_box.pack(fill="x", pady=4)

        self._info_label(
            self.cfg_box,
            "Sincronice el reloj del MIP o personalice el texto en pantalla."
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        self.btn_sync_time = self._textured_button(self.cfg_box, t["btn_sync_time"], self._cmd_sync_time, color="blue")
        self.btn_sync_time.grid(row=1, column=0, columnspan=2, sticky="ew", pady=3)

        self.btn_get_uid = self._textured_button(self.cfg_box, t["btn_get_uid"], self._cmd_get_uid, color="gray")
        self.btn_get_uid.grid(row=2, column=0, columnspan=2, sticky="ew", pady=3)

        tk.Label(self.cfg_box, text=t["idle_msg"], bg="#f8fafc").grid(row=3, column=0, sticky="w", pady=3)
        self.idle_msg_var = tk.StringVar(value="INTELBRAS MIP 1000")
        ttk.Entry(self.cfg_box, textvariable=self.idle_msg_var, width=22).grid(row=3, column=1, pady=3)

        self.btn_set_msg = self._textured_button(self.cfg_box, t["btn_set_msg"], self._cmd_set_idle_msg, color="orange")
        self.btn_set_msg.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

        # Columna Central: Estado de Base de Datos y Herramienta de Testeo de Puertos Abajo
        mid_pane = tk.Frame(self.tab_dashboard, bg="#f8fafc")
        mid_pane.pack(side="left", fill="both", expand=True, padx=5, pady=2)

        port_test_box = tk.LabelFrame(mid_pane, text=" Testeo de Puertos de Red (RTSP / TCP) ", bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        port_test_box.pack(side="bottom", fill="x", pady=(4, 0))

        self._info_label(
            port_test_box,
            "Edite la IP Destino y el Puerto para comprobar conectividad hacia cámaras, grabadores o el MIP."
        ).pack(fill="x", pady=(0, 4))

        pt_row = tk.Frame(port_test_box, bg="#f8fafc")
        pt_row.pack(fill="x", pady=2)

        tk.Label(pt_row, text="IP Destino:", bg="#f8fafc", font=("Segoe UI", 8, "bold")).pack(side="left", padx=2)
        self.test_ip_var = tk.StringVar(value=self.ip_var.get())
        ttk.Entry(pt_row, textvariable=self.test_ip_var, width=14).pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(pt_row, text="Puerto:", bg="#f8fafc", font=("Segoe UI", 8, "bold")).pack(side="left", padx=2)
        self.test_port_var = tk.StringVar(value="554")
        ttk.Entry(pt_row, textvariable=self.test_port_var, width=6).pack(side="left", padx=4)

        self._textured_button(pt_row, "Testear IP:Puerto", self._cmd_test_port, color="teal", width=15).pack(side="left", padx=6)

        self.lbl_port_status = tk.Label(port_test_box, text="Estado: En espera de test...", bg="#f8fafc", fg="#4a5568", font=("Consolas", 9, "bold"))
        self.lbl_port_status.pack(fill="x", pady=(4, 0))

        self.vs_box = tk.LabelFrame(mid_pane, text=t["vs_box"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        self.vs_box.pack(side="top", fill="both", expand=True)

        self._info_label(
            self.vs_box,
            "Muestra el total de usuarios, tarjetas, controles y eventos almacenados en el MIP."
        ).pack(fill="x", pady=(0, 4))

        self.btn_get_vs = self._textured_button(self.vs_box, t["btn_get_vs"], self._cmd_get_vs, color="blue")
        self.btn_get_vs.pack(fill="x", pady=3)

        self.tree_vs = ttk.Treeview(self.vs_box, columns=("tabla", "total"), show="headings", height=6)
        self.tree_vs.heading("tabla", text="Tabla / Recurso en el MIP")
        self.tree_vs.heading("total", text="Total Registros (Ultimo ID)")
        self.tree_vs.column("tabla", width=170, stretch=True)
        self.tree_vs.column("total", width=90, anchor="center", stretch=True)
        self.tree_vs.pack(fill="both", expand=True, pady=3)

        # Columna Derecha: Cámaras y XRE 1000 Plus (Con Grid elástico para video y altura fija de 38px en botones XRE)
        right_pane = tk.Frame(self.tab_dashboard, bg="#f8fafc")
        right_pane.pack(side="left", fill="both", expand=True, padx=5, pady=2)

        cam_box = tk.LabelFrame(right_pane, text=" Visualizacion Camaras Online & XRE 1000 Plus ", bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        cam_box.pack(fill="both", expand=True)
        cam_box.columnconfigure(0, weight=1)
        cam_box.rowconfigure(1, weight=1)
        cam_box.rowconfigure(3, weight=1)

        self._info_label(
            cam_box,
            "Los botones de apertura XRE se habilitan al detectar dispositivos conectados al bus RS-485."
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.cam1_container = tk.Frame(cam_box, bg="#1a202c", height=115)
        self.cam1_container.grid(row=1, column=0, sticky="nsew", pady=2)
        self.cam1_container.grid_propagate(False)
        self.lbl_cam1 = tk.Label(self.cam1_container, bg="#1a202c", text="[ Camara 1 Desconectada ]", fg="#a0aec0", font=("Segoe UI", 9, "bold"))
        self.lbl_cam1.pack(expand=True, fill="both")

        xre1_holder = tk.Frame(cam_box, bg="#f8fafc", height=38)
        xre1_holder.grid(row=2, column=0, sticky="ew", pady=(2, 6))
        xre1_holder.pack_propagate(False)
        self.btn_xre1 = self._textured_button(xre1_holder, "🔓 XRE 1000 Plus [Desconectado]", lambda: self._cmd_open_xre_door(2), color="disabled", state="disabled")
        self.btn_xre1.pack(fill="both", expand=True)

        self.cam2_container = tk.Frame(cam_box, bg="#1a202c", height=115)
        self.cam2_container.grid(row=3, column=0, sticky="nsew", pady=2)
        self.cam2_container.grid_propagate(False)
        self.lbl_cam2 = tk.Label(self.cam2_container, bg="#1a202c", text="[ Camara 2 Desconectada ]", fg="#a0aec0", font=("Segoe UI", 9, "bold"))
        self.lbl_cam2.pack(expand=True, fill="both")

        xre2_holder = tk.Frame(cam_box, bg="#f8fafc", height=38)
        xre2_holder.grid(row=4, column=0, sticky="ew", pady=(2, 2))
        xre2_holder.pack_propagate(False)
        self.btn_xre2 = self._textured_button(xre2_holder, "🔓 XRE 1000 Plus [Desconectado]", lambda: self._cmd_open_xre_door(3), color="disabled", state="disabled")
        self.btn_xre2.pack(fill="both", expand=True)

    # Pestaña 10: Diagnóstico SIP, Softphone y Captura de Tráfico
    def _build_tab_sip_network(self) -> None:
        self.tab_sip_network.columnconfigure(0, weight=1, uniform="sipcol")
        self.tab_sip_network.columnconfigure(1, weight=1, uniform="sipcol")
        self.tab_sip_network.columnconfigure(2, weight=2, uniform="sipcol")
        self.tab_sip_network.rowconfigure(1, weight=1)

        tk.Label(
            self.tab_sip_network,
            text="Herramientas de implementación SIP · Detector SIP ALG, Softphone SIP 2.0 y Monitor de Tráfico en Vivo",
            bg="#f8fafc", fg="#334155", font=("Segoe UI", 10, "bold"), anchor="w"
        ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 6))

        # Columna 1: Detector SIP ALG / Prueba OPTIONS
        alg = tk.LabelFrame(
            self.tab_sip_network, text="1. Detector SIP ALG / Prueba SIP", bg="#f8fafc",
            font=("Segoe UI", 9, "bold"), padx=8, pady=6
        )
        alg.grid(row=1, column=0, sticky="nsew", padx=4, pady=2)
        alg.columnconfigure(0, weight=1)

        tk.Label(alg, text="Servidor SIP / PBX:", bg="#f8fafc").grid(row=0, column=0, sticky="w", pady=(2, 0))
        self.alg_host_var = tk.StringVar(value="d8365fbf8b9c.porteriaenlanube.com")
        ttk.Entry(alg, textvariable=self.alg_host_var).grid(row=1, column=0, sticky="ew", pady=(2, 5))
        tk.Label(alg, text="Puerto SIP:", bg="#f8fafc").grid(row=2, column=0, sticky="w")
        self.alg_port_var = tk.StringVar(value="5060")
        ttk.Entry(alg, textvariable=self.alg_port_var).grid(row=3, column=0, sticky="ew", pady=(2, 5))
        self.btn_sip_probe = self._textured_button(
            alg, "Detectar SIP ALG / Probar OPTIONS", self._sip_probe_clicked, color="teal"
        )
        self.btn_sip_probe.grid(row=4, column=0, sticky="ew", pady=4, ipady=2)
        self.lbl_sip_probe_result = tk.Label(
            alg, text="Sin prueba todavía.", bg="#f8fafc", fg="#4a5568",
            justify="left", anchor="w", wraplength=280
        )
        self.lbl_sip_probe_result.grid(row=5, column=0, sticky="ew", pady=(2, 6))
        self.lbl_sip_probe_result.bind("<Configure>", lambda e: self.lbl_sip_probe_result.config(wraplength=max(180, e.width - 10)))

        ttk.Separator(alg).grid(row=6, column=0, sticky="ew", pady=4)
        tk.Label(
            alg, text="Estado SIP ALG verificado en el router (manual):",
            bg="#f8fafc", justify="left"
        ).grid(row=7, column=0, sticky="w", pady=(2, 2))
        self.alg_manual_state_var = tk.StringVar(value="No verificado")
        ttk.Combobox(
            alg, textvariable=self.alg_manual_state_var,
            values=["No verificado", "Habilitado", "Deshabilitado"], state="readonly"
        ).grid(row=8, column=0, sticky="ew", pady=(0, 5))
        lbl_alg_note = tk.Label(
            alg,
            text=("Envía una trama SIP OPTIONS con cabeceras locales y analiza si el router NAT "
                  "reescribe los encabezados Via/Contact (comportamiento típico de SIP ALG activo)."),
            bg="#fff7ed", fg="#7c2d12", justify="left", anchor="w", wraplength=280,
            padx=6, pady=6
        )
        lbl_alg_note.grid(row=9, column=0, sticky="ew", pady=(2, 0))
        lbl_alg_note.bind("<Configure>", lambda e: lbl_alg_note.config(wraplength=max(180, e.width - 16)))

        # Columna 2: Softphone SIP 2.0 (Usa PJSUA2 si existe o Motor SIP 2.0 UDP Nativo desde cero)
        phone = tk.LabelFrame(
            self.tab_sip_network, text="2. Softphone VoIP SIP 2.0", bg="#f8fafc",
            font=("Segoe UI", 9, "bold"), padx=8, pady=6
        )
        phone.grid(row=1, column=1, sticky="nsew", padx=4, pady=2)
        phone.columnconfigure(1, weight=1)

        phone_fields = [
            ("Servidor / dominio SIP:", "sip_host_var", "d8365fbf8b9c.porteriaenlanube.com"),
            ("Puerto SIP:", "sip_port_var", "5080"),
            ("Extensión / usuario:", "sip_user_var", "990002"),
            ("Usuario auth:", "sip_auth_user_var", "990002"),
            ("Contraseña SIP:", "sip_password_var", "EFv6h8kdr"),
            ("Extensión destino:", "sip_dest_var", "990001"),
            ("Puerto local UDP:", "sip_local_port_var", "5072"),
        ]
        for row, (label, attr, default) in enumerate(phone_fields):
            tk.Label(phone, text=label, bg="#f8fafc").grid(row=row, column=0, sticky="w", pady=2, padx=(0, 4))
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            entry = ttk.Entry(phone, textvariable=var, show="*" if attr == "sip_password_var" else "")
            entry.grid(row=row, column=1, sticky="ew", pady=2)

        pbar = tk.Frame(phone, bg="#f8fafc")
        pbar.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        pbar.columnconfigure(0, weight=1)
        pbar.columnconfigure(1, weight=1)
        self.btn_sip_register = self._textured_button(
            pbar, "Registrar / conectar", self._sip_register_clicked, color="green"
        )
        self.btn_sip_register.grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=2)
        self.btn_sip_unregister = self._textured_button(
            pbar, "Desconectar", self._sip_unregister_clicked, color="gray"
        )
        self.btn_sip_unregister.grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=2)
        # Fila 8: Botón Llamar
        self.btn_sip_call = self._textured_button(
            phone, "Llamar extensión destino", self._sip_call_clicked, color="blue"
        )
        self.btn_sip_call.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(4, 2))

        # Fila 9: Botón Colgar
        self.btn_sip_hangup = self._textured_button(
            phone, "Colgar", self._sip_hangup_clicked, color="red", state="disabled"
        )
        self.btn_sip_hangup.grid(row=9, column=0, columnspan=2, sticky="ew", pady=2)

        # Fila 10: Botón de Verificación (Ping SIP) con altura e indicación visual
        self.btn_check_dest = self._textured_button(
            phone, "Verificar Estado Extensión (Ping SIP)",
            self._cmd_check_dest_status, color="teal"
        )
        self.btn_check_dest.config(wraplength=260, justify="center")
        self.btn_check_dest.grid(row=10, column=0, columnspan=2, sticky="ew", padx=2, pady=(3, 4), ipady=2)

        # Fila 11: Estado de Registro SIP
        self.lbl_softphone_status = tk.Label(
            phone, text=("PJSUA2 disponible." if PJSUA2_AVAILABLE else
                         "Motor SIP 2.0 UDP Nativo listo."),
            bg="#f8fafc", fg="#2b6cb0", justify="left", anchor="w", wraplength=280
        )
        self.lbl_softphone_status.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 1))

        # Fila 12: Estado de Llamada / Respuesta Ping
        self.lbl_call_status = tk.Label(
            phone, text="Llamada: inactiva", bg="#f8fafc", fg="#334155",
            justify="left", anchor="w", wraplength=280
        )
        self.lbl_call_status.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(1, 2))
        # Columna 3: Monitoreo y Analizador de Errores SIP en Vivo
        mon = tk.LabelFrame(
            self.tab_sip_network, text="3. Monitoreo / errores SIP en vivo", bg="#f8fafc",
            font=("Segoe UI", 9, "bold"), padx=8, pady=6
        )
        mon.grid(row=1, column=2, sticky="nsew", padx=4, pady=2)
        mon.columnconfigure(0, weight=1)
        mon.rowconfigure(3, weight=1)

        f_top_mon = tk.Frame(mon, bg="#f8fafc")
        f_top_mon.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        f_top_mon.columnconfigure(1, weight=1)
        f_top_mon.columnconfigure(3, weight=2)

        tk.Label(f_top_mon, text="Interfaz:", bg="#f8fafc").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.capture_interface_var = tk.StringVar(value="")
        ttk.Entry(f_top_mon, textvariable=self.capture_interface_var, width=12).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        tk.Label(f_top_mon, text="Filtro BPF:", bg="#f8fafc").grid(row=0, column=2, sticky="w", padx=(0, 4))
        self.capture_filter_var = tk.StringVar(
            value="udp port 5060 or tcp port 5060 or udp portrange 10000-20000"
        )
        ttk.Entry(f_top_mon, textvariable=self.capture_filter_var).grid(row=0, column=3, sticky="ew")

        cap_buttons = tk.Frame(mon, bg="#f8fafc")
        cap_buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
        for col in range(3):
            cap_buttons.columnconfigure(col, weight=1)
        self.btn_capture_start = self._textured_button(
            cap_buttons, "Iniciar captura", self._capture_start_clicked, color="green"
        )
        self.btn_capture_start.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self.btn_capture_stop = self._textured_button(
            cap_buttons, "Detener", self._capture_stop_clicked, color="red", state="disabled"
        )
        self.btn_capture_stop.grid(row=0, column=1, sticky="ew", padx=3)
        self._textured_button(
            cap_buttons, "Limpiar", self._capture_clear, color="gray"
        ).grid(row=0, column=2, sticky="ew", padx=(3, 0))

        columns = ("hora", "origen", "destino", "protocolo", "detalle")
        self.tree_capture = ttk.Treeview(mon, columns=columns, show="headings", height=10)
        for col, title, width in [
            ("hora", "Hora", 70), ("origen", "Origen", 105), ("destino", "Destino", 105),
            ("protocolo", "Proto", 55), ("detalle", "Resumen / error", 220)
        ]:
            self.tree_capture.heading(col, text=title)
            self.tree_capture.column(col, width=width, minwidth=45, stretch=True)
        self.tree_capture.tag_configure("sip_error", background="#fee2e2", foreground="#991b1b")
        self.tree_capture.grid(row=3, column=0, sticky="nsew")
        cap_scroll = ttk.Scrollbar(mon, orient="vertical", command=self.tree_capture.yview)
        cap_scroll.grid(row=3, column=1, sticky="ns")
        self.tree_capture.configure(yscrollcommand=cap_scroll.set)
        self.lbl_capture_count = tk.Label(mon, text="Paquetes mostrados: 0", bg="#f8fafc", fg="#334155", anchor="w")
        self.lbl_capture_count.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self.lbl_capture_status = tk.Label(
            mon, text="Captura lista (Soporta PyShark, Scapy o Escucha UDP SIP integrada).",
            bg="#f8fafc", fg="#64748b", justify="left", anchor="w", wraplength=480
        )
        self.lbl_capture_status.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(2, 0))

    @staticmethod
    def _mask_rtsp_url(url: str) -> str:
        return re.sub(r"(rtsp://)[^/@\s]+:[^/@\s]+@", r"\1***:***@", url, flags=re.IGNORECASE)

    def _sip_probe_clicked(self) -> None:
        host = self.alg_host_var.get().strip()
        try:
            port = int(self.alg_port_var.get().strip())
            if not host or not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Prueba SIP", "Ingrese un host SIP y un puerto entre 1 y 65535.")
            return
        self.btn_sip_probe.config(state="disabled")
        self.lbl_sip_probe_result.config(text=f"Probando respuesta SIP hacia {host}:{port}…", fg="#975a16")

        def task():
            ok = False
            result = "Prueba sin resultado."
            sock = None
            try:
                infos = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
                family, socktype, proto, _, sockaddr = infos[0]
                sock = socket.socket(family, socktype, proto)
                sock.settimeout(3.0)
                sock.connect(sockaddr)
                local_ip, local_port = sock.getsockname()[:2]
                branch = "z9hG4bK" + uuid.uuid4().hex[:12]
                tag = uuid.uuid4().hex[:8]
                call_id = uuid.uuid4().hex + "@" + local_ip
                request = (
                    f"OPTIONS sip:{host}:{port} SIP/2.0\r\n"
                    f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch};rport\r\n"
                    "Max-Forwards: 70\r\n"
                    f"From: <sip:diag@{local_ip}>;tag={tag}\r\n"
                    f"To: <sip:{host}>\r\n"
                    f"Call-ID: {call_id}\r\n"
                    "CSeq: 1 OPTIONS\r\n"
                    f"Contact: <sip:diag@{local_ip}:{local_port}>\r\n"
                    "Accept: application/sdp\r\n"
                    "Content-Length: 0\r\n\r\n"
                )
                sock.send(request.encode("utf-8"))
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{local_port}", f"{host}:{port}", "UDP", "SIP OPTIONS (Probe)"), False)
                
                try:
                    response = sock.recv(8192).decode("utf-8", errors="replace")
                except (ConnectionResetError, socket.timeout):
                    response = ""
                
                if response:
                    first = response.splitlines()[0] if response.splitlines() else "Respuesta vacía"
                    ok = True
                    result = f"{first}\n✅ El servidor respondió al sondeo SIP OPTIONS."
                else:
                    result = "⚠️ El servidor no respondió al OPTIONS (Puerto protegido o bloqueado por política del PBX)."
            except socket.timeout:
                result = "⏱️ Timeout: El servidor SIP no respondió en el tiempo límite (3s)."
            except Exception as exc:
                result = f"ℹ️ Nota de red: El host remoto cerró la conexión o no admite OPTIONS directos."
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                self.ui_queue.put(("sip_probe_result", (ok, result)))
                self.ui_queue.put(("sip_probe_done", None))
        self._run_bg(task)
        def task():
            ok = False
            result = "Prueba sin resultado."
            try:
                infos = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
                family, socktype, proto, _, sockaddr = infos[0]
                sock = socket.socket(family, socktype, proto)
                sock.settimeout(3.0)
                sock.connect(sockaddr)
                local_ip, local_port = sock.getsockname()[:2]
                branch = "z9hG4bK" + uuid.uuid4().hex[:12]
                tag = uuid.uuid4().hex[:8]
                call_id = uuid.uuid4().hex + "@" + local_ip
                request = (
                    f"OPTIONS sip:{host}:{port} SIP/2.0\r\n"
                    f"Via: SIP/2.0/UDP {local_ip}:{local_port};branch={branch};rport\r\n"
                    "Max-Forwards: 70\r\n"
                    f"From: <sip:diag@{local_ip}>;tag={tag}\r\n"
                    f"To: <sip:{host}>\r\n"
                    f"Call-ID: {call_id}\r\n"
                    "CSeq: 1 OPTIONS\r\n"
                    f"Contact: <sip:diag@{local_ip}:{local_port}>\r\n"
                    "Accept: application/sdp\r\n"
                    "Content-Length: 0\r\n\r\n"
                )
                sock.send(request.encode("utf-8"))
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{local_port}", f"{host}:{port}", "UDP", "SIP OPTIONS (Probe ALG)"), False)
                response = sock.recv(8192).decode("utf-8", errors="replace")
                sock.close()
                first = response.splitlines()[0] if response else "Respuesta vacía"
                status_match = re.search(r"SIP/2\.0\s+(\d{3})", first)
                status_code = int(status_match.group(1)) if status_match else 0
                ok = status_code > 0
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{host}:{port}", f"{local_ip}:{local_port}", "UDP", first), status_code >= 400)

                alg_modified = f"{local_ip}:{local_port}" not in response and "received=" not in response.lower()
                if alg_modified:
                    interpretation = "⚠️ Indicio de SIP ALG ACTIVO: la cabecera Via/Contact local fue alterada en tránsito."
                else:
                    interpretation = "✅ Respuesta recibida sin alteración evidente de cabeceras (SIP ALG no detectado)."
                result = f"{first}\n{interpretation}"
            except socket.timeout:
                result = "Sin respuesta SIP en 3 s (Timeout). Verifique IP, puerto 5060 o firewall."
            except Exception as exc:
                result = f"No se pudo completar la prueba: {exc}"
            finally:
                self.ui_queue.put(("sip_probe_result", (ok, result)))
                self.ui_queue.put(("sip_probe_done", None))
        self._run_bg(task)

    def _sip_register_clicked(self) -> None:
        host = self.sip_host_var.get().strip()
        user = self.sip_user_var.get().strip()
        auth_user = self.sip_auth_user_var.get().strip() or user
        password = self.sip_password_var.get()
        try:
            port = int(self.sip_port_var.get().strip())
            local_port = int(self.sip_local_port_var.get().strip())
            if not host or not user or not password or not 1 <= port <= 65535 or not 1 <= local_port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Softphone", "Complete servidor, extensión, contraseña y puertos válidos.")
            return
        self.btn_sip_register.config(state="disabled")
        self.lbl_softphone_status.config(text="Solicitando registro SIP…", fg="#975a16")

        def task():
            # Si PJSUA2 está instalado, usar PJSUA2; si no, usar el motor SIP 2.0 UDP nativo
            if PJSUA2_AVAILABLE:
                try:
                    if self.sip_endpoint is not None and self.sip_account is not None:
                        self.sip_account.setRegistration(True)
                        self.ui_queue.put(("sip_tool_status", "Solicitud de registro enviada."))
                        return
                    endpoint = pj.Endpoint()
                    endpoint.libCreate()
                    ep_cfg = pj.EpConfig()
                    ep_cfg.logConfig.level = 2
                    endpoint.libInit(ep_cfg)
                    transport_cfg = pj.TransportConfig()
                    transport_cfg.port = local_port
                    endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)
                    endpoint.libStart()

                    account_cfg = pj.AccountConfig()
                    account_cfg.idUri = f"sip:{user}@{host}"
                    account_cfg.regConfig.registrarUri = f"sip:{host}:{port}"
                    credential = pj.AuthCredInfo("digest", "*", auth_user, 0, password)
                    account_cfg.sipConfig.authCreds.append(credential)
                    account = _HmiSipAccount(lambda kind, data: self.ui_queue.put((kind, data)))
                    account.create(account_cfg)
                    self.sip_endpoint = endpoint
                    self.sip_account = account
                    self.ui_queue.put(("sip_tool_status", "Cuenta PJSUA2 creada; esperando respuesta…"))
                except Exception as exc:
                    self.sip_endpoint = None
                    self.sip_account = None
                    self.ui_queue.put(("sip_register_status", (0, f"Error PJSUA2: {exc}")))
                return

            # Fallback Nativo SIP 2.0 UDP con Digest MD5
            try:
                if self.raw_sip_socket is None:
                    self.raw_sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.raw_sip_socket.settimeout(3.5)
                s = self.raw_sip_socket
                s.connect((host, port))
                local_ip, lport = s.getsockname()[:2]
                self.raw_sip_cseq += 1
                branch = "z9hG4bK" + uuid.uuid4().hex[:10]
                tag = uuid.uuid4().hex[:8]

                reg1 = (
                    f"REGISTER sip:{host} SIP/2.0\r\n"
                    f"Via: SIP/2.0/UDP {local_ip}:{lport};branch={branch};rport\r\n"
                    "Max-Forwards: 70\r\n"
                    f"From: <sip:{user}@{host}>;tag={tag}\r\n"
                    f"To: <sip:{user}@{host}>\r\n"
                    f"Call-ID: {self.raw_sip_call_id}\r\n"
                    f"CSeq: {self.raw_sip_cseq} REGISTER\r\n"
                    f"Contact: <sip:{user}@{local_ip}:{lport}>\r\n"
                    "Expires: 3600\r\n"
                    "Content-Length: 0\r\n\r\n"
                )
                s.send(reg1.encode("utf-8"))
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{lport}", f"{host}:{port}", "UDP", "SIP REGISTER"), False)
                resp = s.recv(8192).decode("utf-8", errors="replace")
                first = resp.splitlines()[0] if resp else ""

                if "401 " in first or "407 " in first:
                    nonce_m = re.search(r'nonce="([^"]+)"', resp)
                    realm_m = re.search(r'realm="([^"]+)"', resp)
                    realm_val = realm_m.group(1) if realm_m else host
                    nonce_val = nonce_m.group(1) if nonce_m else ""
                    ha1 = hashlib.md5(f"{auth_user}:{realm_val}:{password}".encode("utf-8")).hexdigest()
                    ha2 = hashlib.md5(f"REGISTER:sip:{host}".encode("utf-8")).hexdigest()
                    digest_resp = hashlib.md5(f"{ha1}:{nonce_val}:{ha2}".encode("utf-8")).hexdigest()

                    self.raw_sip_cseq += 1
                    branch2 = "z9hG4bK" + uuid.uuid4().hex[:10]
                    reg2 = (
                        f"REGISTER sip:{host} SIP/2.0\r\n"
                        f"Via: SIP/2.0/UDP {local_ip}:{lport};branch={branch2};rport\r\n"
                        "Max-Forwards: 70\r\n"
                        f"From: <sip:{user}@{host}>;tag={tag}\r\n"
                        f"To: <sip:{user}@{host}>\r\n"
                        f"Call-ID: {self.raw_sip_call_id}\r\n"
                        f"CSeq: {self.raw_sip_cseq} REGISTER\r\n"
                        f"Contact: <sip:{user}@{local_ip}:{lport}>\r\n"
                        f'Authorization: Digest username="{auth_user}", realm="{realm_val}", nonce="{nonce_val}", uri="sip:{host}", response="{digest_resp}", algorithm=MD5\r\n'
                        "Expires: 3600\r\n"
                        "Content-Length: 0\r\n\r\n"
                    )
                    s.send(reg2.encode("utf-8"))
                    resp = s.recv(8192).decode("utf-8", errors="replace")
                    first = resp.splitlines()[0] if resp else ""

                m_code = re.search(r"SIP/2\.0\s+(\d{3})\s*(.*)", first)
                code_num = int(m_code.group(1)) if m_code else 0
                reason_txt = m_code.group(2) if m_code else first
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{host}:{port}", f"{local_ip}:{lport}", "UDP", f"SIP {code_num} {reason_txt}"), code_num >= 400)
                self.ui_queue.put(("sip_register_status", (code_num, reason_txt)))
            except Exception as exc:
                self.ui_queue.put(("sip_register_status", (0, f"Sin respuesta o error SIP: {exc}")))
        self._run_bg(task)

    def _sip_unregister_clicked(self) -> None:
        def task():
            try:
                if self.raw_sip_socket is not None:
                    try:
                        self.raw_sip_socket.close()
                    except Exception:
                        pass
                    self.raw_sip_socket = None
                if self.sip_call is not None and PJSUA2_AVAILABLE:
                    try:
                        self.sip_call.hangup(pj.CallOpParam())
                    except Exception:
                        pass
                    self.sip_call = None
                account = self.sip_account
                endpoint = self.sip_endpoint
                if account is not None:
                    try:
                        account.setRegistration(False)
                        time.sleep(0.5)
                    except Exception:
                        pass
                self.sip_account = None
                self.sip_endpoint = None
                if endpoint is not None:
                    try:
                        endpoint.libDestroy()
                    except Exception:
                        pass
                self.ui_queue.put(("sip_tool_status", "Softphone desconectado."))
                self.ui_queue.put(("sip_register_status", (0, "Desconectado")))
            except Exception as exc:
                self.ui_queue.put(("sip_tool_status", f"Error al desconectar: {exc}"))
        self._run_bg(task)

    def _sip_call_clicked(self) -> None:
        target = self.sip_dest_var.get().strip()
        if not target:
            messagebox.showwarning("Softphone", "Ingrese la extensión destino.")
            return
        host = self.sip_host_var.get().strip()
        try:
            port = int(self.sip_port_var.get().strip() or "5060")
        except ValueError:
            port = 5060
        user = self.sip_user_var.get().strip() or "1001"
        auth_user = self.sip_auth_user_var.get().strip() or user
        password = self.sip_password_var.get()

        self.btn_sip_call.config(state="disabled")
        self.btn_sip_hangup.config(state="normal")
        self.lbl_call_status.config(text=f"Iniciando llamada a {target}...", fg="#2b6cb0")

        def task():
            if PJSUA2_AVAILABLE and self.sip_endpoint is not None and self.sip_account is not None:
                try:
                    uri = target if target.lower().startswith("sip:") else f"sip:{target}@{host}:{port}"
                    call = _HmiSipCall(
                        self.sip_account, self.sip_endpoint,
                        lambda kind, data: self.ui_queue.put((kind, data))
                    )
                    self.sip_call = call
                    call.makeCall(uri, pj.CallOpParam(True))
                    self.ui_queue.put(("sip_call_status", f"Llamando a {uri}"))
                except Exception as exc:
                    self.sip_call = None
                    self.ui_queue.put(("sip_call_disconnected", f"Error PJSUA2: {exc}"))
                return

            # Motor SIP 2.0 UDP con soporte de reto 407 Proxy Auth
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(3.0)
                s.connect((host, port))
                local_ip, lport = s.getsockname()[:2]
                self.raw_sip_socket = s

                call_id = f"{uuid.uuid4().hex[:16]}@{local_ip}"
                self.raw_sip_call_id = call_id
                self.raw_sip_cseq = 1
                call_tag = uuid.uuid4().hex[:8]
                branch = "z9hG4bK" + uuid.uuid4().hex[:10]

                sdp_lines = [
                    "v=0",
                    f"o={user} 1000 1000 IN IP4 {local_ip}",
                    "s=Talk",
                    f"c=IN IP4 {local_ip}",
                    "t=0 0",
                    "m=audio 40000 RTP/AVP 0 8 101",
                    "a=rtpmap:0 PCMU/8000",
                    "a=rtpmap:8 PCMA/8000",
                    "a=rtpmap:101 telephone-event/8000",
                    ""
                ]
                sdp_body = "\r\n".join(sdp_lines)
                sdp_bytes = sdp_body.encode("utf-8")

                # 1. Enviar INVITE inicial
                inv = (
                    f"INVITE sip:{target}@{host}:{port} SIP/2.0\r\n"
                    f"Via: SIP/2.0/UDP {local_ip}:{lport};branch={branch};rport\r\n"
                    "Max-Forwards: 70\r\n"
                    f"From: <sip:{user}@{host}>;tag={call_tag}\r\n"
                    f"To: <sip:{target}@{host}>\r\n"
                    f"Call-ID: {call_id}\r\n"
                    f"CSeq: {self.raw_sip_cseq} INVITE\r\n"
                    f"Contact: <sip:{user}@{local_ip}:{lport}>\r\n"
                    "Content-Type: application/sdp\r\n"
                    f"Content-Length: {len(sdp_bytes)}\r\n\r\n"
                )
                s.send(inv.encode("utf-8") + sdp_bytes)
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{lport}", f"{host}:{port}", "UDP", f"SIP INVITE -> {target}"), False)

                resp = s.recv(8192).decode("utf-8", errors="replace")
                first_line = resp.splitlines()[0] if resp.splitlines() else ""

                # 2. Si exige autenticación (407 Proxy Auth o 401 Unauth)
                if "407" in first_line or "401" in first_line:
                    nonce_m = re.search(r'nonce="([^"]+)"', resp)
                    realm_m = re.search(r'realm="([^"]+)"', resp)
                    realm_val = realm_m.group(1) if realm_m else host
                    nonce_val = nonce_m.group(1) if nonce_m else ""

                    ha1 = hashlib.md5(f"{auth_user}:{realm_val}:{password}".encode("utf-8")).hexdigest()
                    ha2 = hashlib.md5(f"INVITE:sip:{target}@{host}:{port}".encode("utf-8")).hexdigest()
                    digest_resp = hashlib.md5(f"{ha1}:{nonce_val}:{ha2}".encode("utf-8")).hexdigest()

                    self.raw_sip_cseq += 1
                    branch2 = "z9hG4bK" + uuid.uuid4().hex[:10]
                    inv_auth = (
                        f"INVITE sip:{target}@{host}:{port} SIP/2.0\r\n"
                        f"Via: SIP/2.0/UDP {local_ip}:{lport};branch={branch2};rport\r\n"
                        "Max-Forwards: 70\r\n"
                        f"From: <sip:{user}@{host}>;tag={call_tag}\r\n"
                        f"To: <sip:{target}@{host}>\r\n"
                        f"Call-ID: {call_id}\r\n"
                        f"CSeq: {self.raw_sip_cseq} INVITE\r\n"
                        f"Contact: <sip:{user}@{local_ip}:{lport}>\r\n"
                        f'Proxy-Authorization: Digest username="{auth_user}", realm="{realm_val}", nonce="{nonce_val}", uri="sip:{target}@{host}:{port}", response="{digest_resp}", algorithm=MD5\r\n'
                        "Content-Type: application/sdp\r\n"
                        f"Content-Length: {len(sdp_bytes)}\r\n\r\n"
                    )
                    s.send(inv_auth.encode("utf-8") + sdp_bytes)
                    self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{lport}", f"{host}:{port}", "UDP", f"SIP INVITE (Auth) -> {target}"), False)
                    resp = s.recv(8192).decode("utf-8", errors="replace")

                # 3. Bucle de recepción de respuestas de llamada
                t_inicio = time.time()
                while time.time() - t_inicio < 25:
                    try:
                        data = s.recv(8192).decode("utf-8", errors="replace")
                    except socket.timeout:
                        continue
                    if not data:
                        continue

                    line = data.splitlines()[0] if data.splitlines() else ""
                    m = re.search(r"SIP/2\.0\s+(\d{3})\s*(.*)", line)
                    if m:
                        code = int(m.group(1))
                        reason = m.group(2)
                        self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{host}:{port}", f"{local_ip}:{lport}", "UDP", line), code >= 400)
                        
                        if code in (180, 183):
                            self.ui_queue.put(("sip_call_status", f"Timbrando en destino ({code})..."))
                        elif code == 200:
                            ack = (
                                f"ACK sip:{target}@{host}:{port} SIP/2.0\r\n"
                                f"Via: SIP/2.0/UDP {local_ip}:{lport};branch=z9hG4bK{uuid.uuid4().hex[:10]};rport\r\n"
                                "Max-Forwards: 70\r\n"
                                f"From: <sip:{user}@{host}>;tag={call_tag}\r\n"
                                f"To: <sip:{target}@{host}>\r\n"
                                f"Call-ID: {call_id}\r\n"
                                f"CSeq: {self.raw_sip_cseq} ACK\r\n"
                                "Content-Length: 0\r\n\r\n"
                            )
                            s.send(ack.encode("utf-8"))
                            self.ui_queue.put(("sip_call_status", "Llamada conectada (En curso)"))
                            break
                        elif code >= 400:
                            self.ui_queue.put(("sip_call_disconnected", f"Rechazada: {code} {reason}"))
                            break
            except Exception as exc:
                self.ui_queue.put(("sip_call_disconnected", f"Fallo al conectar: {exc}"))
            finally:
                self.ui_queue.put(("enable_call_btn", None))
        self._run_bg(task)

    def _sip_hangup_clicked(self) -> None:
        def task():
            try:
                if self.sip_call is not None and PJSUA2_AVAILABLE:
                    self.sip_call.hangup(pj.CallOpParam())
                elif self.raw_sip_socket is not None:
                    host = self.sip_host_var.get().strip()
                    user = self.sip_user_var.get().strip() or "1001"
                    target = self.sip_dest_var.get().strip() or "1002"
                    try:
                        local_ip, lport = self.raw_sip_socket.getsockname()[:2]
                        bye = (
                            f"BYE sip:{target}@{host} SIP/2.0\r\n"
                            f"Via: SIP/2.0/UDP {local_ip}:{lport};branch=z9hG4bK{uuid.uuid4().hex[:10]};rport\r\n"
                            "Max-Forwards: 70\r\n"
                            f"From: <sip:{user}@{host}>\r\n"
                            f"To: <sip:{target}@{host}>\r\n"
                            f"Call-ID: {getattr(self, 'raw_sip_call_id', '123')}\r\n"
                            f"CSeq: 2 BYE\r\n"
                            "Content-Length: 0\r\n\r\n"
                        )
                        self.raw_sip_socket.send(bye.encode("utf-8"))
                        self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{lport}", f"{host}", "UDP", "SIP BYE"), False)
                    except Exception:
                        pass
                    try:
                        self.raw_sip_socket.close()
                    except Exception:
                        pass
                    self.raw_sip_socket = None
                self.ui_queue.put(("sip_call_disconnected", "Llamada finalizada"))
            except Exception as exc:
                self.ui_queue.put(("sip_call_disconnected", f"Cerrada ({exc})"))
        self._run_bg(task)
        def task():
            if PJSUA2_AVAILABLE and self.sip_endpoint is not None and self.sip_account is not None:
                try:
                    target = self.sip_dest_var.get().strip() or "1002"
                    host = self.sip_host_var.get().strip()
                    try:
                        port = int(self.sip_port_var.get().strip() or "5060")
                    except ValueError:
                        port = 5060
                    uri = target if target.lower().startswith("sip:") else f"sip:{target}@{host}:{port}"
                    call = _HmiSipCall(
                        self.sip_account, self.sip_endpoint,
                        lambda kind, data: self.ui_queue.put((kind, data))
                    )
                    self.sip_call = call
                    call.makeCall(uri, pj.CallOpParam(True))
                    self.ui_queue.put(("sip_call_status", f"Llamando a {uri}"))
                except Exception as exc:
                    self.sip_call = None
                    self.ui_queue.put(("sip_tool_status", f"No se pudo iniciar la llamada: {exc}"))
                    self.ui_queue.put(("sip_call_disconnected", "error"))
                return

            # Fallback Nativo SIP 2.0 INVITE con bucle de señalización y ACK
            try:
                user = self.sip_user_var.get().strip() or "1001"
                target = self.sip_dest_var.get().strip() or "1002"
                host = self.sip_host_var.get().strip()
                try:
                    port = int(self.sip_port_var.get().strip() or "5060")
                except ValueError:
                    port = 5060
                if self.raw_sip_socket is None:
                    self.raw_sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s = self.raw_sip_socket
                s.settimeout(1.5)
                local_ip, lport = s.getsockname()[:2]
                self.raw_sip_cseq += 1
                cseq_num = self.raw_sip_cseq
                call_tag = uuid.uuid4().hex[:8]
                branch = "z9hG4bK" + uuid.uuid4().hex[:10]

                # SDP compatible con audio estándar PCMU (G.711u)
                sdp = (
                    "v=0\r\n"
                    f"o={user} 8000 8000 IN IP4 {local_ip}\r\n"
                    "s=MIP1000\r\n"
                    f"c=IN IP4 {local_ip}\r\n"
                    "t=0 0\r\n"
                    "m=audio 40000 RTP/AVP 0 101\r\n"
                    "a=rtpmap:0 PCMU/8000\r\n"
                    "a=rtpmap:101 telephone-event/8000\r\n"
                    "a=sendrecv\r\n"
                )
                inv = (
                    f"INVITE sip:{target}@{host}:{port} SIP/2.0\r\n"
                    f"Via: SIP/2.0/UDP {local_ip}:{lport};branch={branch};rport\r\n"
                    "Max-Forwards: 70\r\n"
                    f"From: <sip:{user}@{host}>;tag={call_tag}\r\n"
                    f"To: <sip:{target}@{host}>\r\n"
                    f"Call-ID: {self.raw_sip_call_id}\r\n"
                    f"CSeq: {cseq_num} INVITE\r\n"
                    f"Contact: <sip:{user}@{local_ip}:{lport}>\r\n"
                    "Content-Type: application/sdp\r\n"
                    f"Content-Length: {len(sdp)}\r\n\r\n"
                    f"{sdp}"
                )
                s.sendto(inv.encode("utf-8"), (host, port))
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{lport}", f"{host}:{port}", "UDP", f"SIP INVITE -> {target}"), False)
                self.ui_queue.put(("sip_call_status", f"Llamando a {target}..."))

                # Bucle de escucha de eventos SIP (Ringing, OK, Errores)
                t_start = time.time()
                while time.time() - t_start < 30:
                    try:
                        resp = s.recv(8192).decode("utf-8", errors="replace")
                    except socket.timeout:
                        continue

                    if not resp:
                        continue

                    first = resp.splitlines()[0].strip() if resp.splitlines() else ""
                    m_code = re.search(r"SIP/2\.0\s+(\d{3})\s*(.*)", first)
                    if m_code:
                        code = int(m_code.group(1))
                        reason = m_code.group(2)
                        self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{host}:{port}", f"{local_ip}:{lport}", "UDP", first), code >= 400)
                        self.ui_queue.put(("sip_call_status", f"{code} — {reason}"))

                        if code == 180 or code == 183:
                            self.ui_queue.put(("sip_call_status", "Timbrando en destino (180 Ringing)..."))
                        elif code == 200:
                            # Extraer To-tag para confirmar con ACK
                            to_header = re.search(r"^To:.*", resp, re.MULTILINE | re.IGNORECASE)
                            to_str = to_header.group(0).replace("To: ", "").strip() if to_header else f"<sip:{target}@{host}>"
                            ack = (
                                f"ACK sip:{target}@{host}:{port} SIP/2.0\r\n"
                                f"Via: SIP/2.0/UDP {local_ip}:{lport};branch=z9hG4bK{uuid.uuid4().hex[:10]};rport\r\n"
                                "Max-Forwards: 70\r\n"
                                f"From: <sip:{user}@{host}>;tag={call_tag}\r\n"
                                f"To: {to_str}\r\n"
                                f"Call-ID: {self.raw_sip_call_id}\r\n"
                                f"CSeq: {cseq_num} ACK\r\n"
                                "Content-Length: 0\r\n\r\n"
                            )
                            s.sendto(ack.encode("utf-8"), (host, port))
                            self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{lport}", f"{host}:{port}", "UDP", "SIP ACK (Llamada establecida)"), False)
                            self.ui_queue.put(("sip_call_status", "Llamada conectada (En curso)"))
                            break
                        elif code >= 400:
                            self.ui_queue.put(("sip_call_disconnected", f"Rechazada: {code} {reason}"))
                            break
            except Exception as exc:
                self.ui_queue.put(("sip_call_disconnected", f"Fallo al llamar: {exc}"))
    def _cmd_check_dest_status(self) -> None:
        """Prueba de ping SIP (OPTIONS) para verificar si la extensión destino responde en la PBX."""
        target = self.sip_dest_var.get().strip()
        host = self.sip_host_var.get().strip()
        port = int(self.sip_port_var.get().strip() or "5060")
        user = self.sip_user_var.get().strip() or "1001"
        if not target or not host:
            messagebox.showwarning("Verificar Destino", "Complete servidor y extensión destino.")
            return

        self.lbl_call_status.config(text=f"Verificando disponibilidad de extensión {target}…", fg="#2b6cb0")

        def task():
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2.5)
                sock.connect((host, port))
                local_ip, lport = sock.getsockname()[:2]
                call_id = f"{uuid.uuid4().hex[:12]}@{local_ip}"
                req = (
                    f"OPTIONS sip:{target}@{host}:{port} SIP/2.0\r\n"
                    f"Via: SIP/2.0/UDP {local_ip}:{lport};branch=z9hG4bK{uuid.uuid4().hex[:10]};rport\r\n"
                    "Max-Forwards: 70\r\n"
                    f"From: <sip:{user}@{host}>;tag={uuid.uuid4().hex[:8]}\r\n"
                    f"To: <sip:{target}@{host}>\r\n"
                    f"Call-ID: {call_id}\r\n"
                    "CSeq: 1 OPTIONS\r\n"
                    f"Contact: <sip:{user}@{local_ip}:{lport}>\r\n"
                    "Accept: application/sdp\r\n"
                    "Content-Length: 0\r\n\r\n"
                )
                sock.send(req.encode("utf-8"))
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{local_ip}:{lport}", f"{host}:{port}", "UDP", f"OPTIONS Check -> {target}"), False)
                
                resp = sock.recv(8192).decode("utf-8", errors="replace")
                first = resp.splitlines()[0] if resp.splitlines() else "Sin respuesta"
                is_ok = "200 OK" in first
                self._capture_emit((datetime.now().strftime("%H:%M:%S"), f"{host}:{port}", f"{local_ip}:{lport}", "UDP", first), not is_ok)
                
                if is_ok:
                    msg = f"✅ Extensión {target} disponible y respondiendo (200 OK)."
                else:
                    msg = f"Respuesta de central: {first}"
                self.ui_queue.put(("sip_call_status", msg))
            except socket.timeout:
                self.ui_queue.put(("sip_call_status", f"Timeout: Sin respuesta al verificar {target}."))
            except Exception as e:
                self.ui_queue.put(("sip_call_status", f"Error al verificar extensión: {e}"))
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
        self._run_bg(task)
    def _sip_hangup_clicked(self) -> None:
        def task():
            try:
                if self.sip_call is not None and PJSUA2_AVAILABLE:
                    self.sip_call.hangup(pj.CallOpParam())
                elif self.raw_sip_socket is not None:
                    host = self.sip_host_var.get().strip()
                    user = self.sip_user_var.get().strip() or "1001"
                    target = self.sip_dest_var.get().strip() or "1002"
                    local_ip, lport = self.raw_sip_socket.getsockname()[:2]
                    self.raw_sip_cseq += 1
                    bye = (
                        f"BYE sip:{target}@{host} SIP/2.0\r\n"
                        f"Via: SIP/2.0/UDP {local_ip}:{lport};branch=z9hG4bK{uuid.uuid4().hex[:10]};rport\r\n"
                        "Max-Forwards: 70\r\n"
                        f"From: <sip:{user}@{host}>;tag={uuid.uuid4().hex[:8]}\r\n"
                        f"To: <sip:{target}@{host}>\r\n"
                        f"Call-ID: {self.raw_sip_call_id}\r\n"
                        f"CSeq: {self.raw_sip_cseq} BYE\r\n"
                        "Content-Length: 0\r\n\r\n"
                    )
                    self.raw_sip_socket.send(bye.encode("utf-8"))
                    self.ui_queue.put(("sip_call_disconnected", "BYE enviado"))
                else:
                    self.ui_queue.put(("sip_call_disconnected", "sin llamada activa"))
            except Exception as exc:
                self.ui_queue.put(("sip_call_disconnected", f"Cerrada ({exc})"))
        self._run_bg(task)

    def _capture_start_clicked(self) -> None:
        if self.capture_thread is not None and self.capture_thread.is_alive():
            return
        bpf = self.capture_filter_var.get().strip()
        if not bpf:
            messagebox.showwarning("Captura", "Ingrese un filtro BPF o use el filtro predeterminado.")
            return
        self.capture_stop_event.clear()
        self.capture_packet_count = 0
        self.btn_capture_start.config(state="disabled")
        self.btn_capture_stop.config(state="normal")
        self.lbl_capture_status.config(text="Iniciando captura en vivo...")
        interface = self.capture_interface_var.get().strip() or None
        self.capture_thread = threading.Thread(
            target=self._capture_worker, args=(interface, bpf), daemon=True
        )
        self.capture_thread.start()

    def _capture_stop_clicked(self) -> None:
        self.capture_stop_event.set()
        try:
            if self.capture_handle is not None:
                self.capture_handle.close()
        except Exception:
            pass
        self.btn_capture_stop.config(state="disabled")
        self.btn_capture_start.config(state="normal")
        self.lbl_capture_status.config(text="Deteniendo captura…")

    def _capture_clear(self) -> None:
        for item in self.tree_capture.get_children():
            self.tree_capture.delete(item)
        self.capture_packet_count = 0
        self.lbl_capture_count.config(text="Paquetes mostrados: 0")

    @staticmethod
    def _packet_error_level(detail: str) -> bool:
        return bool(re.search(r"\b(?:SIP\s+)?(?:4\d\d|5\d\d|6\d\d)\b", detail, re.IGNORECASE))

    def _capture_emit(self, values, is_error=False) -> None:
        self.ui_queue.put(("capture_row", (values, is_error)))

    # Función _capture_worker corregida SIN 'return' dentro de 'finally'
    def _capture_worker(self, interface, bpf):
        pyshark_completed = False
        if PYSHARK_AVAILABLE:
            capture = None
            try:
                kwargs = {"bpf_filter": bpf}
                if interface:
                    kwargs["interface"] = interface
                capture = pyshark.LiveCapture(**kwargs)
                self.capture_handle = capture
                self.ui_queue.put(("capture_status", "Captura activa mediante PyShark/TShark."))
                for packet in capture.sniff_continuously():
                    if self.capture_stop_event.is_set():
                        break
                    stamp = str(getattr(packet, "sniff_time", datetime.now().strftime("%H:%M:%S")))
                    if " " in stamp:
                        stamp = stamp.split(" ")[-1]
                    src = dst = "?"
                    for layer in ("ip", "ipv6"):
                        try:
                            obj = getattr(packet, layer)
                            src, dst = str(obj.src), str(obj.dst)
                            break
                        except Exception:
                            continue
                    proto = str(getattr(packet, "transport_layer", "?"))
                    try:
                        src_port = str(packet[proto].srcport)
                        dst_port = str(packet[proto].dstport)
                        src = f"{src}:{src_port}"
                        dst = f"{dst}:{dst_port}"
                    except Exception:
                        pass
                    detail = str(getattr(packet, "highest_layer", proto))
                    try:
                        sip = packet.sip
                        code = str(getattr(sip, "Status_Code", "") or "")
                        method = str(getattr(sip, "Request_Method", "") or "")
                        reason = str(getattr(sip, "Reason_Phrase", "") or "")
                        if code:
                            detail = f"SIP {code} {reason}".strip()
                        elif method:
                            detail = f"SIP {method}"
                    except Exception:
                        if "rtp" in detail.lower():
                            detail = "RTP media"
                    is_error = self._packet_error_level(detail)
                    self._capture_emit((stamp, src, dst, proto, detail), is_error)
                pyshark_completed = True
            except Exception as exc:
                if not self.capture_stop_event.is_set():
                    self.ui_queue.put(("capture_status", f"PyShark no disponible ({exc}); pasando a Scapy/UDP…"))
            finally:
                try:
                    if capture is not None:
                        capture.close()
                except Exception:
                    pass
                self.capture_handle = None

        if pyshark_completed or self.capture_stop_event.is_set():
            self.ui_queue.put(("capture_finished", None))
            return

        scapy_completed = False
        if SCAPY_AVAILABLE and not self.capture_stop_event.is_set():
            try:
                def handle_packet(packet):
                    if self.capture_stop_event.is_set():
                        return
                    stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    src = dst = "?"
                    if IP in packet:
                        src, dst = packet[IP].src, packet[IP].dst
                    elif IPv6 in packet:
                        src, dst = packet[IPv6].src, packet[IPv6].dst
                    proto = "UDP" if UDP in packet else ("TCP" if TCP in packet else "IP")
                    try:
                        if UDP in packet:
                            src = f"{src}:{packet[UDP].sport}"
                            dst = f"{dst}:{packet[UDP].dport}"
                        elif TCP in packet:
                            src = f"{src}:{packet[TCP].sport}"
                            dst = f"{dst}:{packet[TCP].dport}"
                    except Exception:
                        pass
                    detail = "Paquete de red"
                    if Raw in packet:
                        raw = bytes(packet[Raw].load[:600]).decode("utf-8", errors="replace")
                        first = raw.splitlines()[0].strip() if raw.splitlines() else ""
                        match = re.match(r"SIP/2\.0\s+(\d{3})\s*(.*)", first)
                        if match:
                            detail = f"SIP {match.group(1)} {match.group(2)}".strip()
                        elif re.match(r"^(INVITE|REGISTER|OPTIONS|ACK|BYE|CANCEL|INFO|UPDATE|PRACK|NOTIFY|SUBSCRIBE)\s", first, re.I):
                            detail = "SIP " + first.split()[0].upper()
                        elif "RTP" in raw[:80]:
                            detail = "Posible RTP (carga útil)"
                    if UDP in packet and detail == "Paquete de red":
                        try:
                            sport, dport = int(packet[UDP].sport), int(packet[UDP].dport)
                            if 10000 <= sport <= 20000 or 10000 <= dport <= 20000:
                                detail = "UDP media (RTP probable)"
                        except Exception:
                            pass
                    self._capture_emit((stamp, src, dst, proto, detail), self._packet_error_level(detail))
                self.ui_queue.put(("capture_status", "Captura activa mediante Scapy."))
                sniff(
                    iface=interface, filter=bpf, prn=handle_packet, store=False,
                    stop_filter=lambda packet: self.capture_stop_event.is_set()
                )
                scapy_completed = True
            except Exception as exc:
                if not self.capture_stop_event.is_set():
                    self.ui_queue.put(("capture_status", f"Scapy sin Npcap ({exc}); activando escucha UDP SIP local."))

        # Fallback Socket UDP 5060 si no están instalados TShark ni Npcap
        if not scapy_completed and not self.capture_stop_event.is_set():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.bind(("0.0.0.0", 5060))
                sock.settimeout(1.0)
                self.ui_queue.put(("capture_status", "Escucha UDP SIP directa activa en puerto 5060."))
                while not self.capture_stop_event.is_set():
                    try:
                        raw_bytes, addr = sock.recvfrom(4096)
                        txt = raw_bytes.decode("utf-8", errors="replace")
                        first = txt.splitlines()[0].strip() if txt.splitlines() else "Trama UDP"
                        self._capture_emit(
                            (datetime.now().strftime("%H:%M:%S"), f"{addr[0]}:{addr[1]}", "0.0.0.0:5060", "UDP", first),
                            self._packet_error_level(first)
                        )
                    except socket.timeout:
                        continue
            except Exception as exc:
                self.ui_queue.put(("capture_status", f"Monitoreo pasivo de pruebas SIP activo ({exc})."))
                while not self.capture_stop_event.is_set():
                    time.sleep(0.5)
            finally:
                try:
                    sock.close()
                except Exception:
                    pass

        self.capture_handle = None
        self.ui_queue.put(("capture_finished", None))

    # Lógica de Testeo de Puertos con IP Personalizada
    def _cmd_test_port(self) -> None:
        target_ip = self.test_ip_var.get().strip() or self.ip_var.get().strip()
        try:
            port = int(self.test_port_var.get().strip())
        except ValueError:
            messagebox.showwarning("Puerto inválido", "Ingrese un número de puerto válido.")
            return

        self.lbl_port_status.config(text=f"Testeando {target_ip}:{port}...", fg="#d69e2e")

        def task():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            try:
                result = s.connect_ex((target_ip, port))
                s.close()
                if result == 0:
                    self.ui_queue.put(("port_test_result", (True, f"¡Abierto y respondiendo en {target_ip}:{port}!")))
                else:
                    self.ui_queue.put(("port_test_result", (False, f"Cerrado o sin respuesta en {target_ip}:{port}.")))
            except Exception as e:
                self.ui_queue.put(("port_test_result", (False, f"Error de red: {e}")))

        self._run_bg(task)

    # Control de Streams RTSP con diagnóstico explícito en consola y visor
    def _connect_rtsp_1(self) -> None:
        url = self.rtsp1_var.get().strip()
        if not OPENCV_AVAILABLE:
            messagebox.showerror("Error", "La librería opencv-python no está instalada. Ejecute: pip install opencv-python pillow")
            return
        if self.rtsp1_running:
            self._disconnect_rtsp_1()

        self.lbl_cam1.config(image="", text="Conectando RTSP Cam 1...", fg="#ecc94b")
        self.client.log(f"Iniciando streaming RTSP 1: {self._mask_rtsp_url(url)}")
        self.rtsp1_running = True
        threading.Thread(target=self._stream_rtsp_worker, args=(url, 1), daemon=True).start()

    def _disconnect_rtsp_1(self) -> None:
        self.rtsp1_running = False
        self.lbl_cam1.config(image="", text="[ Camara 1 Desconectada ]", fg="#a0aec0")
        self.client.log("Streaming RTSP 1 detenido.")

    def _connect_rtsp_2(self) -> None:
        url = self.rtsp2_var.get().strip()
        if not OPENCV_AVAILABLE:
            messagebox.showerror("Error", "La librería opencv-python no está instalada. Ejecute: pip install opencv-python pillow")
            return
        if self.rtsp2_running:
            self._disconnect_rtsp_2()

        self.lbl_cam2.config(image="", text="Conectando RTSP Cam 2...", fg="#ecc94b")
        self.client.log(f"Iniciando streaming RTSP 2: {self._mask_rtsp_url(url)}")
        self.rtsp2_running = True
        threading.Thread(target=self._stream_rtsp_worker, args=(url, 2), daemon=True).start()

    def _disconnect_rtsp_2(self) -> None:
        self.rtsp2_running = False
        self.lbl_cam2.config(image="", text="[ Camara 2 Desconectada ]", fg="#a0aec0")
        self.client.log("Streaming RTSP 2 detenido.")

    def _stream_rtsp_worker(self, url: str, cam_id: int) -> None:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(url)
        container = self.cam1_container if cam_id == 1 else self.cam2_container
        lbl = self.lbl_cam1 if cam_id == 1 else self.lbl_cam2

        if not cap.isOpened():
            self.ui_queue.put(("log", f"[ERROR RTSP Cam {cam_id}] No se pudo abrir el stream. Verifique IP, puerto 554, credenciales o que la cámara use códec H.264."))
            self.ui_queue.put(("rtsp_error", (cam_id, "[ Error RTSP: Verifique IP / Puerto 554 / Códec H.264 ]")))
            cap.release()
            return

        fail_count = 0
        while True:
            is_running = self.rtsp1_running if cam_id == 1 else self.rtsp2_running
            if not is_running:
                break

            ret, frame = cap.read()
            if ret and frame is not None:
                fail_count = 0
                h, w = frame.shape[:2]
                target_w = max(260, container.winfo_width() - 6)
                target_h = max(115, container.winfo_height() - 6)
                scale = min(target_w / w, target_h / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))

                frame_resized = cv2.resize(frame, (new_w, new_h))
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)

                if cam_id == 1 and self.rtsp1_running:
                    lbl.imgtk = imgtk
                    lbl.config(image=imgtk, text="")
                elif cam_id == 2 and self.rtsp2_running:
                    lbl.imgtk = imgtk
                    lbl.config(image=imgtk, text="")
            else:
                fail_count += 1
                if fail_count > 60:
                    self.ui_queue.put(("log", f"[ERROR RTSP Cam {cam_id}] Stream sin cuadros decodificables (verifique que el canal RTSP esté en H.264 y no H.265)."))
                    self.ui_queue.put(("rtsp_error", (cam_id, "[ Sin video: Cambie cámara a H.264 ]")))
                    break
                time.sleep(0.05)
        cap.release()

    def _cmd_open_xre_door(self, dev_addr: int) -> None:
        self.client.log(f"Enviando comando ASR al XRE 1000 Plus en dirección RS-485 {dev_addr}...")
        self._run_bg(lambda: self.client.trigger_remote_output(dev_addr, 1))

    # Pestaña 2: Crear Usuario (Con barra inferior anclada y 24 dispositivos)
    def _build_tab_create_user(self) -> None:
        t = I18N[self.lang]

        self.lbl_create_status = tk.Label(
            self.tab_create, text="Listo para enviar datos al MIP 1000 IP.",
            bg="#e2e8f0", fg="#1a202c", font=("Consolas", 10, "bold"), pady=5,
        )
        self.lbl_create_status.pack(side="bottom", fill="x", padx=5, pady=(2, 0))

        action_bar = tk.Frame(self.tab_create, bg="#f8fafc", pady=6)
        action_bar.pack(side="bottom", fill="x")

        self.btn_send_all = self._textured_button(action_bar, t["btn_send_all"], self._cmd_send_full_user, color="green")
        self.btn_send_all.pack(side="left", fill="x", expand=True, padx=6)

        self.btn_goto_edit = self._textured_button(action_bar, t["btn_goto_edit"], self._jump_to_edit_tab, color="blue")
        self.btn_goto_edit.pack(side="left", padx=6)

        self.btn_clear_form = self._textured_button(action_bar, t["btn_clear_form"], self._clear_user_form, color="gray")
        self.btn_clear_form.pack(side="left", padx=6)

        cols_frame = tk.Frame(self.tab_create, bg="#f8fafc")
        cols_frame.pack(side="top", fill="both", expand=True)
        for c in range(3):
            cols_frame.columnconfigure(c, weight=1)
        cols_frame.rowconfigure(0, weight=1)

        self.u_personal_box = tk.LabelFrame(cols_frame, text=t["u_personal"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        self.u_personal_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)
        self.u_personal_box.columnconfigure(1, weight=1)

        self._info_label(
            self.u_personal_box,
            "ID=0 asigna el primer ID libre automáticamente."
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        self.f_uid_var = tk.StringVar(value="0")
        self.f_nome_var = tk.StringVar(value="")
        self.f_apto_var = tk.StringVar(value="101")
        self.f_bloco_var = tk.StringVar(value="A")
        self.f_cpf_var = tk.StringVar(value="")
        self.f_rg_var = tk.StringVar(value="")
        self.f_email_var = tk.StringVar(value="")
        self.f_tel_res_var = tk.StringVar(value="")
        self.f_tel_cel_var = tk.StringVar(value="")

        fields_col1 = [
            ("ID Usuario (0 = Automatico):", self.f_uid_var),
            ("Nombre Completo (max 34):", self.f_nome_var),
            ("Apartamento / Casa (max 5):", self.f_apto_var),
            ("Bloque / Torre (max 5):", self.f_bloco_var),
            ("CPF / Identificacion (solo num):", self.f_cpf_var),
            ("RG / Documento (solo num):", self.f_rg_var),
            ("E-mail (max 34):", self.f_email_var),
            ("Telefono Fijo (solo num):", self.f_tel_res_var),
            ("Telefono Celular (solo num):", self.f_tel_cel_var),
        ]
        for idx, (label_txt, var) in enumerate(fields_col1, start=1):
            tk.Label(self.u_personal_box, text=label_txt, bg="#f8fafc").grid(row=idx, column=0, sticky="w", pady=2)
            ttk.Entry(self.u_personal_box, textvariable=var, width=24).grid(row=idx, column=1, pady=2, padx=4, sticky="ew")

        self.u_access_box = tk.LabelFrame(cols_frame, text=t["u_access"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        self.u_access_box.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)
        self.u_access_box.columnconfigure(1, weight=1)

        self._info_label(
            self.u_access_box,
            "Marque los dispositivos RS-485 (1 al 24) con permiso."
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        tk.Label(self.u_access_box, text="Categoria:", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=2)
        self.f_cat_var = tk.StringVar(value="0 - Morador (Residente)")
        ttk.Combobox(
            self.u_access_box, textvariable=self.f_cat_var,
            values=["0 - Morador (Residente)", "1 - Prestador de Servicio", "2 - Visitante"],
            width=23, state="readonly",
        ).grid(row=1, column=1, pady=2, padx=4, sticky="ew")

        tk.Label(self.u_access_box, text="Nivel Acceso (1..4):", bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=2)
        self.f_nivel_var = tk.IntVar(value=1)
        ttk.Spinbox(self.u_access_box, from_=1, to=4, textvariable=self.f_nivel_var, width=8).grid(row=2, column=1, sticky="w", pady=2, padx=4)

        tk.Label(self.u_access_box, text="Senha Teclado (3 digitos):", bg="#f8fafc").grid(row=3, column=0, sticky="w", pady=2)
        self.f_senha3_var = tk.StringVar(value="")
        ttk.Entry(self.u_access_box, textvariable=self.f_senha3_var, width=12).grid(row=3, column=1, sticky="w", pady=2, padx=4)

        tk.Label(self.u_access_box, text="Senha Secundaria (4-6 dig):", bg="#f8fafc").grid(row=4, column=0, sticky="w", pady=2)
        self.f_senhasec_var = tk.StringVar(value="")
        ttk.Entry(self.u_access_box, textvariable=self.f_senhasec_var, width=12).grid(row=4, column=1, sticky="w", pady=2, padx=4)

        tk.Label(self.u_access_box, text="Dispositivos Liberados RS-485 (24 Soportados):", bg="#f8fafc", font=("Segoe UI", 8, "bold")).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(6, 2)
        )
        disp_frame = tk.Frame(self.u_access_box, bg="#f8fafc")
        disp_frame.grid(row=6, column=0, columnspan=2, sticky="w")
        self.disp_vars: Dict[int, tk.BooleanVar] = {}
        for d in range(1, 25):
            v = tk.BooleanVar(value=(d in (1, 2)))
            self.disp_vars[d] = v
            tk.Checkbutton(disp_frame, text=f"D{d}", variable=v, bg="#f8fafc", font=("Segoe UI", 8)).grid(
                row=(d - 1) // 6, column=(d - 1) % 6, sticky="w", padx=2, pady=1
            )

        self.u_media_box = tk.LabelFrame(cols_frame, text=t["u_media"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        self.u_media_box.grid(row=0, column=2, sticky="nsew", padx=4, pady=2)
        self.u_media_box.columnconfigure(1, weight=1)

        self._info_label(
            self.u_media_box,
            "Presione 'Capturar' y acerque la credencial al MIP."
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        self.f_tag_code_var = tk.StringVar(value="")
        self.f_rf_code_var = tk.StringVar(value="")
        self.f_rf_ts_var = tk.IntVar(value=0)
        self.f_placa_var = tk.StringVar(value="")
        self.f_marca_var = tk.StringVar(value="")
        self.f_modelo_var = tk.StringVar(value="")
        self.f_cor_var = tk.StringVar(value="")

        tk.Label(self.u_media_box, text="Codigo TAG RFID (Hex/Dec):", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(self.u_media_box, textvariable=self.f_tag_code_var, width=20).grid(row=1, column=1, pady=2, sticky="ew")
        self.btn_read_tag_form = self._textured_button(self.u_media_box, t["btn_read_tag_form"], self._cmd_capture_tag_to_form, color="orange")
        self.btn_read_tag_form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)

        tk.Label(self.u_media_box, text="Codigo Control RF (XTR):", bg="#f8fafc").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(self.u_media_box, textvariable=self.f_rf_code_var, width=20).grid(row=3, column=1, pady=2, sticky="ew")
        self.btn_read_rf_form = self._textured_button(self.u_media_box, t["btn_read_rf_form"], self._cmd_capture_rf_to_form, color="orange")
        self.btn_read_rf_form.grid(row=4, column=0, columnspan=2, sticky="ew", pady=2)

        veh_fields = [
            ("Placa Vehiculo (max 7):", self.f_placa_var),
            ("Marca Vehiculo (max 18):", self.f_marca_var),
            ("Modelo Vehiculo (max 18):", self.f_modelo_var),
            ("Color Vehiculo (max 18):", self.f_cor_var),
        ]
        for idx, (lbl, var) in enumerate(veh_fields, start=5):
            tk.Label(self.u_media_box, text=lbl, bg="#f8fafc").grid(row=idx, column=0, sticky="w", pady=2)
            ttk.Entry(self.u_media_box, textvariable=var, width=20).grid(row=idx, column=1, pady=2, sticky="ew")

    # Pestaña 3: Editar Usuario (Con barra inferior fija para que siempre se vea "Guardar Cambios" y los 24 Dispositivos)
    def _build_tab_edit_user(self) -> None:
        t = I18N[self.lang]

        self.lbl_edit_status = tk.Label(
            self.tab_edit, text="Consulte un usuario por su ID o busque por Apartamento para comenzar la edición.",
            bg="#e2e8f0", fg="#1a202c", font=("Consolas", 10, "bold"), pady=5,
        )
        self.lbl_edit_status.pack(side="bottom", fill="x", padx=5, pady=(2, 0))

        edit_action_bar = tk.Frame(self.tab_edit, bg="#f8fafc", pady=6)
        edit_action_bar.pack(side="bottom", fill="x", padx=5)

        self.btn_save_changes = self._textured_button(edit_action_bar, t["btn_save_changes"], self._cmd_save_edited_user, color="green", width=35)
        self.btn_save_changes.pack(side="left", padx=6)

        search_bar = tk.LabelFrame(
            self.tab_edit,
            text=" Buscar Usuario en el MIP para Editar (Por ID o por Apartamento) ",
            bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6
        )
        search_bar.pack(side="top", fill="x", padx=5, pady=2)

        self._info_label(
            search_bar,
            "Puede buscar directamente por ID o ingresar el Apartamento para listar sus residentes registrados y elegir cuál editar."
        ).pack(fill="x", pady=(0, 4))

        row_id = tk.Frame(search_bar, bg="#f8fafc")
        row_id.pack(fill="x", pady=2)

        tk.Label(row_id, text="Opción 1 - ID de Usuario:", bg="#f8fafc", font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)
        self.edit_uid_var = tk.IntVar(value=1)
        ttk.Spinbox(row_id, from_=1, to=99999, textvariable=self.edit_uid_var, width=10).pack(side="left", padx=4)

        self.edit_is_visitor_var = tk.BooleanVar(value=False)
        tk.Checkbutton(row_id, text="Es Visitante / Prestador", variable=self.edit_is_visitor_var, bg="#f8fafc").pack(side="left", padx=10)

        self._textured_button(row_id, "Consultar por ID", self._cmd_fetch_user_to_edit, color="blue").pack(side="left", padx=6)

        row_apto = tk.Frame(search_bar, bg="#f8fafc")
        row_apto.pack(fill="x", pady=(4, 2))

        tk.Label(row_apto, text="Opción 2 - Apartamento:", bg="#f8fafc", font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)
        self.edit_search_apto_var = tk.StringVar(value="101")
        ttk.Entry(row_apto, textvariable=self.edit_search_apto_var, width=8).pack(side="left", padx=4)

        self.btn_search_apto_users = self._textured_button(
            row_apto, "Buscar Residentes del Apto", self._cmd_search_users_by_apto, color="teal"
        )
        self.btn_search_apto_users.pack(side="left", padx=6)

        tk.Label(row_apto, text="Seleccionar Residente:", bg="#f8fafc", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(12, 4))
        self.edit_apto_users_var = tk.StringVar(value="(Busque un Apto primero)")
        self.cb_apto_users = ttk.Combobox(row_apto, textvariable=self.edit_apto_users_var, values=[], width=38, state="readonly")
        self.cb_apto_users.pack(side="left", fill="x", expand=True, padx=4)
        self.cb_apto_users.bind("<<ComboboxSelected>>", self._on_select_apto_user_to_edit)

        form_container = tk.Frame(self.tab_edit, bg="#f8fafc")
        form_container.pack(side="top", fill="both", expand=True, padx=5, pady=2)
        for c in range(2):
            form_container.columnconfigure(c, weight=1)
        form_container.rowconfigure(0, weight=1)

        self.e_personal_box = tk.LabelFrame(form_container, text=t["u_personal"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        self.e_personal_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)
        self.e_personal_box.columnconfigure(1, weight=1)

        self.e_nome_var = tk.StringVar(value="")
        self.e_apto_var = tk.StringVar(value="")
        self.e_bloco_var = tk.StringVar(value="")
        self.e_cpf_var = tk.StringVar(value="")
        self.e_rg_var = tk.StringVar(value="")
        self.e_email_var = tk.StringVar(value="")
        self.e_tel_res_var = tk.StringVar(value="")
        self.e_tel_cel_var = tk.StringVar(value="")

        edit_fields_col1 = [
            ("Nombre Completo (max 34):", self.e_nome_var),
            ("Apartamento / Casa (max 5):", self.e_apto_var),
            ("Bloque / Torre (max 5):", self.e_bloco_var),
            ("CPF / Identificacion:", self.e_cpf_var),
            ("RG / Documento:", self.e_rg_var),
            ("E-mail:", self.e_email_var),
            ("Telefono Fijo:", self.e_tel_res_var),
            ("Telefono Celular:", self.e_tel_cel_var),
        ]
        for idx, (label_txt, var) in enumerate(edit_fields_col1):
            tk.Label(self.e_personal_box, text=label_txt, bg="#f8fafc").grid(row=idx, column=0, sticky="w", pady=2)
            ttk.Entry(self.e_personal_box, textvariable=var, width=25).grid(row=idx, column=1, pady=2, padx=4, sticky="ew")

        self.e_access_box = tk.LabelFrame(form_container, text=t["u_access"], bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        self.e_access_box.grid(row=0, column=1, sticky="nsew", padx=4, pady=2)
        self.e_access_box.columnconfigure(1, weight=1)

        tk.Label(self.e_access_box, text="Categoria:", bg="#f8fafc").grid(row=0, column=0, sticky="w", pady=2)
        self.e_cat_var = tk.StringVar(value="0 - Morador (Residente)")
        ttk.Combobox(
            self.e_access_box, textvariable=self.e_cat_var,
            values=["0 - Morador (Residente)", "1 - Prestador de Servicio", "2 - Visitante"],
            width=23, state="readonly",
        ).grid(row=0, column=1, pady=2, padx=4, sticky="ew")

        tk.Label(self.e_access_box, text="Nivel Acceso (1..4):", bg="#f8fafc").grid(row=1, column=0, sticky="w", pady=2)
        self.e_nivel_var = tk.IntVar(value=1)
        ttk.Spinbox(self.e_access_box, from_=1, to=4, textvariable=self.e_nivel_var, width=8).grid(row=1, column=1, sticky="w", pady=2, padx=4)

        tk.Label(self.e_access_box, text="Senha Teclado (3 digitos):", bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=2)
        self.e_senha3_var = tk.StringVar(value="")
        ttk.Entry(self.e_access_box, textvariable=self.e_senha3_var, width=12).grid(row=2, column=1, sticky="w", pady=2, padx=4)

        tk.Label(self.e_access_box, text="Senha Secundaria:", bg="#f8fafc").grid(row=3, column=0, sticky="w", pady=2)
        self.e_senhasec_var = tk.StringVar(value="")
        ttk.Entry(self.e_access_box, textvariable=self.e_senhasec_var, width=12).grid(row=3, column=1, sticky="w", pady=2, padx=4)

        tk.Label(
            self.e_access_box,
            text="Dispositivos Liberados RS-485 (24 Dispositivos Soportados por MIP 1000 IP):",
            bg="#f8fafc", font=("Segoe UI", 8, "bold")
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 2))

        edisp_frame = tk.Frame(self.e_access_box, bg="#f8fafc")
        edisp_frame.grid(row=5, column=0, columnspan=2, sticky="w")
        self.edisp_vars: Dict[int, tk.BooleanVar] = {}
        for d in range(1, 25):
            v = tk.BooleanVar(value=(d in (1, 2)))
            self.edisp_vars[d] = v
            tk.Checkbutton(edisp_frame, text=f"Disp {d}", variable=v, bg="#f8fafc", font=("Segoe UI", 8)).grid(
                row=(d - 1) // 6, column=(d - 1) % 6, sticky="w", padx=3, pady=1
            )

    # Pestaña 4: Plantillas
    def _build_tab_templates(self) -> None:
        t = I18N[self.lang]
        self.tpl_box = tk.LabelFrame(self.tab_tpl, text=t["tpl_box"], bg="#f8fafc", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        self.tpl_box.pack(fill="both", expand=True, padx=6, pady=4)

        self._info_label(
            self.tpl_box,
            "Las plantillas permiten preconfigurar perfiles de residentes o visitantes para agilizar el alta de usuarios."
        ).pack(fill="x", pady=(0, 6))

        top_row = tk.Frame(self.tpl_box, bg="#f8fafc")
        top_row.pack(fill="x", pady=4)

        tk.Label(top_row, text="Plantilla:", bg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        self.tpl_select_var = tk.StringVar(value=list(self.templates.keys())[0])
        self.cb_templates = ttk.Combobox(top_row, textvariable=self.tpl_select_var, values=list(self.templates.keys()), width=45, state="readonly")
        self.cb_templates.pack(side="left", padx=6)
        self.cb_templates.bind("<<ComboboxSelected>>", self._on_template_preview)

        tk.Label(top_row, text="Guardar Nueva:", bg="#f8fafc").pack(side="left", padx=(15, 4))
        self.new_tpl_name_var = tk.StringVar(value="Mi Plantilla")
        ttk.Entry(top_row, textvariable=self.new_tpl_name_var, width=20).pack(side="left", padx=4)

        btn_bar = tk.Frame(self.tpl_box, bg="#f8fafc")
        btn_bar.pack(side="bottom", fill="x", pady=6)

        self.btn_apply_tpl = self._textured_button(btn_bar, t["btn_apply_tpl"], self._apply_selected_template_to_form, color="blue")
        self.btn_apply_tpl.pack(side="left", padx=6)

        self.btn_apply_and_send = self._textured_button(btn_bar, t["btn_apply_and_send"], self._apply_and_send_template_now, color="green")
        self.btn_apply_and_send.pack(side="left", padx=6)

        self.btn_save_tpl = self._textured_button(btn_bar, t["btn_save_tpl"], self._save_current_form_as_template, color="orange")
        self.btn_save_tpl.pack(side="left", padx=6)

        self.txt_tpl_preview = tk.Text(self.tpl_box, height=10, bg="#ffffff", fg="#1a202c", font=("Consolas", 10))
        self.txt_tpl_preview.pack(fill="both", expand=True, pady=6)
        self._on_template_preview()

    # Pestaña 5: Consultas y Lectores
    def _build_tab_search(self) -> None:
        u_box = tk.LabelFrame(self.tab_search, text=" Consultar Usuario Cadastrado - MU (0x01) ", bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=10)
        u_box.pack(fill="x", pady=6)

        self._info_label(
            u_box,
            "Consulte un registro puntual en la memoria del MIP indicando su ID y si pertenece a la tabla de visitantes."
        ).grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 6))

        tk.Label(u_box, text="ID del Usuario:", bg="#f8fafc").grid(row=1, column=0, padx=4)
        self.search_uid_var = tk.IntVar(value=1)
        ttk.Spinbox(u_box, from_=1, to=99999, textvariable=self.search_uid_var, width=10).grid(row=1, column=1, padx=4)

        self.is_visitor_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(u_box, text="Es Visitante / Prestador", variable=self.is_visitor_var).grid(row=1, column=2, padx=10)

        self._textured_button(u_box, "Buscar Usuario", self._cmd_search_user, color="blue").grid(row=1, column=3, padx=6)

        self.lbl_user_result = tk.Label(u_box, text="Resultado: (Sin consulta)", bg="#f8fafc", font=("Consolas", 10))
        self.lbl_user_result.grid(row=2, column=0, columnspan=4, sticky="w", pady=8)

        read_box = tk.LabelFrame(self.tab_search, text=" Captura Directa de Tarjetas RFID (LT - 0x1C) y Controles RF (RF - 0x26) ", bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=10)
        read_box.pack(fill="x", pady=6)

        self._info_label(
            read_box,
            "Pone al MIP 1000 IP en modo lectura para identificar el código hexadecimal de un TAG o Control RF."
        ).pack(fill="x", pady=(0, 6))

        btn_row = tk.Frame(read_box, bg="#f8fafc")
        btn_row.pack(fill="x", pady=4)

        self._textured_button(btn_row, "Leer TAG RFID en MIP (0x1C)", self._cmd_read_tag, color="orange").pack(side="left", padx=6)
        self._textured_button(btn_row, "Leer Control RF XTR (0x26)", self._cmd_read_rf, color="orange").pack(side="left", padx=6)

        self.captured_code_var = tk.StringVar(value="Esperando lectura...")
        ttk.Entry(read_box, textvariable=self.captured_code_var, font=("Consolas", 11, "bold"), state="readonly").pack(fill="x", pady=6)

    # Pestaña 6: Eventos por Apartamento
    def _build_tab_events(self) -> None:
        self._info_label(
            self.tab_events,
            "Filtre los eventos de acceso por número de apartamento (deje vacío para traer todos). Puede exportar la tabla a Excel (.csv) o texto (.txt)."
        ).pack(fill="x", pady=(0, 4))

        top_bar = tk.Frame(self.tab_events, bg="#f8fafc", pady=4)
        top_bar.pack(fill="x")

        tk.Label(top_bar, text="Filtrar por Apartamento:", bg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        self.ev_apto_var = tk.StringVar(value="101")
        ttk.Entry(top_bar, textvariable=self.ev_apto_var, width=10).pack(side="left", padx=4)

        self.btn_ev_today = self._textured_button(top_bar, "Traer Eventos de Hoy", self._cmd_get_events_today, color="blue")
        self.btn_ev_today.pack(side="left", padx=8)

        self.btn_ev_week = self._textured_button(top_bar, "Traer Eventos de la Semana", self._cmd_get_events_week, color="green")
        self.btn_ev_week.pack(side="left", padx=4)

        self._textured_button(
            top_bar, "📊 Exportar a Excel (.csv)",
            lambda: self._export_tree_to_csv(self.tree_ev, "Eventos_Apartamento"), color="green"
        ).pack(side="right", padx=4)

        self._textured_button(
            top_bar, "Exportar a .txt",
            lambda: self._export_tree_to_txt(self.tree_ev, "Eventos_Apartamento"), color="orange"
        ).pack(side="right", padx=4)

        prog_bar_frame = tk.Frame(self.tab_events, bg="#f8fafc", pady=2)
        prog_bar_frame.pack(fill="x")

        self.ev_progress = ttk.Progressbar(prog_bar_frame, orient="horizontal", length=480, mode="determinate")
        self.ev_progress.pack(side="left", padx=4)

        self.lbl_ev_status = tk.Label(
            prog_bar_frame, text="Estado: Listo para consultar eventos.",
            bg="#f8fafc", fg="#2b6cb0", font=("Segoe UI", 9, "bold")
        )
        self.lbl_ev_status.pack(side="left", padx=10)

        cols = ("id", "fecha", "evento", "recurso", "disp", "salida", "usuario", "apto", "bloco", "placa")
        self.tree_ev = ttk.Treeview(self.tab_events, columns=cols, show="headings", height=12)
        headers = {
            "id": ("ID", 55), "fecha": ("Fecha y Hora", 130), "evento": ("Tipo de Evento", 180),
            "recurso": ("Medio Acceso", 130), "disp": ("Disp", 50), "salida": ("Rele", 45),
            "usuario": ("Nombre Usuario", 180), "apto": ("Apto", 60), "bloco": ("Bloque", 60), "placa": ("Placa", 80)
        }
        for col, (text, width) in headers.items():
            self.tree_ev.heading(col, text=text)
            self.tree_ev.column(col, width=width, anchor="center" if width < 100 else "w", stretch=True)
        self.tree_ev.pack(fill="both", expand=True, pady=4)

    # Pestaña 7: Online (Monitor en tiempo real verdadero + Alerta de Pánico)
    def _build_tab_online(self) -> None:
        self._info_label(
            self.tab_online,
            "Monitoreo en Tiempo Real activo automáticamente al conectar: detecta nuevos eventos y alertas de PÁNICO en el MIP sin intervención manual."
        ).pack(fill="x", pady=(0, 4))

        top_bar = tk.Frame(self.tab_online, bg="#f8fafc", pady=4)
        top_bar.pack(fill="x")

        tk.Label(top_bar, text="Monitor de Eventos en Tiempo Real:", bg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)

        self.lbl_online_indicator = tk.Label(
            top_bar, text="[Escucha en Tiempo Real: INACTIVA]",
            bg="#f8fafc", fg="#c53030", font=("Segoe UI", 9, "bold")
        )
        self.lbl_online_indicator.pack(side="left", padx=10)

        self._textured_button(
            top_bar, "Limpiar Monitor Online",
            lambda: [self.tree_online.delete(i) for i in self.tree_online.get_children()], color="gray"
        ).pack(side="right", padx=4)

        cols_online = ("fecha", "apto", "usuario", "medio_acceso", "evento", "dispositivo")
        self.tree_online = ttk.Treeview(self.tab_online, columns=cols_online, show="headings", height=14)
        headers_online = {
            "fecha": ("Fecha y Hora", 140), "apto": ("Apto", 60), "usuario": ("Usuario", 180),
            "medio_acceso": ("Medio de Acceso", 180), "evento": ("Tipo de Evento", 200), "dispositivo": ("Dispositivo", 80)
        }
        for col, (text, width) in headers_online.items():
            self.tree_online.heading(col, text=text)
            self.tree_online.column(col, width=width, anchor="center" if col in ("apto", "dispositivo") else "w", stretch=True)

        self.tree_online.tag_configure("panic", background="#fed7d7", foreground="#9b2c2c", font=("Segoe UI", 9, "bold"))
        self.tree_online.pack(fill="both", expand=True, pady=4)

    # Pestaña 8: Análisis IA Comportamental
    def _build_tab_ai(self) -> None:
        ai_top = tk.LabelFrame(self.tab_ai, text=" Motor de Inteligencia Artificial - Analisis Historico y Grafico por Apartamento ", bg="#f8fafc", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        ai_top.pack(fill="x", pady=2)

        self._info_label(
            ai_top,
            "Seleccione el Apartamento, el periodo de días a evaluar y la cantidad máxima de eventos recientes a inspeccionar."
        ).pack(fill="x", pady=(0, 4))

        f1 = tk.Frame(ai_top, bg="#f8fafc")
        f1.pack(fill="x", pady=2)

        tk.Label(f1, text="Apartamento:", bg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        self.ai_apto_var = tk.StringVar(value="101")
        ttk.Entry(f1, textvariable=self.ai_apto_var, width=8).pack(side="left", padx=4)

        tk.Label(f1, text="Periodo:", bg="#f8fafc").pack(side="left", padx=(10, 4))
        self.ai_period_var = tk.StringVar(value="Ultimos 7 Dias")
        cb_period = ttk.Combobox(f1, textvariable=self.ai_period_var, values=["Ultimos 3 Dias", "Ultimos 7 Dias", "Ultimos 15 Dias", "Ultimos 30 Dias"], width=15, state="readonly")
        cb_period.pack(side="left", padx=4)

        tk.Label(f1, text="Max Eventos:", bg="#f8fafc").pack(side="left", padx=(10, 4))
        self.ai_range_var = tk.IntVar(value=100)
        ttk.Spinbox(f1, from_=20, to=1000, textvariable=self.ai_range_var, width=7).pack(side="left", padx=4)

        self.btn_run_ai = self._textured_button(f1, "Ejecutar Analisis Inteligente IA", self._cmd_run_ai_analysis, color="purple")
        self.btn_run_ai.pack(side="left", padx=10)

        self.btn_goto_detail = self._textured_button(f1, "Ver Detalle de Medios de Acceso ->", self._jump_to_detail_tab, color="teal")
        self.btn_goto_detail.pack(side="right", padx=4)

        f2 = tk.Frame(ai_top, bg="#f8fafc")
        f2.pack(fill="x", pady=2)

        self.ai_progress = ttk.Progressbar(f2, orient="horizontal", length=500, mode="determinate")
        self.ai_progress.pack(side="left", padx=4)

        self.lbl_ai_status = tk.Label(f2, text="Estado: En espera de analisis...", bg="#f8fafc", fg="#2b6cb0", font=("Segoe UI", 9, "bold"))
        self.lbl_ai_status.pack(side="left", padx=10)

        content_pane = tk.PanedWindow(self.tab_ai, orient="horizontal", sashrelief="raised", bg="#e2e8f0")
        content_pane.pack(fill="both", expand=True, pady=4)

        text_frame = tk.LabelFrame(content_pane, text=" Reporte y Observaciones de Comportamiento (IA) ", bg="#ffffff", font=("Segoe UI", 9, "bold"), padx=5, pady=5)
        content_pane.add(text_frame, width=650, stretch="always")

        self.txt_ai_report = tk.Text(text_frame, wrap="word", bg="#fffaf0", fg="#1a202c", font=("Consolas", 9), padx=8, pady=8)
        self.txt_ai_report.pack(side="left", fill="both", expand=True)
        txt_scroll = ttk.Scrollbar(text_frame, command=self.txt_ai_report.yview)
        txt_scroll.pack(side="right", fill="y")
        self.txt_ai_report.config(yscrollcommand=txt_scroll.set)

        chart_frame = tk.LabelFrame(content_pane, text=" Grafico de Frecuencia Historica por Dia ", bg="#ffffff", font=("Segoe UI", 9, "bold"), padx=5, pady=5)
        content_pane.add(chart_frame, width=480, stretch="always")

        self.chart_canvas = tk.Canvas(chart_frame, bg="#ffffff", highlightthickness=0)
        self.chart_canvas.pack(fill="both", expand=True)
        self.chart_canvas.bind("<Configure>", self._on_chart_resize)
        self._draw_empty_chart()

    # Pestaña 9: Detalle y Medios de Acceso
    def _build_tab_detail(self) -> None:
        self._info_label(
            self.tab_detail,
            "Desglose detallado de cada acceso indicando el medio utilizado (TAG RFID, Control RF XTR, Teclado). Exportable a Excel (.csv)."
        ).pack(fill="x", pady=(0, 4))

        detail_top = tk.Frame(self.tab_detail, bg="#f8fafc", pady=4)
        detail_top.pack(fill="x")

        tk.Label(detail_top, text="Historial detallado de eventos analizados con especificacion de medios de acceso:", bg="#f8fafc", font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)

        self._textured_button(
            detail_top, "📊 Exportar a Excel (.csv)",
            lambda: self._export_tree_to_csv(self.tree_detail, "Detalle_Medios_Acceso"), color="green"
        ).pack(side="right", padx=6)

        self._textured_button(
            detail_top, "Exportar a .txt",
            lambda: self._export_tree_to_txt(self.tree_detail, "Detalle_Medios_Acceso"), color="orange"
        ).pack(side="right", padx=6)

        cols_detail = ("fecha", "apto", "usuario", "medio_acceso", "evento", "dispositivo")
        self.tree_detail = ttk.Treeview(self.tab_detail, columns=cols_detail, show="headings", height=14)
        headers_detail = {
            "fecha": ("Fecha y Hora", 140), "apto": ("Apto", 60), "usuario": ("Usuario", 180),
            "medio_acceso": ("Medio de Acceso Especifico", 180), "evento": ("Tipo de Evento", 180), "dispositivo": ("Dispositivo", 80)
        }
        for col, (text, width) in headers_detail.items():
            self.tree_detail.heading(col, text=text)
            self.tree_detail.column(col, width=width, anchor="center" if col in ("apto", "dispositivo") else "w", stretch=True)
        self.tree_detail.pack(fill="both", expand=True, pady=4)

    def _jump_to_edit_tab(self) -> None:
        self.notebook.select(self.tab_edit)

    def _jump_to_detail_tab(self) -> None:
        self.notebook.select(self.tab_detail)

    def _export_tree_to_csv(self, tree: ttk.Treeview, default_name: str) -> None:
        items = tree.get_children()
        if not items:
            messagebox.showwarning("Exportar a Excel (.csv)", "No hay datos en la tabla para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivo Excel CSV", "*.csv"), ("Todos los archivos", "*.*")],
            initialfile=f"{default_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                cols = tree["columns"]
                headers = [tree.heading(c)["text"] for c in cols]
                writer.writerow(headers)

                for item in items:
                    vals = tree.item(item, "values")
                    writer.writerow([str(v) for v in vals])

            messagebox.showinfo("Exportación Exitosa", f"Archivo Excel (.csv) generado correctamente en:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo CSV: {e}")

    def _export_tree_to_txt(self, tree: ttk.Treeview, default_name: str) -> None:
        items = tree.get_children()
        if not items:
            messagebox.showwarning("Exportar", "No hay datos en la tabla para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")],
            initialfile=f"{default_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                cols = tree["columns"]
                headers = [tree.heading(c)["text"] for c in cols]
                f.write(" | ".join(headers) + "\n")
                f.write("-" * 100 + "\n")

                for item in items:
                    vals = tree.item(item, "values")
                    f.write(" | ".join(str(v) for v in vals) + "\n")

            messagebox.showinfo("Exportación Exitosa", f"Datos exportados correctamente a:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

    def _on_chart_resize(self, event=None) -> None:
        if self.last_day_counts:
            self._render_bar_chart(self.last_day_counts)
        else:
            self._draw_empty_chart()

    def _draw_empty_chart(self) -> None:
        self.chart_canvas.delete("all")
        w = max(300, self.chart_canvas.winfo_width())
        h = max(180, self.chart_canvas.winfo_height())
        self.chart_canvas.create_text(
            w / 2, h / 2,
            text="Sin datos para graficar.\nEjecuta el analisis IA para visualizar el historico.",
            fill="#a0aec0", font=("Segoe UI", 9), justify="center"
        )

    def _render_bar_chart(self, day_counts: Dict[str, int]) -> None:
        self.last_day_counts = dict(day_counts)
        self.chart_canvas.delete("all")
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_label = {"Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mie", "Thursday": "Jue", "Friday": "Vie", "Saturday": "Sab", "Sunday": "Dom"}

        canvas_width = max(380, self.chart_canvas.winfo_width())
        canvas_height = max(200, self.chart_canvas.winfo_height())
        margin_left = 40
        margin_bottom = 35
        margin_top = 25
        usable_w = canvas_width - margin_left - 20
        usable_h = canvas_height - margin_bottom - margin_top
        max_val = max(list(day_counts.values()) + [5])

        step = usable_w / 7
        bar_width = max(24, int(step * 0.65))
        gap = step - bar_width
        start_x = margin_left + gap / 2

        for i in range(4):
            y = margin_top + i * (usable_h / 3)
            val_label = int(max_val - (i * (max_val / 3)))
            self.chart_canvas.create_text(22, y, text=str(val_label), fill="#718096", font=("Segoe UI", 8))
            self.chart_canvas.create_line(margin_left, y, canvas_width - 15, y, fill="#edf2f7", dash=(2, 2))

        for idx, day in enumerate(days_order):
            count = day_counts.get(day, 0)
            x0 = start_x + idx * step
            y0 = canvas_height - margin_bottom - int((count / max_val) * usable_h)
            x1 = x0 + bar_width
            y1 = canvas_height - margin_bottom

            bar_color = "#3182ce" if count < 10 else "#d69e2e" if count < 25 else "#e53e3e"
            self.chart_canvas.create_rectangle(x0, y0, x1, y1, fill=bar_color, outline="")
            self.chart_canvas.create_text((x0 + x1) / 2, y0 - 10, text=str(count), fill="#2d3748", font=("Segoe UI", 8, "bold"))
            self.chart_canvas.create_text((x0 + x1) / 2, y1 + 14, text=days_label[day], fill="#4a5568", font=("Segoe UI", 8, "bold"))

    # Búsqueda de Usuarios por Apartamento en la pestaña Editar Usuario
    def _cmd_search_users_by_apto(self) -> None:
        target_apto = self.edit_search_apto_var.get().strip()
        if not target_apto:
            messagebox.showwarning("Apartamento requerido", "Ingrese el número de apartamento a buscar.")
            return

        self.lbl_edit_status.config(text=f"Buscando residentes del Apartamento {target_apto} en el MIP...", bg="#e2e8f0")
        self.btn_search_apto_users.config(state="disabled")

        def task():
            with self.busy_lock:
                vs = self.client.get_sync_counts(silent=True)
                max_u = max(int(vs.get("usuarios", 0)), int(vs.get("moradores", 0)), 50)
                max_u = min(max_u, 500)

                found: Dict[str, Dict[str, Any]] = {}
                for uid in range(1, max_u + 1):
                    res = self.client.search_user(uid, False)
                    if isinstance(res, dict) and "error" not in res:
                        apto_val = str(res.get("apto", "")).strip()
                        nombre_val = str(res.get("nombre", res.get("nome", ""))).strip()
                        if apto_val == target_apto and nombre_val:
                            bloco_val = str(res.get("bloco", "")).strip()
                            label = f"ID {uid} - {nombre_val} (Apto {apto_val} Blq {bloco_val})"
                            res["id"] = uid
                            found[label] = res

                last_ev = int(vs.get("eventos", 0))
                if last_ev > 0:
                    for eid in range(max(1, last_ev - 80), last_ev + 1):
                        ev = self.client.fetch_event_by_id(eid)
                        if isinstance(ev, dict) and str(ev.get("apto", "")).strip() == target_apto:
                            uid_ev = int(ev.get("id_usuario", 0) or 0)
                            if uid_ev > 0:
                                res = self.client.search_user(uid_ev, False)
                                if isinstance(res, dict) and "error" not in res:
                                    nombre_val = str(res.get("nombre", res.get("nome", ""))).strip()
                                    bloco_val = str(res.get("bloco", "")).strip()
                                    label = f"ID {uid_ev} - {nombre_val} (Apto {target_apto} Blq {bloco_val})"
                                    res["id"] = uid_ev
                                    found[label] = res

                self.ui_queue.put(("apto_users_found", (target_apto, found)))

        self._run_bg(task)

    def _on_select_apto_user_to_edit(self, event=None) -> None:
        sel = self.edit_apto_users_var.get()
        if sel in self.found_apto_users:
            user_dict = self.found_apto_users[sel]
            uid = int(user_dict.get("id", 1))
            self.edit_uid_var.set(uid)
            self.ui_queue.put(("populate_edit_form", user_dict))

    # Lógica de Consulta y Edición de Usuario
    def _cmd_fetch_user_to_edit(self) -> None:
        uid = self.edit_uid_var.get()
        is_vis = self.edit_is_visitor_var.get()
        self.lbl_edit_status.config(text=f"Consultando usuario ID {uid} en el MIP...", bg="#e2e8f0")

        def task():
            with self.busy_lock:
                res = self.client.search_user(uid, is_vis)
                self.ui_queue.put(("populate_edit_form", res))

        self._run_bg(task)

    def _cmd_save_edited_user(self) -> None:
        uid = self.edit_uid_var.get()
        if uid <= 0:
            messagebox.showwarning("ID Requerido", "Selecciona un ID válido para editar.")
            return

        cat_code = int(self.e_cat_var.get().split("-")[0].strip())
        allowed_devs = [d for d, var in self.edisp_vars.items() if var.get()]

        user_data = {
            "id": uid,
            "categoria": cat_code,
            "nivel": int(self.e_nivel_var.get()),
            "nome": self.e_nome_var.get().strip(),
            "apto": self.e_apto_var.get().strip(),
            "bloco": self.e_bloco_var.get().strip(),
            "cpf": self.e_cpf_var.get().strip(),
            "rg": self.e_rg_var.get().strip(),
            "email": self.e_email_var.get().strip(),
            "tel_res": self.e_tel_res_var.get().strip(),
            "tel_cel": self.e_tel_cel_var.get().strip(),
            "senha_3dig": self.e_senha3_var.get().strip(),
            "senha_sec": self.e_senhasec_var.get().strip(),
            "dispositivos": allowed_devs,
            "dias_semana": 255,
        }

        self.lbl_edit_status.config(text="Enviando cambios al MIP (ALTERAR_RECURSO)...", bg="#e2e8f0")

        def task():
            with self.busy_lock:
                ok, _, msg = self.client.create_or_update_user(user_data, is_update=True)
                if not ok:
                    self.ui_queue.put(("edit_result", (False, f"Fallo al enviar: {msg}. Debe repetirse la opción.")))
                    return

                verify_res = self.client.search_user(uid, cat_code in (1, 2))
                if "error" in verify_res:
                    self.ui_queue.put(("edit_result", (False, "El equipo no pudo verificar el cambio. Fallo la comprobación.")))
                else:
                    self.ui_queue.put(("edit_result", (True, f"¡Cambios guardados y verificados con éxito en el MIP! ({msg})")))

        self._run_bg(task)

    def _cmd_get_events_today(self) -> None:
        self._fetch_filtered_events(days_limit=0)

    def _cmd_get_events_week(self) -> None:
        self._fetch_filtered_events(days_limit=7)

    def _fetch_filtered_events(self, days_limit: int) -> None:
        target_apto = self.ev_apto_var.get().strip()
        self.client.log(f"Filtrando eventos por Apto '{target_apto}' (Límite días: {days_limit})...")
        self.btn_ev_today.config(state="disabled")
        self.btn_ev_week.config(state="disabled")
        self.ev_progress["value"] = 5
        self.lbl_ev_status.config(text="Conectando al MIP y calculando eventos a descargar...")

        def task():
            with self.busy_lock:
                vs = self.client.get_sync_counts(silent=True)
                last_id = int(vs.get("eventos", 0))
                if last_id == 0:
                    self.ui_queue.put(("ev_progress", (100, "No hay eventos registrados en el MIP.")))
                    self.ui_queue.put(("events_loaded", []))
                    return

                start_id = max(1, last_id - 150)
                total_to_fetch = last_id - start_id + 1
                cutoff_date = datetime.now() - timedelta(days=days_limit)
                matched_events = []
                fetched = 0
                t_start = time.time()

                for eid in range(start_id, last_id + 1):
                    ev = self.client.fetch_event_by_id(eid)
                    fetched += 1
                    if fetched % 5 == 0 or fetched == total_to_fetch:
                        elapsed = max(0.01, time.time() - t_start)
                        rate = elapsed / fetched
                        rem = round((total_to_fetch - fetched) * rate, 1)
                        prog_val = int((fetched / total_to_fetch) * 100)
                        self.ui_queue.put((
                            "ev_progress",
                            (prog_val, f"Descargando {fetched}/{total_to_fetch} (Tiempo restante aprox: {rem}s)...")
                        ))

                    if ev and "id_evento" in ev:
                        apto_ev = str(ev.get("apto", "")).strip()
                        if apto_ev == target_apto or not target_apto:
                            if days_limit == 0:
                                date_str = str(ev.get("fecha", "")).split(" ")[0]
                                today_str = datetime.now().strftime("%d/%m/%Y")
                                if date_str == today_str:
                                    matched_events.append(ev)
                            else:
                                date_str = str(ev.get("fecha", ""))
                                try:
                                    ev_date = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
                                    if ev_date >= cutoff_date:
                                        matched_events.append(ev)
                                except Exception:
                                    matched_events.append(ev)

                self.ui_queue.put(("ev_progress", (100, f"Descarga finalizada. {len(matched_events)} eventos encontrados.")))
                self.ui_queue.put(("events_loaded", matched_events))

        self._run_bg(task)

    def _cmd_run_ai_analysis(self) -> None:
        target_apto = self.ai_apto_var.get().strip()
        period_str = self.ai_period_var.get()
        max_scan = self.ai_range_var.get()

        days_map = {"Ultimos 3 Dias": 3, "Ultimos 7 Dias": 7, "Ultimos 15 Dias": 15, "Ultimos 30 Dias": 30}
        target_days = days_map.get(period_str, 7)

        self.client.log(f"IA Iniciada: Escaneando apto '{target_apto}' para los {period_str}...")
        self.btn_run_ai.config(state="disabled")
        self.ai_progress["value"] = 10
        self.lbl_ai_status.config(text="Calculando tiempo aproximado y conectando al MIP...")

        def task():
            with self.busy_lock:
                vs = self.client.get_sync_counts(silent=True)
                last_id = int(vs.get("eventos", 0))
                if last_id == 0:
                    self.ui_queue.put(("ai_done", ([], {}, [])))
                    return

                start_id = max(1, last_id - max_scan)
                total_to_fetch = last_id - start_id + 1
                est_time = round(total_to_fetch * 0.015, 1)
                self.ui_queue.put(("ai_progress", (30, f"Descargando {total_to_fetch} eventos (T. aprox: {est_time}s)...")))

                cutoff_date = datetime.now() - timedelta(days=target_days)
                events_collected = []
                fetched = 0

                for eid in range(start_id, last_id + 1):
                    ev = self.client.fetch_event_by_id(eid)
                    fetched += 1
                    if fetched % 10 == 0:
                        prog_val = 30 + int((fetched / total_to_fetch) * 50)
                        self.ui_queue.put(("ai_progress", (prog_val, f"Procesando evento {fetched}/{total_to_fetch}...")))

                    if ev and "id_evento" in ev:
                        if str(ev.get("apto", "")).strip() == target_apto:
                            date_str = str(ev.get("fecha", ""))
                            try:
                                ev_date = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
                                if ev_date >= cutoff_date:
                                    events_collected.append(ev)
                            except Exception:
                                events_collected.append(ev)

                self.ui_queue.put(("ai_progress", (90, "Generando historicos y detalle de accesos...")))

                user_stats: Dict[str, List[Dict[str, Any]]] = {}
                global_days_count: Dict[str, int] = {"Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 0, "Saturday": 0, "Sunday": 0}
                detailed_rows = []

                for ev in events_collected:
                    uname = ev.get("nombre", "DESCONOCIDO")
                    if uname not in user_stats:
                        user_stats[uname] = []
                    user_stats[uname].append(ev)

                    recurso_txt = str(ev.get("tipo_recurso", "Desconocido"))
                    if "RFID" in recurso_txt or "Chaveiro" in recurso_txt:
                        medio_especifico = "Tarjeta RFID (TAG XID)"
                    elif "Controle" in recurso_txt or "RF" in recurso_txt:
                        medio_especifico = "Control Remoto (XTR)"
                    elif "Senha" in recurso_txt:
                        medio_especifico = "Contraseña de Teclado"
                    else:
                        medio_especifico = f"Medio: {recurso_txt}"

                    detailed_rows.append({
                        "fecha": ev.get("fecha", ""),
                        "apto": ev.get("apto", ""),
                        "usuario": uname,
                        "medio_acceso": medio_especifico,
                        "evento": ev.get("tipo_evento", ""),
                        "dispositivo": ev.get("id_dispositivo", 1)
                    })

                    try:
                        dt = datetime.strptime(str(ev.get("fecha", "")), "%d/%m/%Y %H:%M:%S")
                        dname = dt.strftime("%A")
                        if dname in global_days_count:
                            global_days_count[dname] += 1
                    except Exception:
                        pass

                analysis_results = []
                for uname, uevs in user_stats.items():
                    total = len(uevs)
                    anomalies = 0
                    historical_days: Dict[str, int] = {}
                    obs_details = []

                    for ev in uevs:
                        fecha_str = str(ev.get("fecha", ""))
                        try:
                            dt = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M:%S")
                            day_name = dt.strftime("%A")
                            hour = dt.hour
                        except Exception:
                            day_name = "Desconocido"
                            hour = 12

                        historical_days[day_name] = historical_days.get(day_name, 0) + 1

                        if 1 <= hour <= 4:
                            anomalies += 1
                            obs_details.append(f"Anomalia nocturna el {fecha_str} (01:00-04:00 AM).")

                    history_summary = ", ".join([f"{d}: {c}" for d, c in historical_days.items()])

                    if anomalies > 0:
                        semaforo = "ROJO"
                        obs = f"ALERTA CRITICA: {anomalies} salidas de madrugada. Dias [{history_summary}]. Requiere intervencion inmediata."
                    elif total > 20:
                        semaforo = "AMARILLO"
                        obs = f"PRECAUCION: Alto volumen ({total} eventos). Dias [{history_summary}]. Atipico pero valido."
                    else:
                        semaforo = "VERDE"
                        obs = f"ESTABLE: Parametros normales. Dias [{history_summary}]. Todo bien."

                    if obs_details:
                        obs = f"{' | '.join(obs_details)} | Dias: [{history_summary}]"

                    analysis_results.append({
                        "usuario": uname,
                        "apto": target_apto,
                        "total": total,
                        "semaforo": semaforo,
                        "observaciones": obs
                    })

                self.ui_queue.put(("ai_progress", (100, "Analisis completado con exito.")))
                self.ui_queue.put(("ai_done", (analysis_results, global_days_count, detailed_rows)))

        self._run_bg(task)

    # Cambio de Idioma
    def _on_change_language(self, event=None) -> None:
        self.lang = self.lang_var.get()
        t = I18N[self.lang]
        self.title(t["app_title"])
        self.conn_frame.config(text=t["conn_frame"])
        self.notebook.tab(0, text=t["tab_dashboard"])
        self.notebook.tab(1, text=t["tab_create"])
        self.notebook.tab(2, text=t["tab_edit"])
        self.notebook.tab(3, text=t["tab_tpl"])
        self.notebook.tab(4, text=t["tab_search"])
        self.notebook.tab(5, text=t["tab_events"])
        self.notebook.tab(6, text=t["tab_online"])
        self.notebook.tab(7, text=t["tab_ai"])
        self.notebook.tab(8, text=t["tab_detail"])
        self.notebook.tab(9, text=t["tab_sip_network"])
        self.asr_box.config(text=t["asr_box"])
        self.btn_open_door.config(text=t["btn_open_door"])
        self.cfg_box.config(text=t["cfg_box"])
        self.vs_box.config(text=t["vs_box"])
        self.u_personal_box.config(text=t["u_personal"])
        self.u_access_box.config(text=t["u_access"])
        self.u_media_box.config(text=t["u_media"])
        self.btn_send_all.config(text=t["btn_send_all"])
        self.btn_goto_edit.config(text=t["btn_goto_edit"])
        self.tpl_box.config(text=t["tpl_box"])
        self.log_frame.config(text=t["log_frame"])

    # Lógica de Formulario y Utilitarios
    def _collect_form_data(self) -> Dict[str, Any]:
        cat_code = int(self.f_cat_var.get().split("-")[0].strip())
        allowed_devs: List[int] = [d for d, var in self.disp_vars.items() if var.get()]
        return {
            "id": int(self.f_uid_var.get().strip() or "0"),
            "categoria": cat_code,
            "nivel": int(self.f_nivel_var.get()),
            "nome": self.f_nome_var.get().strip(),
            "apto": self.f_apto_var.get().strip(),
            "bloco": self.f_bloco_var.get().strip(),
            "cpf": self.f_cpf_var.get().strip(),
            "rg": self.f_rg_var.get().strip(),
            "email": self.f_email_var.get().strip(),
            "tel_res": self.f_tel_res_var.get().strip(),
            "tel_cel": self.f_tel_cel_var.get().strip(),
            "senha_3dig": self.f_senha3_var.get().strip(),
            "senha_sec": self.f_senhasec_var.get().strip(),
            "dispositivos": allowed_devs,
            "dias_semana": 255,
            "modelo": self.f_modelo_var.get().strip(),
            "marca": self.f_marca_var.get().strip(),
            "placa": self.f_placa_var.get().strip(),
            "cor": self.f_cor_var.get().strip(),
        }

    def _populate_form_from_dict(self, d: Dict[str, Any]) -> None:
        self.f_uid_var.set(str(d.get("id", 0)))
        cat = int(d.get("categoria", 0))
        cat_labels = {0: "0 - Morador (Residente)", 1: "1 - Prestador de Servicio", 2: "2 - Visitante"}
        self.f_cat_var.set(cat_labels.get(cat, "0 - Morador (Residente)"))
        self.f_nivel_var.set(int(d.get("nivel", 1)))
        self.f_nome_var.set(d.get("nome", ""))
        self.f_apto_var.set(d.get("apto", ""))
        self.f_bloco_var.set(d.get("bloco", ""))
        self.f_cpf_var.set(d.get("cpf", ""))
        self.f_rg_var.set(d.get("rg", ""))
        self.f_email_var.set(d.get("email", ""))
        self.f_tel_res_var.set(d.get("tel_res", ""))
        self.f_tel_cel_var.set(d.get("tel_cel", ""))
        self.f_senha3_var.set(d.get("senha_3dig", ""))
        self.f_senhasec_var.set(d.get("senha_sec", ""))
        devs = d.get("dispositivos", [1, 2])
        for dev_id, var in self.disp_vars.items():
            var.set(dev_id in devs)
        self.f_modelo_var.set(d.get("modelo", ""))
        self.f_marca_var.set(d.get("marca", ""))
        self.f_placa_var.set(d.get("placa", ""))
        self.f_cor_var.set(d.get("cor", ""))

    def _clear_user_form(self) -> None:
        self._populate_form_from_dict({"id": 0, "categoria": 0, "nivel": 1, "dispositivos": [1, 2]})
        self.f_tag_code_var.set("")
        self.f_rf_code_var.set("")
        self.lbl_create_status.config(text="Formulario limpio.")

    def _on_template_preview(self, event=None) -> None:
        name = self.tpl_select_var.get()
        tpl = self.templates.get(name, {})
        self.txt_tpl_preview.delete("1.0", "end")
        self.txt_tpl_preview.insert("end", json.dumps(tpl, indent=2, ensure_ascii=False))

    def _apply_selected_template_to_form(self) -> None:
        name = self.tpl_select_var.get()
        tpl = self.templates.get(name, {})
        self._populate_form_from_dict(tpl)
        self.notebook.select(self.tab_create)
        self.lbl_create_status.config(text=f"Plantilla '{name}' cargada.")

    def _apply_and_send_template_now(self) -> None:
        name = self.tpl_select_var.get()
        tpl = self.templates.get(name, {})
        self._populate_form_from_dict(tpl)
        self.notebook.select(self.tab_create)
        self._cmd_send_full_user()

    def _save_current_form_as_template(self) -> None:
        name = self.new_tpl_name_var.get().strip()
        if not name:
            messagebox.showwarning("Plantilla", "Escribe un nombre.")
            return
        self.templates[name] = self._collect_form_data()
        self._save_templates_to_disk()
        self.cb_templates.config(values=list(self.templates.keys()))
        self.tpl_select_var.set(name)
        self._on_template_preview()
        messagebox.showinfo("Guardado", f"Plantilla '{name}' guardada.")

    def _run_bg(self, func) -> None:
        threading.Thread(target=func, daemon=True).start()

    # Hilo de Monitoreo Online en Tiempo Real Verdadero
    def _online_poll_worker(self) -> None:
        while self.online_polling_active:
            time.sleep(2.0)
            if not self.online_polling_active:
                break
            if self.busy_lock.acquire(blocking=False):
                try:
                    vs = self.client.get_sync_counts(silent=True)
                    if isinstance(vs, dict):
                        curr_id = int(vs.get("eventos", 0))
                        if self.last_polled_event_id == -1 and curr_id > 0:
                            self.last_polled_event_id = curr_id
                        elif curr_id > self.last_polled_event_id and self.last_polled_event_id != -1:
                            start_new = max(self.last_polled_event_id + 1, curr_id - 10)
                            for eid in range(start_new, curr_id + 1):
                                ev = self.client.fetch_event_by_id(eid)
                                if ev and isinstance(ev, dict):
                                    self.ui_queue.put(("online_event", ev))
                            self.last_polled_event_id = curr_id
                except Exception:
                    pass
                finally:
                    self.busy_lock.release()

    def _on_connect(self) -> None:
        ip = self.ip_var.get().strip()
        port = int(self.port_var.get().strip() or 9080)
        login = self.login_var.get().strip()
        pwd = self.pass_var.get().strip()
        pmode = self.pmode_var.get()
        self.test_ip_var.set(ip)
        #self.alg_host_var.set(ip)
        #self.sip_host_var.set(ip)
        self.btn_connect.config(state="disabled")

        def task():
            with self.busy_lock:
                ok = self.client.connect(ip, port, login, pwd, pmode)
                self.ui_queue.put(("conn_state", ok))
                if ok:
                    vs = self.client.get_sync_counts()
                    if isinstance(vs, dict):
                        self.last_polled_event_id = int(vs.get("eventos", 0))
                    self.ui_queue.put(("vs_data", vs))
                    if not self.online_polling_active:
                        self.online_polling_active = True
                        threading.Thread(target=self._online_poll_worker, daemon=True).start()

        self._run_bg(task)

    def _on_disconnect(self) -> None:
        self.online_polling_active = False
        self.last_polled_event_id = -1
        self.client.disconnect()
        self.ui_queue.put(("conn_state", False))

        self.btn_xre1.config(
            state="disabled",
            bg="#cbd5e0",
            fg="#a0aec0",
            activebackground="#cbd5e0",
            text="🔓 XRE 1000 Plus [Desconectado]"
        )
        self.btn_xre2.config(
            state="disabled",
            bg="#cbd5e0",
            fg="#a0aec0",
            activebackground="#cbd5e0",
            text="🔓 XRE 1000 Plus [Desconectado]"
        )

    def _cmd_open_door(self) -> None:
        self._run_bg(lambda: self.client.trigger_remote_output(self.dev_addr_var.get(), self.out_num_var.get()))

    def _cmd_sync_time(self) -> None:
        self._run_bg(lambda: self.client.sync_datetime(0))

    def _cmd_get_uid(self) -> None:
        def task():
            with self.busy_lock:
                info = self.client.get_mip_uid()
                if info:
                    self.client.log(f"INFO MIP -> UID: {info.get('uid')} | MAC: {info.get('mac')} | FW: {info.get('firmware')}")
        self._run_bg(task)

    def _cmd_set_idle_msg(self) -> None:
        self._run_bg(lambda: self.client.set_idle_message(self.idle_msg_var.get()))

    def _cmd_get_vs(self) -> None:
        def task():
            with self.busy_lock:
                vs = self.client.get_sync_counts()
                self.ui_queue.put(("vs_data", vs))
        self._run_bg(task)

    def _cmd_send_full_user(self) -> None:
        user_data = self._collect_form_data()
        if not user_data["nome"]:
            messagebox.showwarning("Dato requerido", "Ingresa el Nombre del Usuario.")
            return
        tag_code = self.f_tag_code_var.get().strip()
        rf_code = self.f_rf_code_var.get().strip()
        rf_ts = self.f_rf_ts_var.get()
        veh = {"modelo": user_data["modelo"], "marca": user_data["marca"], "placa": user_data["placa"], "cor": user_data["cor"]}
        self.lbl_create_status.config(text="[ENVIANDO] Enviando Usuario al MIP 1000 IP...")

        def task():
            with self.busy_lock:
                ok, msg = self.client.send_full_user_bundle(user_data, tag_code, rf_code, rf_ts, veh, False)
                self.ui_queue.put(("create_status", (ok, msg)))
                if ok:
                    vs = self.client.get_sync_counts(silent=True)
                    self.ui_queue.put(("vs_data", vs))

        self._run_bg(task)

    # Captura robusta de TAG RFID y Control RF en el formulario Crear Usuario
    def _cmd_capture_tag_to_form(self) -> None:
        self.lbl_create_status.config(text="[LECTURA] Aproxima el TAG RFID al lector del MIP 1000 IP (0x1C)...", bg="#fefcbf")
        self.btn_read_tag_form.config(state="disabled")

        def task():
            with self.busy_lock:
                try:
                    res = self.client.read_tag_on_mip()
                    tag_val = ""
                    if isinstance(res, (tuple, list)):
                        tag_val = str(res[1] if len(res) > 1 and res[1] else res[0]).strip()
                    elif isinstance(res, dict):
                        tag_val = str(res.get("codigo_hex") or res.get("tag") or res.get("codigo") or "").strip()
                    elif isinstance(res, str):
                        tag_val = res.strip()

                    if tag_val:
                        self.ui_queue.put(("fill_tag", tag_val))
                    else:
                        self.ui_queue.put(("create_status", (False, "No se detectó TAG en el tiempo de espera del MIP.")))
                except Exception as e:
                    self.ui_queue.put(("create_status", (False, f"Error al capturar TAG: {e}")))
                finally:
                    self.ui_queue.put(("enable_capture_btns", None))

        self._run_bg(task)

    def _cmd_capture_rf_to_form(self) -> None:
        self.lbl_create_status.config(text="[LECTURA] Presiona el botón del Control RF cerca del receptor (0x26)...", bg="#fefcbf")
        self.btn_read_rf_form.config(state="disabled")

        def task():
            with self.busy_lock:
                try:
                    res = self.client.read_rf_control()
                    rf_code = ""
                    rf_ts = 0
                    if isinstance(res, dict):
                        rf_code = str(res.get("codigo_hex") or res.get("codigo") or res.get("rf") or "").strip()
                        rf_ts = int(res.get("timestamp", 0) or 0)
                    elif isinstance(res, (tuple, list)) and len(res) > 0:
                        rf_code = str(res[0]).strip()
                        if len(res) > 1 and str(res[1]).isdigit():
                            rf_ts = int(res[1])
                    elif isinstance(res, str):
                        rf_code = res.strip()

                    if rf_code:
                        self.ui_queue.put(("fill_rf", {"codigo_hex": rf_code, "timestamp": rf_ts}))
                    else:
                        self.ui_queue.put(("create_status", (False, "No se detectó Control RF en el tiempo de espera.")))
                except Exception as e:
                    self.ui_queue.put(("create_status", (False, f"Error al capturar Control RF: {e}")))
                finally:
                    self.ui_queue.put(("enable_capture_btns", None))

        self._run_bg(task)

    def _cmd_search_user(self) -> None:
        uid, vis = self.search_uid_var.get(), self.is_visitor_var.get()
        def task():
            with self.busy_lock:
                res = self.client.search_user(uid, vis)
                self.ui_queue.put(("user_data", res))
        self._run_bg(task)

    def _cmd_read_tag(self) -> None:
        def task():
            with self.busy_lock:
                res = self.client.read_tag_on_mip()
                if isinstance(res, (tuple, list)) and len(res) > 1:
                    txt = f"TAG RFID: {res[1]} ({res[0]})"
                elif res:
                    txt = f"TAG RFID: {res}"
                else:
                    txt = "Sin lectura"
                self.ui_queue.put(("captured_code", txt))
        self._run_bg(task)

    def _cmd_read_rf(self) -> None:
        def task():
            with self.busy_lock:
                res = self.client.read_rf_control()
                if isinstance(res, dict):
                    txt = f"Control RF: {res.get('codigo_hex', '')} | TS: {res.get('timestamp', 0)}"
                elif res:
                    txt = f"Control RF: {res}"
                else:
                    txt = "Sin lectura RF"
                self.ui_queue.put(("captured_code", txt))
        self._run_bg(task)

    def _process_ui_queue(self) -> None:
        t = I18N[self.lang]
        while not self.ui_queue.empty():
            kind, data = self.ui_queue.get_nowait()
            if kind == "log":
                msg_str = str(data)
                self.txt_log.insert("end", msg_str + "\n")
                self.txt_log.see("end")
                if "AUTENTICACAO_INVALIDA" in msg_str:
                    self.lbl_status.config(text="[SENHA INVALIDA / BLOQUEO 10m]", fg="#c53030")
            elif kind == "rtsp_error":
                cam_id, err_msg = data
                if cam_id == 1:
                    self.rtsp1_running = False
                    self.lbl_cam1.config(image="", text=err_msg, fg="#fc8181")
                else:
                    self.rtsp2_running = False
                    self.lbl_cam2.config(image="", text=err_msg, fg="#fc8181")
            elif kind == "conn_state":
                if data:
                    self.lbl_status.config(text=t["st_conn"], fg="#1b8a4b")
                    self.lbl_online_indicator.config(text="[Escucha en Tiempo Real: ACTIVA]", fg="#1b8a4b")
                    self.btn_connect.config(state="disabled")
                    self.btn_disconnect.config(state="normal")
                else:
                    self.lbl_status.config(text=t["st_disc"], fg="#c53030")
                    self.lbl_online_indicator.config(text="[Escucha en Tiempo Real: INACTIVA]", fg="#c53030")
                    self.btn_connect.config(state="normal")
                    self.btn_disconnect.config(state="disabled")
            elif kind == "vs_data":
                if isinstance(data, dict):
                    for item in self.tree_vs.get_children():
                        self.tree_vs.delete(item)
                    for k, v in data.items():
                        self.tree_vs.insert("", "end", values=(k, v))

                    dev_count = int(data.get("dispositivos", 1))
                    if dev_count >= 1:
                        self.btn_xre1.config(state="normal", bg="#1b8a4b", fg="#ffffff", activebackground="#126335")
                        self.btn_xre1.config(text="🔓 Abrir XRE 1000 Plus #1 (RS-485 2)")
                    if dev_count >= 2:
                        self.btn_xre2.config(state="normal", bg="#1b8a4b", fg="#ffffff", activebackground="#126335")
                        self.btn_xre2.config(text="🔓 Abrir XRE 1000 Plus #2 (RS-485 3)")
            elif kind == "port_test_result":
                success, msg = data
                self.lbl_port_status.config(text=msg, fg="#22543d" if success else "#742a2a")
            elif kind == "sip_probe_result":
                ok, msg = data
                self.lbl_sip_probe_result.config(text=msg, fg="#276749" if ok else "#9b2c2c")
            elif kind == "sip_register_status":
                code, msg = data
                ok = 200 <= int(code or 0) < 300
                self.lbl_softphone_status.config(
                    text=f"Registro SIP: {code} — {msg}",
                    fg="#276749" if ok else ("#9b2c2c" if int(code or 0) >= 300 else "#975a16")
                )
                self.btn_sip_register.config(state="normal")
            elif kind == "sip_call_status":
                self.lbl_call_status.config(text=f"Llamada: {data}")
            elif kind == "sip_call_disconnected":
                self.sip_call = None
                self.btn_sip_call.config(state="normal")
                self.btn_sip_hangup.config(state="disabled")
                self.lbl_call_status.config(text=f"Llamada finalizada: {data}")
            elif kind == "sip_tool_status":
                self.lbl_softphone_status.config(text=str(data))
            elif kind == "capture_status":
                self.lbl_capture_status.config(text=str(data))
            elif kind == "sip_probe_done":
                self.btn_sip_probe.config(state="normal")
            elif kind == "capture_finished":
                self.btn_capture_start.config(state="normal")
                self.btn_capture_stop.config(state="disabled")
                if self.capture_stop_event.is_set():
                    self.lbl_capture_status.config(text="Captura detenida.")
            elif kind == "capture_row":
                values, is_error = data
                self.capture_packet_count += 1
                tag = "sip_error" if is_error else "normal"
                self.tree_capture.insert("", 0, values=values, tags=(tag,))
                children = self.tree_capture.get_children()
                if len(children) > 500:
                    for item in children[500:]:
                        self.tree_capture.delete(item)
                self.lbl_capture_count.config(text=f"Paquetes mostrados: {self.capture_packet_count}")
            elif kind == "enable_capture_btns":
                self.btn_read_tag_form.config(state="normal")
                self.btn_read_rf_form.config(state="normal")
            elif kind == "create_status":
                ok, msg = data
                self.lbl_create_status.config(text=("[OK] " if ok else "[ERROR] ") + str(msg), bg="#c6f6d5" if ok else "#fed7d7")
            elif kind == "fill_tag":
                self.f_tag_code_var.set(str(data))
                self.lbl_create_status.config(text=f"[OK] TAG capturado en MIP: {data}", bg="#c6f6d5")
            elif kind == "fill_rf":
                self.f_rf_code_var.set(str(data.get("codigo_hex", "")))
                self.f_rf_ts_var.set(int(data.get("timestamp", 0)))
                self.lbl_create_status.config(text=f"[OK] Control RF capturado: {data.get('codigo_hex', '')}", bg="#c6f6d5")
            elif kind == "user_data":
                self.lbl_user_result.config(text=f"Resultado: {data}")
            elif kind == "captured_code":
                self.captured_code_var.set(str(data))
            elif kind == "apto_users_found":
                apto_num, found_dict = data
                self.btn_search_apto_users.config(state="normal")
                self.found_apto_users = found_dict
                if not found_dict:
                    self.cb_apto_users.config(values=[])
                    self.edit_apto_users_var.set(f"(Sin residentes en Apto {apto_num})")
                    self.lbl_edit_status.config(text=f"No se encontraron residentes registrados en el Apto {apto_num}.", bg="#fed7d7")
                else:
                    keys = list(found_dict.keys())
                    self.cb_apto_users.config(values=keys)
                    self.edit_apto_users_var.set(keys[0])
                    self._on_select_apto_user_to_edit()
                    self.lbl_edit_status.config(
                        text=f"[OK] {len(keys)} residente(s) encontrado(s) en el Apto {apto_num}. Seleccione de la lista para editar.",
                        bg="#c6f6d5"
                    )
            elif kind == "populate_edit_form":
                if not isinstance(data, dict) or "error" in data:
                    err_txt = data.get("error", "Desconocido") if isinstance(data, dict) else str(data)
                    self.lbl_edit_status.config(text=f"[ERROR] No se encontró el usuario: {err_txt}", bg="#fed7d7")
                else:
                    self.e_nome_var.set(str(data.get("nombre", data.get("nome", ""))))
                    self.e_apto_var.set(str(data.get("apto", "")))
                    self.e_bloco_var.set(str(data.get("bloco", "")))
                    self.e_cpf_var.set(str(data.get("cpf", "")))
                    self.e_rg_var.set(str(data.get("rg", "")))
                    self.e_email_var.set(str(data.get("email", "")))
                    self.e_tel_res_var.set(str(data.get("tel_res", "")))
                    self.e_tel_cel_var.set(str(data.get("tel_cel", "")))
                    self.e_nivel_var.set(int(data.get("nivel_acceso", data.get("nivel", 1)) or 1))
                    devs = data.get("dispositivos", [1, 2])
                    if isinstance(devs, list):
                        for d_id, var in self.edisp_vars.items():
                            var.set(d_id in devs)
                    self.lbl_edit_status.config(
                        text=f"[OK] Datos cargados para usuario ID {self.edit_uid_var.get()}. Modifique y guarde.",
                        bg="#c6f6d5"
                    )
            elif kind == "edit_result":
                ok, msg = data
                self.lbl_edit_status.config(text=msg, bg="#c6f6d5" if ok else "#fed7d7")
                if ok:
                    messagebox.showinfo("Éxito", msg)
                else:
                    messagebox.showerror("Error", msg)
            elif kind == "online_event":
                ev = data if isinstance(data, dict) else {"tipo_evento": str(data)}
                fecha_ev = str(ev.get("fecha") or datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                apto_ev = str(ev.get("apto") or ev.get("apartamento") or "-")
                nombre_ev = str(ev.get("nombre") or ev.get("nome") or ev.get("usuario") or "DESCONOCIDO")
                recurso_txt = str(ev.get("tipo_recurso") or ev.get("recurso") or ev.get("tecla") or "Desconocido")
                evento_txt = str(ev.get("tipo_evento") or ev.get("evento") or ev.get("alerta") or "Evento Online")
                disp_ev = ev.get("id_dispositivo") or ev.get("dispositivo") or 1

                if "RFID" in recurso_txt or "Chaveiro" in recurso_txt:
                    medio_especifico = "Tarjeta RFID (TAG XID)"
                elif "Controle" in recurso_txt or "RF" in recurso_txt:
                    medio_especifico = "Control Remoto (XTR)"
                elif "Senha" in recurso_txt or "Tecla" in recurso_txt:
                    medio_especifico = "Contraseña de Teclado"
                else:
                    medio_especifico = f"Medio: {recurso_txt}"

                is_panic = any(
                    w in (evento_txt.upper() + " " + recurso_txt.upper())
                    for w in ("PANICO", "PÂNICO", "COACAO", "COAÇÃO", "COACCION", "EMERGENCIA")
                )
                row_tags = ("panic",) if is_panic else ()
                if is_panic:
                    evento_txt = f"🚨 ALERTA DE PÁNICO / COACCIÓN: {evento_txt}"

                self.tree_online.insert("", 0, values=(
                    fecha_ev, apto_ev, nombre_ev, medio_especifico, evento_txt, disp_ev
                ), tags=row_tags)
            elif kind == "ev_progress":
                val, text = data
                self.ev_progress["value"] = val
                self.lbl_ev_status.config(text=text)
            elif kind == "events_loaded":
                self.btn_ev_today.config(state="normal")
                self.btn_ev_week.config(state="normal")
                for item in self.tree_ev.get_children():
                    self.tree_ev.delete(item)
                for ev in data:
                    self.tree_ev.insert("", 0, values=(
                        ev.get("id_evento", ""), ev.get("fecha", ""), ev.get("tipo_evento", ""),
                        ev.get("tipo_recurso", ""), ev.get("id_dispositivo", ""), ev.get("salida", ""),
                        ev.get("nombre", ""), ev.get("apto", ""), ev.get("bloco", ""), ev.get("placa", ""),
                    ))
            elif kind == "ai_progress":
                val, text = data
                self.ai_progress["value"] = val
                self.lbl_ai_status.config(text=text)
            elif kind == "ai_done":
                self.btn_run_ai.config(state="normal")
                analysis_results, day_counts, detailed_rows = data

                self.txt_ai_report.delete("1.0", "end")
                report_lines = []
                for item in analysis_results:
                    report_lines.append(f"--- RESIDENTE / USUARIO: {item['usuario']} (Apto {item['apto']}) ---")
                    report_lines.append(f"Total Eventos: {item['total']} | Nivel de Riesgo: [{item['semaforo']}]")
                    report_lines.append(f"Analisis e Historial: {item['observaciones']}\n")
                self.txt_ai_report.insert("end", "\n".join(report_lines))

                for item in self.tree_detail.get_children():
                    self.tree_detail.delete(item)
                for row in detailed_rows:
                    self.tree_detail.insert("", "end", values=(
                        row["fecha"], row["apto"], row["usuario"], row["medio_acceso"], row["evento"], row["dispositivo"]
                    ))

                self._render_bar_chart(day_counts)
        self.after(100, self._process_ui_queue)

    def _on_close(self) -> None:
        self.online_polling_active = False
        self.rtsp1_running = False
        self.rtsp2_running = False
        self.capture_stop_event.set()
        try:
            if self.raw_sip_socket is not None:
                self.raw_sip_socket.close()
        except Exception:
            pass
        try:
            if self.capture_handle is not None:
                self.capture_handle.close()
        except Exception:
            pass
        try:
            if self.sip_call is not None and PJSUA2_AVAILABLE:
                self.sip_call.hangup(pj.CallOpParam())
        except Exception:
            pass
        try:
            if self.sip_account is not None:
                self.sip_account.setRegistration(False)
        except Exception:
            pass
        try:
            if self.sip_endpoint is not None:
                self.sip_endpoint.libDestroy()
        except Exception:
            pass
        self.client.disconnect()
        self.destroy()