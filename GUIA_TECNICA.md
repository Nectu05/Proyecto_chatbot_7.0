# Guía Técnica del Proyecto: Chatbot de Fisioterapia "Gon"

**Autor:** Fabian Plaza
**Elaborado para:** Profesor Pablo Ortiz  


---

## 1. Descripción General
Este proyecto consiste en un **Chatbot Inteligente para Agendamiento de Citas de Fisioterapia**, integrado con **Telegram** y potenciado por **Inteligencia Artificial (Google Gemini)**. Su objetivo es automatizar la atención al cliente, permitiendo a los pacientes agendar, cancelar y reprogramar citas, así como resolver dudas generales de manera natural las 24 horas del día.

Además, el proyecto incluye una implementación complementaria en **React** (carpeta `gon---fisioterapia-bot`) para una versión web del asistente.

## 2. Funcionalidades Principales

### 🤖 Atención Inteligente (IA)
- **Conversación Natural**: Utiliza el modelo **Gemini 2.5 Flash** para entender la intención del usuario (saludos, preguntas de precios, síntomas, etc.) y responder de forma empática y contextual.
- **Detección de Intenciones**: Identifica si el usuario quiere agendar, cancelar, consultar precios o simplemente charlar.
- **Manejo de Audio**: Capaz de transcribir notas de voz enviadas por el usuario y procesarlas como texto.

### 📅 Gestión de Citas
- **Agendamiento Interactivo**: Muestra un calendario visual y botones de horas disponibles para facilitar la reserva.
- **Validación de Reglas de Negocio**:
    - No permite agendar los domingos ni festivos.
    - Exige agendar con al menos 1 día de anticipación.
    - Valida que el horario no esté ocupado por otro paciente.
- **Gestión de Usuario**: Permite al paciente ver sus citas activas, cancelarlas o reprogramarlas (siempre que falte más de 24h para la cita).

### 🛡️ Seguridad y Validación
- **Validación de Datos**: Verifica que la cédula y el celular contengan solo números (y espacios/+) y que el nombre no tenga caracteres inválidos.
- **Filtros de Visualización**: Los usuarios solo ven sus citas futuras o del día actual; el historial pasado se oculta para mantener la interfaz limpia.
- **Protección de Credenciales**: Las claves sensibles (Tokens de Telegram, API Keys de Google, Credenciales de Base de Datos) **NO se comparten** en el código fuente. Se utilizan variables de entorno (`.env`) para garantizar la seguridad del proyecto.

### 📊 Reportes Financieros
- **Generación de PDFs**: Incluye un módulo para generar reportes de ingresos por rango de fechas, útil para la administración del consultorio.

---

## 3. Arquitectura y Tecnologías Usadas

El proyecto fue desarrollado principalmente en **Python** para el backend/bot de Telegram, y cuenta con un componente frontend en **React**.

### 📚 Bibliotecas y Componentes Clave

#### Backend (Python - Telegram Bot)
1.  **`python-telegram-bot`**: Núcleo del bot para la conexión con Telegram.
2.  **`google-generativeai`**: Conexión con la API de Google Gemini ("cerebro" del bot).
3.  **`pyodbc`**: Conexión con la base de datos SQL Server.
4.  **`reportlab`**: Generación de reportes financieros en PDF.
5.  **`holidays`**: Detección automática de festivos en Colombia.

#### Frontend (React - Web Version)
-   Ubicado en la carpeta: **`gon---fisioterapia-bot`**.
-   Implementación de la interfaz de usuario del chatbot utilizando **React.js**.
-   Permite una integración visual en navegadores web, complementando la experiencia de Telegram.

### 📂 Estructura de Archivos

*   **`bot.py`**: Lógica principal y flujo de conversación (Telegram).
*   **`config.py`**: Configuración y variables de entorno.
*   **`gemini_service.py`**: Comunicación con la IA.
*   **`database.py`**: Capa de acceso a datos.
*   **`utils.py`**: Funciones auxiliares (calendarios, validaciones).
*   **`generar_reporte.py`**: Script de reportes.
*   **`gon---fisioterapia-bot/`**: Código fuente de la implementación en React.

---

## 4. Escalabilidad, Despliegue y Versatilidad

Este proyecto ha sido desarrollado y probado en un entorno **local** para validar su funcionamiento, pero está diseñado con una arquitectura modular que permite su fácil escalabilidad y despliegue en la nube.

### 🚀 Potencial de Migración a la Nube
- **Servidores**: El código es compatible para ser desplegado en plataformas como **Heroku**, **Render** o **AWS**, permitiendo que el bot esté activo 24/7 sin depender de un equipo local encendido.
- **Base de Datos**: Aunque actualmente utiliza SQL Server, la capa de datos (`database.py`) está aislada, lo que facilita la migración a bases de datos en la nube como **MongoDB** (NoSQL) o **Azure SQL** si el volumen de datos crece significativamente.
- **Repositorio**: El uso de **GitHub** permite la integración continua (CI/CD), facilitando actualizaciones automáticas en el servidor productivo.

### 🌐 Versatilidad Multiplataforma (Web y WhatsApp)
La lógica central del chatbot (IA y gestión de citas) es agnóstica a la plataforma de mensajería. Esto significa que el sistema está preparado para integrarse con:
-   **Páginas Web**: Como se evidencia con el código fuente en React incluido en el proyecto.
-   **WhatsApp Business**: Utilizando la API oficial de Meta.

**Decisión de Diseño (Telegram vs WhatsApp):**
Para esta fase de implementación y validación, se seleccionó **Telegram** debido a que su API es **completamente gratuita** y abierta. Esto permite desarrollar un producto mínimo viable (MVP) funcional y robusto sin incurrir en los costos por conversación que cobra la API de WhatsApp Business, haciendo el proyecto más viable económicamente en sus etapas iniciales.

---

## 5. Guía de Desarrollo (Cómo se creó)

1.  **Configuración del Entorno**: Se creó un entorno virtual (`venv`) para aislar las dependencias.
2.  **Diseño de la Base de Datos**: Estructuración de tablas para Pacientes, Servicios y Citas.
3.  **Integración con Telegram**: Configuración del bot para escuchar mensajes.
4.  **Implementación de la IA**: Diseño del "Prompt del Sistema" para la personalidad de "Gon".
5.  **Desarrollo de Flujos**: Programación de la lógica de agendamiento paso a paso.
6.  **Versión Web (React)**: Desarrollo de la interfaz frontend en la carpeta `gon---fisioterapia-bot` para ofrecer una alternativa web.
7.  **Refinamiento**: Implementación de validaciones estrictas y mejoras de seguridad.

---

**Repositorio del Proyecto:** [Enlace al repositorio]
**Contacto:** portizg21@gmail.com
