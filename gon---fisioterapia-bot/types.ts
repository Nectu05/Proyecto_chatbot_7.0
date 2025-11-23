
export interface Service {
  id: number;
  nombre: string;
  duracion: number; // minutes
  precio: number;
  description?: string;
}

export interface Appointment {
  id: string;
  patientName: string;
  patientId: string; // Cédula
  patientPhone: string;
  serviceId: number;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM
  status: 'confirmed' | 'cancelled';
  reminded?: boolean; // Track if a reminder has been sent
}

export type Sender = 'user' | 'bot';

export interface Message {
  id: string;
  text: string;
  sender: Sender;
  timestamp: Date;
  type?: 'text' | 'service_suggestion' | 'service_list' | 'appointment_form' | 'appointment_confirmed' | 'appointment_ticket';
  payload?: any;
  interactionComplete?: boolean;
}

export interface GeminiResponseSchema {
  message: string;
  intent: 'greeting' | 'symptom_analysis' | 'show_all_services' | 'booking_request' | 'cancellation' | 'price_inquiry' | 'general' | 'invoice_analysis' | 'check_appointment' | 'revenue_report' | 'reschedule';
  suggestedServiceIds?: number[];
  extractedInvoiceData?: {
    amount: number;
    date: string;
  };
}
