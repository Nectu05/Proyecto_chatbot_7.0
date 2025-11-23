import React, { useState, useEffect } from 'react';
import { Service, Appointment } from '../types';
import { getAvailableDates, getAvailableSlots, formatDate } from '../utils/timeUtils';

interface AppointmentModalProps {
  service: Service;
  onConfirm: (appointmentData: Omit<Appointment, 'id' | 'status'>) => void;
  onCancel: () => void;
  // New: Receive existing appointments to block slots
  existingAppointments?: Appointment[];
  // New: Pre-fill data for rescheduling
  initialData?: {
    patientName: string;
    patientId: string;
    patientPhone: string;
  };
}

const AppointmentModal: React.FC<AppointmentModalProps> = ({ 
  service, 
  onConfirm, 
  onCancel, 
  existingAppointments = [],
  initialData
}) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    patientName: initialData?.patientName || '',
    patientId: initialData?.patientId || '',
    patientPhone: initialData?.patientPhone || ''
  });

  const dates = getAvailableDates();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedDate && selectedTime && formData.patientName && formData.patientId) {
      onConfirm({
        patientName: formData.patientName,
        patientId: formData.patientId,
        patientPhone: formData.patientPhone,
        serviceId: service.id,
        date: selectedDate.toISOString().split('T')[0],
        time: selectedTime
      });
    }
  };

  // Calculate occupied slots logic
  const getOccupiedSlots = (date: Date): string[] => {
    const dateStr = date.toISOString().split('T')[0];
    return existingAppointments
      .filter(app => app.date === dateStr && app.status === 'confirmed')
      .map(app => app.time);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-md overflow-hidden shadow-2xl animate-fade-in-up">
        <div className="bg-teal-600 p-4 text-white flex justify-between items-center">
          <h2 className="font-semibold">{initialData ? 'Reprogramar Cita' : 'Agendar Cita'}</h2>
          <button onClick={onCancel} className="text-white/80 hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 max-h-[80vh] overflow-y-auto no-scrollbar">
          <div className="mb-4">
            <span className="text-xs font-bold text-teal-600 uppercase tracking-wide">Servicio Seleccionado</span>
            <p className="text-gray-800 font-medium">{service.nombre}</p>
          </div>

          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Elige una fecha</label>
                <div className="flex space-x-2 overflow-x-auto pb-2 no-scrollbar">
                  {dates.map((date, idx) => (
                    <button
                      key={idx}
                      onClick={() => { setSelectedDate(date); setSelectedTime(null); }}
                      className={`flex-shrink-0 px-4 py-2 rounded-lg border text-sm transition-all ${
                        selectedDate?.toDateString() === date.toDateString()
                          ? 'bg-teal-600 text-white border-teal-600 shadow-md'
                          : 'bg-white text-gray-600 border-gray-200 hover:border-teal-300'
                      }`}
                    >
                      <div className="font-bold">{date.getDate()}</div>
                      <div className="text-xs uppercase">{date.toLocaleDateString('es-CO', { weekday: 'short' })}</div>
                    </button>
                  ))}
                </div>
              </div>

              {selectedDate && (
                <div className="animate-fade-in">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Elige una hora</label>
                  <div className="grid grid-cols-4 gap-2">
                    {getAvailableSlots(selectedDate).map((slot) => {
                      const isOccupied = getOccupiedSlots(selectedDate).includes(slot);
                      return (
                        <button
                          key={slot}
                          disabled={isOccupied}
                          onClick={() => setSelectedTime(slot)}
                          className={`py-2 text-sm rounded-md border transition-all ${
                            isOccupied
                              ? 'bg-red-50 text-gray-300 border-gray-100 cursor-not-allowed decoration-slice'
                              : selectedTime === slot
                                ? 'bg-teal-100 text-teal-800 border-teal-300 font-semibold'
                                : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                          }`}
                        >
                          {slot}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-xs text-gray-400 mt-1 text-right">* Horas en rojo están ocupadas</p>
                </div>
              )}

              <div className="flex space-x-3 pt-2">
                  <button 
                    onClick={onCancel}
                    className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-xl font-medium hover:bg-gray-200"
                  >
                    Atrás
                  </button>
                  <button 
                    onClick={() => setStep(2)}
                    disabled={!selectedDate || !selectedTime}
                    className="flex-1 bg-teal-600 text-white py-3 rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-teal-700 transition-colors"
                  >
                    Continuar
                  </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <form onSubmit={handleSubmit} className="space-y-4 animate-fade-in">
               <div className="bg-blue-50 p-3 rounded-lg text-sm text-blue-800 mb-4">
                Nueva cita para el <strong>{selectedDate && formatDate(selectedDate)}</strong> a las <strong>{selectedTime}</strong>.
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Nombre Completo</label>
                <input 
                  type="text" 
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-teal-500 focus:border-teal-500 outline-none"
                  value={formData.patientName}
                  onChange={e => setFormData({...formData, patientName: e.target.value})}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Cédula</label>
                <input 
                  type="text" 
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-teal-500 focus:border-teal-500 outline-none"
                  value={formData.patientId}
                  onChange={e => setFormData({...formData, patientId: e.target.value})}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Celular</label>
                <input 
                  type="tel" 
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-teal-500 focus:border-teal-500 outline-none"
                  value={formData.patientPhone}
                  onChange={e => setFormData({...formData, patientPhone: e.target.value})}
                />
              </div>

              <div className="flex space-x-3 pt-4">
                 <button 
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-xl font-medium hover:bg-gray-200"
                >
                  Atrás
                </button>
                <button 
                  type="submit"
                  className="flex-1 bg-teal-600 text-white py-3 rounded-xl font-medium hover:bg-teal-700 shadow-lg shadow-teal-600/30"
                >
                  Confirmar {initialData ? 'Cambio' : 'Cita'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default AppointmentModal;