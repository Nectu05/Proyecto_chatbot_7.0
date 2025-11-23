
import React, { useState, useEffect, useRef } from 'react';
import { Message, Service, Appointment } from './types';
import { SERVICES, CLINIC_INFO } from './constants';
import { sendMessageToGemini } from './services/geminiService';
import ServiceCard from './components/ServiceCard';
import AppointmentModal from './components/AppointmentModal';
import CheckAppointmentModal from './components/CheckAppointmentModal';
import { formatDateFull } from './utils/timeUtils';

// Helper for IDs in environments where crypto.randomUUID might be unavailable
const generateId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
};

const App: React.FC = () => {
  // SQL SERVER SIMULATION (Persistence)
  const [appointments, setAppointments] = useState<Appointment[]>(() => {
      const saved = localStorage.getItem('gon_appointments_db');
      return saved ? JSON.parse(saved) : [];
  });

  // Save to "DB" whenever appointments change
  useEffect(() => {
      localStorage.setItem('gon_appointments_db', JSON.stringify(appointments));
  }, [appointments]);

  // REMINDER SYSTEM
  useEffect(() => {
    // 1. Request Notification Permission on Load
    if ('Notification' in window && Notification.permission !== 'granted') {
      Notification.requestPermission();
    }

    // 2. Reminder Loop (Checks every 60 seconds)
    const checkReminders = () => {
      const now = new Date();
      
      setAppointments(prevApps => {
        let updatesMade = false;
        const updatedApps = prevApps.map(app => {
          // Skip if cancelled or already reminded
          if (app.status !== 'confirmed' || app.reminded) return app;

          // Construct Date Object
          const appDate = new Date(`${app.date}T${app.time}:00`);
          const diffMs = appDate.getTime() - now.getTime();
          const diffHours = diffMs / (1000 * 60 * 60);

          // Logic: Remind if appointment is within the next 24 hours (and in the future)
          if (diffHours > 0 && diffHours <= 24) {
            
            // A. Trigger Browser Notification
            if ('Notification' in window && Notification.permission === 'granted') {
              new Notification(`Recordatorio de Cita - ${CLINIC_INFO.botName}`, {
                body: `Hola ${app.patientName}, recuerda tu cita de ${SERVICES.find(s => s.id === app.serviceId)?.nombre} mañana a las ${app.time}.`,
                icon: '/favicon.ico' // Optional
              });
            }

            // B. Trigger Chat Message
            const reminderMsg: Message = {
              id: generateId(),
              text: `🔔 **Recordatorio Automático**\n\nHola ${app.patientName}, paso a recordarte que tienes una cita programada para el ${formatDateFull(app.date)} a las ${app.time}.\n\nTe esperamos en: ${CLINIC_INFO.address}.`,
              sender: 'bot',
              timestamp: new Date(),
              type: 'text'
            };
            
            // We need to use a functional update for messages inside the interval, 
            // but since we are inside setAppointments, we'll dispatch an event or use a ref 
            // to avoid complex dependency loops. simpler here to just force the message update separately.
            // However, React state updates in intervals need care. 
            // We will use a separate side-effect outside map to update messages.
            
            // Mark as reminded
            updatesMade = true;
            // Side effect: Add message to chat
            setMessages(msgs => [...msgs, reminderMsg]);

            return { ...app, reminded: true };
          }
          return app;
        });

        return updatesMade ? updatedApps : prevApps;
      });
    };

    const intervalId = setInterval(checkReminders, 60000); // Check every minute
    checkReminders(); // Run immediately on load

    return () => clearInterval(intervalId);
  }, []); 

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      text: `Hola, soy ${CLINIC_INFO.botName}, asistente virtual del ${CLINIC_INFO.name}. ¿En qué puedo ayudarte hoy?`,
      sender: 'bot',
      timestamp: new Date(),
      type: 'text'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  // Modals & Overlays
  const [showAllServices, setShowAllServices] = useState(false);
  const [viewingServiceInModal, setViewingServiceInModal] = useState<Service | null>(null);
  
  const [selectedServiceForBooking, setSelectedServiceForBooking] = useState<Service | null>(null);
  const [showCheckAppointmentModal, setShowCheckAppointmentModal] = useState(false);

  // Cancellation & Rescheduling State
  const [appointmentToCancel, setAppointmentToCancel] = useState<string | null>(null); // ID of appt to cancel
  const [reschedulingAppointmentId, setReschedulingAppointmentId] = useState<string | null>(null);
  const [reschedulingInitialData, setReschedulingInitialData] = useState<any>(null);
  
  // Refs for scrolling
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text: string, imageBase64?: string) => {
    if ((!text.trim() && !imageBase64) || isLoading) return;

    const newMessage: Message = {
      id: generateId(),
      text: text || (imageBase64 ? "Imagen adjuntada" : ""),
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, newMessage]);
    setInputText('');
    setIsLoading(true);

    const history = messages.map(m => ({
      role: m.sender === 'user' ? 'user' : 'model',
      parts: [{ text: m.text }]
    }));

    const aiResponse = await sendMessageToGemini(history, text, imageBase64);

    setIsLoading(false);

    const botMessage: Message = {
      id: generateId(),
      text: aiResponse.message,
      sender: 'bot',
      timestamp: new Date(),
      type: 'text'
    };

    // LOGIC: Suggestions
    if (aiResponse.suggestedServiceIds && aiResponse.suggestedServiceIds.length > 0) {
       botMessage.type = 'service_suggestion';
       botMessage.payload = aiResponse.suggestedServiceIds;
    }

    if (aiResponse.intent === 'show_all_services') {
        botMessage.type = 'service_list';
    }
    
    // LOGIC: Check / Cancel / Reschedule (All trigger ID check)
    if (aiResponse.intent === 'check_appointment' || aiResponse.intent === 'cancellation' || aiResponse.intent === 'reschedule') {
        setTimeout(() => setShowCheckAppointmentModal(true), 500);
    }
    
    if (aiResponse.intent === 'invoice_analysis' && aiResponse.extractedInvoiceData) {
        botMessage.text = `${aiResponse.message} \n\nMonto detectado: $${aiResponse.extractedInvoiceData.amount} \nFecha: ${aiResponse.extractedInvoiceData.date}`;
    }

    if (aiResponse.intent === 'revenue_report') {
        const totalRevenue = appointments
         .filter(app => app.status === 'confirmed')
         .reduce((sum, app) => {
              const service = SERVICES.find(s => s.id === app.serviceId);
              return sum + (service ? service.precio : 0);
         }, 0);
 
        botMessage.text = `📊 Reporte de Ventas (Sesión Actual):\n\nCitas confirmadas: ${appointments.length}\nTotal Generado: $${totalRevenue.toLocaleString('es-CO')}\n\n${aiResponse.message}`;
    }

    setMessages(prev => [...prev, botMessage]);
  };

  const handleCheckAppointmentSearch = (patientId: string) => {
      setShowCheckAppointmentModal(false);
      
      // LIVE SQL QUERY from "DB" (State)
      const foundAppointments = appointments.filter(
          app => app.patientId === patientId && app.status === 'confirmed'
      );

      if (foundAppointments.length > 0) {
          const ticketMsg: Message = {
              id: generateId(),
              text: `He encontrado ${foundAppointments.length} cita(s) activa(s). Aquí tienes los detalles:`,
              sender: 'bot',
              timestamp: new Date(),
              type: 'appointment_ticket',
              payload: foundAppointments
          };
          setMessages(prev => [...prev, ticketMsg]);
      } else {
          const notFoundMsg: Message = {
              id: generateId(),
              text: `No encontré ninguna cita activa registrada con la cédula ${patientId}. ¿Deseas agendar una nueva?`,
              sender: 'bot',
              timestamp: new Date(),
              type: 'text'
          };
          setMessages(prev => [...prev, notFoundMsg]);
      }
  };

  const handleCancelAppointment = (appointmentId: string) => {
      // Using custom Modal via State instead of window.confirm
      setAppointmentToCancel(appointmentId);
  };

  const confirmCancellation = () => {
      if (!appointmentToCancel) return;

      // SQL UPDATE
      setAppointments(prev => prev.map(app => 
        app.id === appointmentToCancel ? { ...app, status: 'cancelled' } : app
      ));
      
      setAppointmentToCancel(null);

      const cancelMsg: Message = {
          id: generateId(),
          text: `✅ La cita ha sido cancelada correctamente y el horario ha sido liberado.`,
          sender: 'bot',
          timestamp: new Date(),
          type: 'text'
      };
      setMessages(prev => [...prev, cancelMsg]);
  };

  const handleRescheduleAppointment = (appointment: Appointment) => {
      // 1. Find Service
      const service = SERVICES.find(s => s.id === appointment.serviceId);
      if (!service) return;

      // 2. Set Reschedule State (to know we are modifying, not just booking new)
      setReschedulingAppointmentId(appointment.id);
      setReschedulingInitialData({
          patientName: appointment.patientName,
          patientId: appointment.patientId,
          patientPhone: appointment.patientPhone
      });
      
      // 3. Open Booking Modal
      setSelectedServiceForBooking(service);
  };

  const handleBookingConfirm = (appointmentData: Omit<Appointment, 'id' | 'status'>) => {
      // SQL TRANSACTION SIMULATION: Check for double booking
      const isSlotTaken = appointments.some(app => 
          app.date === appointmentData.date && 
          app.time === appointmentData.time && 
          app.status === 'confirmed' &&
          app.id !== reschedulingAppointmentId // Ignore itself if modifying
      );

      if (isSlotTaken) {
          alert("Lo sentimos, ese horario acaba de ser ocupado por otro paciente. Por favor selecciona otra hora.");
          return;
      }

      // Close Modal
      setSelectedServiceForBooking(null);
      
      // If Rescheduling -> Cancel Old One First
      if (reschedulingAppointmentId) {
          setAppointments(prev => prev.map(app => 
              app.id === reschedulingAppointmentId ? { ...app, status: 'cancelled' } : app
          ));
          setReschedulingAppointmentId(null); // Reset
          setReschedulingInitialData(null);
      }

      // Create New Record
      const newAppointment: Appointment = {
        id: generateId(),
        status: 'confirmed',
        ...appointmentData,
        reminded: false // Reset reminded status for new/rescheduled appt
      };
      
      setAppointments(prev => [...prev, newAppointment]);

      const readableDate = formatDateFull(appointmentData.date);
      const actionText = reschedulingAppointmentId ? "reprogramada" : "agendada";

      const successMsg: Message = {
          id: generateId(),
          text: `¡Listo ${appointmentData.patientName}! Tu cita para ${SERVICES.find(s => s.id === appointmentData.serviceId)?.nombre} ha sido ${actionText} para el ${readableDate} a las ${appointmentData.time}.`,
          sender: 'bot',
          timestamp: new Date(),
          type: 'appointment_confirmed'
      };
      setMessages(prev => [...prev, successMsg]);

      setTimeout(() => {
        const followUpMsg: Message = {
            id: generateId(),
            text: `¿Hay algo más en lo que pueda asistirte?`,
            sender: 'bot',
            timestamp: new Date(),
            type: 'text'
        };
        setMessages(prev => [...prev, followUpMsg]);
      }, 1500);
  };

  const handleServiceSelectFromChat = (service: Service, messageId: string) => {
      setMessages(prev => prev.map(msg => 
          msg.id === messageId ? { ...msg, interactionComplete: true } : msg
      ));
      setShowAllServices(true);
      setViewingServiceInModal(service);
  };

  const handleOpenMenuFromChat = (messageId: string) => {
      setMessages(prev => prev.map(msg => 
          msg.id === messageId ? { ...msg, interactionComplete: true } : msg
      ));
      setShowAllServices(true);
      setViewingServiceInModal(null);
  };

  const handleServiceSelectConfirmed = (service: Service) => {
     setShowAllServices(false);
     setViewingServiceInModal(null);

     const confirmMsg: Message = {
        id: generateId(),
        text: `Me gustaría agendar: ${service.nombre}`,
        sender: 'user',
        timestamp: new Date()
     };
     setMessages(prev => [...prev, confirmMsg]);
     
     setTimeout(() => {
        // Reset rescheduling state if this was a fresh booking flow
        setReschedulingAppointmentId(null);
        setReschedulingInitialData(null);
        setSelectedServiceForBooking(service);
     }, 500);
  };

  // Voice & File logic (abbreviated for standard handlers)
  const handleVoiceInput = () => {
    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SpeechRecognition) return alert("Navegador no compatible");
    const recognition = new SpeechRecognition();
    recognition.lang = 'es-CO';
    recognition.onstart = () => setIsRecording(true);
    recognition.onend = () => setIsRecording(false);
    recognition.onresult = (e: any) => setInputText(e.results[0][0].transcript);
    recognition.start();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
        const r = new FileReader();
        r.onloadend = () => handleSend("", r.result as string);
        r.readAsDataURL(file);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 overflow-hidden">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center shadow-sm z-10">
        <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center text-teal-600 mr-3 font-bold text-lg">AL</div>
        <div>
            <h1 className="font-bold text-gray-800 leading-tight">Ana María López</h1>
            <p className="text-xs text-gray-500">Fisioterapia Especializada • Bot Gon</p>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[90%] md:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm ${
              msg.sender === 'user' 
                ? 'bg-teal-600 text-white rounded-tr-none' 
                : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
            }`}>
              <div className="whitespace-pre-wrap text-sm md:text-base leading-relaxed">
                  {msg.text}
              </div>
              
              {!msg.interactionComplete && msg.type === 'service_suggestion' && msg.payload && (
                  <div className="mt-4 animate-fade-in">
                      <p className="text-xs text-gray-500 font-medium mb-2 uppercase">Opciones Recomendadas:</p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {msg.payload.map((sId: number) => {
                            const s = SERVICES.find(ser => ser.id === sId);
                            if(!s) return null;
                            return <ServiceCard key={s.id} service={s} onSelect={(s) => handleServiceSelectFromChat(s, msg.id)} compact={true} />;
                        })}
                      </div>
                      <button onClick={() => handleOpenMenuFromChat(msg.id)} className="w-full mt-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-xs font-medium text-gray-600 transition-colors flex items-center justify-center">
                            <span>Ver todos los servicios</span>
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                        </button>
                  </div>
              )}

               {!msg.interactionComplete && msg.type === 'service_list' && (
                   <div className="mt-3">
                       <button onClick={() => handleOpenMenuFromChat(msg.id)} className="bg-teal-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium shadow-md hover:bg-teal-700 transition-all w-full sm:w-auto">
                           Abrir Menú de Servicios
                       </button>
                   </div>
               )}

               {msg.interactionComplete && (msg.type === 'service_suggestion' || msg.type === 'service_list') && (
                   <div className="mt-2 pt-2 border-t border-gray-100 text-xs text-gray-400 italic flex items-center">
                       <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
                       Selección realizada
                   </div>
               )}

               {msg.type === 'appointment_ticket' && msg.payload && (
                 <div className="mt-4 space-y-3 animate-fade-in">
                    {msg.payload.map((snapshotApp: Appointment) => {
                        // LIVE DATA LOOKUP (Simulating SQL query by ID)
                        const liveApp = appointments.find(a => a.id === snapshotApp.id) || snapshotApp;
                        const isCancelled = liveApp.status === 'cancelled';
                        
                        return (
                          <div key={liveApp.id} className={`bg-white border border-gray-200 rounded-xl p-4 shadow-md border-l-4 ${isCancelled ? 'border-l-gray-400 opacity-80' : 'border-l-teal-500'}`}>
                              <div className="flex justify-between items-center mb-3">
                                  <span className={`text-xs font-bold uppercase tracking-wider px-2 py-1 rounded ${isCancelled ? 'bg-gray-200 text-gray-600' : 'bg-teal-50 text-teal-600'}`}>
                                      {isCancelled ? 'Cita Cancelada' : 'Cita Confirmada'}
                                  </span>
                                  <span className="text-xs text-gray-400">ID: {liveApp.id.slice(-4)}</span>
                              </div>
                              <div className="mb-2">
                                  <p className="text-sm text-gray-500">Servicio</p>
                                  <p className="font-bold text-gray-800">{SERVICES.find(s => s.id === liveApp.serviceId)?.nombre}</p>
                              </div>
                              <div className="grid grid-cols-2 gap-4 mb-3">
                                  <div>
                                      <p className="text-xs text-gray-500">Fecha</p>
                                      <p className="font-medium text-gray-800">{formatDateFull(liveApp.date)}</p>
                                  </div>
                                  <div>
                                      <p className="text-xs text-gray-500">Hora</p>
                                      <p className="font-medium text-gray-800">{liveApp.time}</p>
                                  </div>
                              </div>
                              <div className="pt-3 border-t border-gray-100 text-xs text-gray-500 grid grid-cols-2 gap-2 mb-3">
                                  <div><span className="block">Paciente:</span><span className="font-medium text-gray-700">{liveApp.patientName}</span></div>
                                  <div><span className="block">Cédula:</span><span className="font-medium text-gray-700">{liveApp.patientId}</span></div>
                              </div>
                              
                              {!isCancelled && (
                                <div className="flex space-x-2 mt-4 pt-3 border-t border-gray-100">
                                    <button 
                                        onClick={() => handleRescheduleAppointment(liveApp)}
                                        className="flex-1 py-2 bg-teal-50 border border-teal-200 text-teal-700 text-xs font-bold rounded-lg hover:bg-teal-100 transition-colors flex items-center justify-center"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                        Modificar
                                    </button>
                                    <button 
                                        onClick={() => handleCancelAppointment(liveApp.id)}
                                        className="flex-1 py-2 bg-red-50 border border-red-200 text-red-600 text-xs font-bold rounded-lg hover:bg-red-100 transition-colors flex items-center justify-center"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                        Cancelar
                                    </button>
                                </div>
                              )}
                          </div>
                        );
                    })}
                 </div>
               )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </main>

      <footer className="bg-white border-t border-gray-200 p-3 md:p-4 z-10">
        <div className="max-w-4xl mx-auto flex items-end space-x-2">
            <button onClick={() => fileInputRef.current?.click()} className="p-3 text-gray-400 hover:text-teal-600 hover:bg-gray-100 rounded-full transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
                <input type="file" ref={fileInputRef} className="hidden" accept="image/*" onChange={handleFileUpload}/>
            </button>
            <div className="flex-1 bg-gray-100 rounded-2xl flex items-center px-4 py-2 focus-within:ring-2 focus-within:ring-teal-500/50 transition-all border border-transparent focus-within:border-teal-500 focus-within:border-teal-500 focus-within:bg-white">
                <textarea rows={1} className="flex-1 bg-transparent outline-none text-gray-800 resize-none max-h-32 py-2" placeholder="Escribe un mensaje..." value={inputText} onChange={(e) => setInputText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(inputText); } }} />
            </div>
            {inputText.trim() ? (
                <button onClick={() => handleSend(inputText)} className="p-3 bg-teal-600 text-white rounded-full hover:bg-teal-700 shadow-md transition-transform active:scale-90">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor"><path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" /></svg>
                </button>
            ) : (
                <button onClick={handleVoiceInput} className={`p-3 rounded-full transition-all shadow-md ${isRecording ? 'bg-red-500 text-white animate-pulse' : 'bg-teal-600 text-white hover:bg-teal-700'}`}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
                </button>
            )}
        </div>
      </footer>

      {/* Modals */}
      {showAllServices && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 backdrop-blur-sm transition-opacity">
              <div className="bg-white w-full max-w-3xl h-[85vh] sm:h-[80vh] rounded-t-3xl sm:rounded-2xl flex flex-col shadow-2xl animate-fade-in-up overflow-hidden">
                  <div className="px-5 py-4 border-b flex justify-between items-center bg-white z-10 shrink-0">
                      <div className="flex items-center">
                          {viewingServiceInModal && (
                              <button onClick={() => setViewingServiceInModal(null)} className="mr-3 p-1.5 rounded-full hover:bg-gray-100 text-gray-600 transition-colors"><svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg></button>
                          )}
                          <h2 className="font-bold text-xl text-gray-800 truncate">{viewingServiceInModal ? 'Confirmar Selección' : 'Nuestros Servicios'}</h2>
                      </div>
                      <button onClick={() => setShowAllServices(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors"><svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
                  </div>
                  <div className="flex-1 overflow-y-auto bg-gray-50/50 relative">
                      {viewingServiceInModal ? (
                          <div className="p-6 flex flex-col h-full">
                                <div className="flex-1">
                                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mb-6">
                                        <div className="flex items-start justify-between mb-4"><h3 className="text-2xl font-bold text-teal-800 leading-tight">{viewingServiceInModal.nombre}</h3></div>
                                        <div className="flex items-center mb-6 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg w-fit"><svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg><span>Duración estimada: <strong>{viewingServiceInModal.duracion} min</strong></span></div>
                                        <div className="prose prose-teal"><h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Descripción</h4><p className="text-gray-700 text-lg leading-relaxed">{viewingServiceInModal.description || "Servicio especializado de fisioterapia realizado por profesionales."}</p></div>
                                    </div>
                                </div>
                                <div className="mt-auto space-y-3 pt-4">
                                    <button onClick={() => handleServiceSelectConfirmed(viewingServiceInModal)} className="w-full py-4 bg-teal-600 text-white text-lg font-bold rounded-xl shadow-lg shadow-teal-600/20 hover:bg-teal-700 active:transform active:scale-[0.98] transition-all flex items-center justify-center"><span>Sí, Agendar Cita</span><svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg></button>
                                    <button onClick={() => setViewingServiceInModal(null)} className="w-full py-3 bg-white text-gray-600 font-medium rounded-xl border border-gray-200 hover:bg-gray-50 transition-colors">Atrás</button>
                                </div>
                          </div>
                      ) : (
                          <div className="p-4 min-h-full flex flex-col">
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                                  {SERVICES.filter(s => s.precio > 0).map(service => <ServiceCard key={service.id} service={service} onSelect={(s) => setViewingServiceInModal(s)} />)}
                              </div>
                              <div className="mt-auto">
                                <button 
                                    onClick={() => setShowAllServices(false)}
                                    className="w-full py-3 bg-gray-100 text-gray-700 font-medium rounded-xl border border-gray-200 hover:bg-gray-200 transition-colors"
                                >
                                    Volver al Chat
                                </button>
                              </div>
                          </div>
                      )}
                  </div>
              </div>
          </div>
      )}

      {/* Booking Modal */}
      {selectedServiceForBooking && (
          <AppointmentModal 
              service={selectedServiceForBooking}
              onConfirm={handleBookingConfirm}
              onCancel={() => { setSelectedServiceForBooking(null); setReschedulingAppointmentId(null); setReschedulingInitialData(null); }}
              existingAppointments={appointments}
              initialData={reschedulingInitialData}
          />
      )}

      {/* Check Appointment Modal */}
      {showCheckAppointmentModal && (
          <CheckAppointmentModal onSearch={handleCheckAppointmentSearch} onCancel={() => setShowCheckAppointmentModal(false)} />
      )}

      {/* Cancel Confirmation Modal */}
      {appointmentToCancel && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4 backdrop-blur-sm">
              <div className="bg-white rounded-2xl w-full max-w-sm p-6 shadow-2xl animate-fade-in-up text-center">
                  <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">¿Cancelar Cita?</h3>
                  <p className="text-gray-500 mb-6">Esta acción es irreversible. El horario quedará libre para otros pacientes.</p>
                  <div className="flex space-x-3">
                      <button 
                          onClick={() => setAppointmentToCancel(null)}
                          className="flex-1 py-3 bg-gray-100 text-gray-700 font-bold rounded-xl hover:bg-gray-200 transition-colors"
                      >
                          Volver
                      </button>
                      <button 
                          onClick={confirmCancellation}
                          className="flex-1 py-3 bg-red-600 text-white font-bold rounded-xl hover:bg-red-700 shadow-lg shadow-red-600/20 transition-transform active:scale-[0.98]"
                      >
                          Sí, Cancelar
                      </button>
                  </div>
              </div>
          </div>
      )}
    </div>
  );
};

export default App;
