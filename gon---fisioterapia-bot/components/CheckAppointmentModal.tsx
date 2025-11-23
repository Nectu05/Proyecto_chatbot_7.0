import React, { useState } from 'react';

interface CheckAppointmentModalProps {
  onSearch: (patientId: string) => void;
  onCancel: () => void;
}

const CheckAppointmentModal: React.FC<CheckAppointmentModalProps> = ({ onSearch, onCancel }) => {
  const [idInput, setIdInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (idInput.trim()) {
      onSearch(idInput.trim());
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl animate-fade-in-up">
        <div className="bg-teal-700 p-4 text-white flex justify-between items-center">
          <h2 className="font-semibold text-lg">Verificación requerida</h2>
          <button onClick={onCancel} className="text-white/80 hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <p className="text-gray-600 text-sm mb-4">
            Por seguridad, para consultar o cancelar citas, ingresa el número de documento (cédula) del paciente.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="mb-6">
              <label className="block text-sm font-bold text-gray-700 mb-2">
                Número de Cédula
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0c0 .884-.356 1.763-1 2.438a4.492 4.492 0 01-1.763 1H5" />
                  </svg>
                </div>
                <input 
                  type="text" 
                  required
                  autoFocus
                  className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-xl focus:ring-teal-500 focus:border-teal-500 outline-none transition-shadow shadow-sm"
                  placeholder="Ej: 1061700..."
                  value={idInput}
                  onChange={(e) => setIdInput(e.target.value)}
                />
              </div>
            </div>

            <div className="flex space-x-3">
                <button 
                  type="button"
                  onClick={onCancel}
                  className="flex-1 bg-gray-100 text-gray-700 py-3 rounded-xl font-bold hover:bg-gray-200 transition-colors"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="flex-1 bg-teal-600 text-white py-3 rounded-xl font-bold shadow-lg shadow-teal-600/20 hover:bg-teal-700 transition-all active:scale-[0.98]"
                >
                  Buscar
                </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CheckAppointmentModal;