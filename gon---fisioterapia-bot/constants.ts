
import { Service } from './types';

export const CLINIC_INFO = {
  name: "Consultorio Ana María López Fisioterapia Especializada",
  therapist: "Ana María López",
  address: "Cra 7 # 10N - 16, barrio Prados del Norte, frente al Bambi del Norte, Popayán, Colombia",
  mapUrl: "https://maps.app.goo.gl/XqJX1Xb177k7Dqk36",
  botName: "Gon"
};

export const SERVICES: Service[] = [
  { id: 1, nombre: "Consulta", duracion: 60, precio: 65000, description: "Evaluación completa inicial para diagnóstico fisioterapéutico." },
  { id: 2, nombre: "Valoración por fisioterapia + ecografía especializada", duracion: 60, precio: 85000, description: "Diagnóstico preciso mediante tecnología de ultrasonido." },
  { id: 3, nombre: "Sesión de descarga muscular en piernas", duracion: 90, precio: 75000, description: "Recuperación muscular profunda enfocada en extremidades inferiores." },
  { id: 4, nombre: "Terapia física avanzada y manejo del dolor", duracion: 60, precio: 65000, description: "Tratamiento integral para aliviar dolor y recuperar movilidad." },
  { id: 5, nombre: "Paquete 5 sesiones terapia física y manejo del dolor", duracion: 300, precio: 250000, description: "Plan completo de recuperación con descuento especial." },
  { id: 6, nombre: "Sesión de ejercicio personalizado", duracion: 60, precio: 50000, description: "Rutinas guiadas adaptadas a tus necesidades físicas." },
  { id: 7, nombre: "Sesión recovery y relajación", duracion: 80, precio: 80000, description: "Terapia regenerativa para reducir estrés físico." },
  { id: 8, nombre: "Entrenamiento deportivo", duracion: 60, precio: 60000, description: "Mejora de rendimiento enfocado en tu disciplina." },
  { id: 9, nombre: "Acondicionamiento físico en el embarazo", duracion: 60, precio: 50000, description: "Ejercicios seguros para la salud de la mamá y el bebé." },
  { id: 10, nombre: "Sesión pilates piso", duracion: 60, precio: 50000, description: "Fortalecimiento del core y mejora de la postura." },
  { id: 11, nombre: "Plasma rico en plaquetas", duracion: 60, precio: 165000, description: "Terapia regenerativa para lesiones articulares o musculares." },
  { id: 12, nombre: "3 sesiones plasma rico en plaquetas", duracion: 180, precio: 450000, description: "Tratamiento completo regenerativo." },
  { id: 13, nombre: "Limpieza facial profunda", duracion: 90, precio: 90000, description: "Higiene facial clínica para renovar tu piel." },
  { id: 14, nombre: "Limpieza facial profunda con alta hidratación", duracion: 120, precio: 120000, description: "Tratamiento intensivo de hidratación y limpieza." },
  { id: 15, nombre: "Plasma rico en hidratación facial + plaquetas", duracion: 60, precio: 160000, description: "Rejuvenecimiento facial avanzado." },
  { id: 16, nombre: "Educación continua", duracion: 0, precio: 0, description: "Talleres y formación especializada." },
  { id: 17, nombre: "Venta de insumos y suministros médicos", duracion: 0, precio: 0, description: "Productos especializados para tu recuperación." },
];

export const SYSTEM_INSTRUCTION = `
Eres Gon, el asistente virtual comercial e inteligente del consultorio de Fisioterapia de Ana María López.

INFORMACIÓN DEL NEGOCIO:
- Fisioterapeuta: ${CLINIC_INFO.therapist}
- Dirección: ${CLINIC_INFO.address} (Mapa: ${CLINIC_INFO.mapUrl})
- Horarios: Lunes a Sábado, 9am-12pm y 2pm-7pm. Dom/Festivos CERRADO.

TU OBJETIVO:
Concretar citas, ayudar a modificarlas y brindar soporte, pero manteniendo una conversación natural.

DIRECTRICES DE INTELIGENCIA (IMPORTANTE):

1. **Fase de Saludo:**
   - Saludo simple -> INTENT: 'greeting'.
   - NO SUGERIR botones.

2. **Fase de Oportunidad:**
   - "Quiero cita", "Dolor", "Precios", "Horarios" -> INTENT: 'booking_request'.
   - SUGERIR botones 'suggestedServiceIds': [1, 2].

3. **Gestión de Citas (Consulta, Cancelación, Modificación):**
   - Si el usuario quiere "Consultar", "Cancelar", "Cambiar hora", "Mover cita", "Reprogramar", "Modificar":
   - TU RESPUESTA: "Claro, para gestionar tu cita (consultar, cancelar o modificar), por favor ingresa tu documento en el formulario."
   - INTENT: 'check_appointment' (o 'reschedule' o 'cancellation').
   - NO pidas la cédula por chat.

4. **Contexto Temporal:**
   - HOY es HOY. No agendar para hoy.

CATÁLOGO:
${JSON.stringify(SERVICES.map(s => ({ id: s.id, nombre: s.nombre })))}

SALIDA JSON:
{
  "message": "Texto de respuesta",
  "intent": "greeting" | "booking_request" | "revenue_report" | "check_appointment" | "cancellation" | "reschedule" | "general",
  "suggestedServiceIds": []
}
`;