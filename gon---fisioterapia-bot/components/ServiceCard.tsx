import React from 'react';
import { Service } from '../types';

interface ServiceCardProps {
  service: Service;
  onSelect: (service: Service) => void;
  compact?: boolean;
}

const ServiceCard: React.FC<ServiceCardProps> = ({ service, onSelect, compact = false }) => {
  return (
    <div 
      className={`bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col justify-between group overflow-hidden ${compact ? 'p-3' : 'p-4'}`}
      onClick={() => onSelect(service)}
    >
      <div>
        <div className="flex justify-between items-start mb-2">
            <h3 className={`font-semibold text-gray-800 group-hover:text-teal-600 transition-colors ${compact ? 'text-sm' : 'text-base'}`}>
            {service.nombre}
            </h3>
            {service.duracion > 0 && (
                 <div className="flex items-center text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded-lg whitespace-nowrap ml-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {service.duracion} min
                </div>
            )}
        </div>
        
        {service.description && (
            <p className={`text-gray-500 leading-snug ${compact ? 'text-xs line-clamp-2' : 'text-sm'}`}>
                {service.description}
            </p>
        )}
      </div>
      
      <div className="mt-3 pt-2 border-t border-gray-50 flex justify-end">
        <span className={`text-teal-700 font-medium flex items-center ${compact ? 'text-xs' : 'text-sm'}`}>
          Agendar
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </span>
      </div>
    </div>
  );
};

export default ServiceCard;