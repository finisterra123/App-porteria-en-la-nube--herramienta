# herramienta Mip 1000 ip by ING Ricardo Rodriguez

Transformación integral de la app móvil hacia una **consola técnica pura estilo botonera táctil**, eliminando por completo los módulos de tickets y alertas, y concentrando el 100% de la interfaz en herramientas operativas directas para testear porterías en la nube, abrir puertas XRE 1000/MIP 1000, verificar SIP ALG, probar voz IP y cámaras RTSP.

## Decisiones Críticas y Preferencias Confirmadas

> [!IMPORTANT]
> - **Sin módulo de tickets ni alertas**: Se remueve toda la lógica y vistas de gestión de tickets, diagnósticos teóricos y alertas de pánico.
> - **Diseño tipo botonera técnica**: Disposición en cuadrícula táctil con botones grandes de alto contraste y respuesta inmediata, optimizada para uso con una sola mano en campo.
> - **Branding Oficial**: `herramienta Mip 1000 ip by ING Ricardo Rodriguez` en cabecera y metadatos.

---

### 1. Concepto Central y Flujo Operativo

La aplicación servirá como el instrumento de bolsillo definitivo para el ingeniero o técnico de campo al momento de comisionar, probar y entregar una **portería en la nube** con controladores Intelbras MIP 1000 IP y módulos expansores RS-485 XRE 1000.

El técnico podrá:
1. Conectarse vía TCP al MIP 1000 IP ingresando IP, puerto (9080), usuario y contraseña.
2. Visualizar inmediatamente **todas las puertas disponibles** (relevadores de la placa base del MIP y de cada módulo XRE 1000 Plus) y abrirlas con un toque (ASR 0x18) con temporizador visual regresivo de 3 segundos.
3. Sincronizar la hora del MIP con el celular (CD 0x08) y cambiar el mensaje en pantalla LCD (MG 0x22).
4. Realizar la prueba crítica de **SIP ALG** hacia el servidor PBX en la nube (`d8365fbf8b9c.porteriaenlanube.com:5080`) para descartar alteraciones de NAT en el router.
5. Hacer ping y llamar a extensiones de citofonía con el softphone móvil integrado.
6. Probar streams y puertos RTSP (554) de las cámaras con verificación de códec H.264.
7. Capturar llaveros TAG RFID (0x1C) y controles vehiculares XTR (0x26) en la antena del equipo.
8. Monitorear las tramas hexadecimales TX/RX en la consola inferior en vivo.

---

### 2. Arquitectura de Pantalla y Botonera Táctica

```
┌─────────────────────────────────────────────────────────────┐
│ 🛡️ herramienta Mip 1000 ip by ING Ricardo Rodriguez         │
│ Conexión TCP: [179.33.25.101:9080] [ESTADO: CONECTADO]      │
├─────────────────────────────────────────────────────────────┤
│ 🚪 BOTONERA DE APERTURA DE TODAS LAS PUERTAS (ASR 0x18)     │
│ ┌───────────────────────────┐ ┌───────────────────────────┐ │
│ │ 🔓 PEATONAL PRINCIPAL     │ │ 🔓 PORTÓN VEHICULAR (XRE) │ │
│ │ MIP Dir 1 · Relé 1        │ │ XRE #1 Dir 2 · Relé 1     │ │
│ └───────────────────────────┘ └───────────────────────────┘ │
│ ┌───────────────────────────┐ ┌───────────────────────────┐ │
│ │ 🔓 BARRERA SALIDA (XRE)   │ │ 🔓 PUERTA SECUNDARIA      │ │
│ │ XRE #2 Dir 3 · Relé 1     │ │ MIP Dir 1 · Relé 2        │ │
│ └───────────────────────────┘ └───────────────────────────┘ │
│ [ ⚡ Disparador Universal: Dirección RS-485 [1..24] Relé [1..8] ]│
├─────────────────────────────────────────────────────────────┤
│ ⚙️ CONFIGURACIÓN RÁPIDA MIP 1000                            │
│ [ 🕒 Sincronizar Hora Celular (CD) ] [ 💬 Mensaje LCD (MG) ]│
│ [ 🔍 Consultar UID/MAC/FW (0x32)   ] [ 📊 Contadores (VS)  ]│
├─────────────────────────────────────────────────────────────┤
│ 📞 TESTEO SIP ALG & CITOFONÍA EN LA NUBE                    │
│ [ 🌐 Sondeo OPTIONS / SIP ALG ] [ 🔔 Ping Extensión 990001] │
│ [ 📞 Probar Llamada VoIP a Conserjería (Softphone)         ]│
├─────────────────────────────────────────────────────────────┤
│ 📹 TESTEO DE CÁMARAS RTSP (PUERTO 554)                      │
│ [ 🎥 Cam 1 Lobby (H.264) ] [ 🎥 Cam 2 Portón Vehicular ]   │
├─────────────────────────────────────────────────────────────┤
│ 🔑 CAPTURA DE CREDENCIALES EN ANTENA                        │
│ [ 📡 Capturar TAG RFID (0x1C) ] [ 🚗 Capturar Control (0x26)│
├─────────────────────────────────────────────────────────────┤
│ 💻 CONSOLA DE TRAMAS HEXADECIMALES (TX / RX EN VIVO)        │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. Componentes a Reestructurar y Eliminar

1. **Eliminar**:
   - `KanbanBoard.tsx` (módulo de tickets).
   - `TicketCard.tsx` y `TicketDetailModal.tsx`.
   - `CreateTicketModal.tsx`.
   - Lógica y tipos asociados a tickets y alertas de pánico.
2. **Reestructurar**:
   - `Header.tsx`: Mostrar el nuevo nombre oficial `herramienta Mip 1000 ip by ING Ricardo Rodriguez` y el indicador de enlace TCP.
   - `DoorsKeypad.tsx`: Matriz táctil de puertas detectadas en el MIP 1000 y módulos XRE 1000 con temporizador de pulso háptico de 3 segundos y disparador universal RS-485.
   - `MipConfigPanel.tsx`: Sincronización horaria (CD 0x08), simulador de mensaje display LCD retroiluminado (MG 0x22), lectura de UID/MAC (UID 0x32) y contadores de memoria (VS 0x17).
   - `SipAlgTester.tsx`: Diagnóstico de router para portería en la nube, softphone SIP 2.0 y monitor de señalización.
   - `CameraRtsptester.tsx`: Comprobación de socket TCP 554, advertencia de códec H.264/H.265 y previsualización.
   - `CredentialScanner.tsx`: Captura de llaveros XID y controles XTR con vinculación a apartamento.
   - `HexConsole.tsx`: Registro permanente en la parte inferior de las tramas del protocolo V2.

---

### 4. Plan de Verificación

- **Pruebas unitarias (`node:test`)**: Verificar tramas ASR, comandos de reloj CD, mensajes LCD MG, cálculo de direcciones RS-485 y detector de SIP ALG.
- **Compilación TypeScript / Vite**: `compile_applet` y `lint_applet` sin errores.
- **Validación visual con Playwright CLI**: Inspección en viewport móvil de 390×844 para comprobar la botonera táctil, respuesta de aperturas y diseño compacto.
