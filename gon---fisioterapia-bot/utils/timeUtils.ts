
// Algoritmo para calcular la fecha de Pascua (necesario para festivos móviles)
const getEasterDate = (year: number): Date => {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31) - 1; // 0-indexed
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month, day);
};

// Función auxiliar para mover fecha a lunes (Ley Emiliani)
const moveToMonday = (date: Date): Date => {
  const day = date.getDay();
  if (day === 1) return date; // Ya es lunes
  const diff = 8 - day; // Días hasta el próximo lunes
  const newDate = new Date(date);
  newDate.setDate(date.getDate() + (day === 0 ? 1 : diff)); // Si es domingo (0) +1, sino diff
  return newDate;
};

// Obtener lista de festivos de un año específico
const getColombianHolidays = (year: number): string[] => {
  const holidays: Date[] = [];

  // 1. Festivos fijos (se celebran el día que caen)
  holidays.push(new Date(year, 0, 1));   // Año Nuevo
  holidays.push(new Date(year, 4, 1));   // Día del Trabajo
  holidays.push(new Date(year, 6, 20));  // Independencia
  holidays.push(new Date(year, 7, 7));   // Batalla de Boyacá
  holidays.push(new Date(year, 11, 8));  // Inmaculada Concepción
  holidays.push(new Date(year, 11, 25)); // Navidad

  // 2. Festivos Emiliani (se mueven al lunes siguiente si no caen en lunes)
  holidays.push(moveToMonday(new Date(year, 0, 6)));   // Reyes Magos
  holidays.push(moveToMonday(new Date(year, 2, 19)));  // San José
  holidays.push(moveToMonday(new Date(year, 5, 29)));  // San Pedro y San Pablo
  holidays.push(moveToMonday(new Date(year, 7, 15)));  // Asunción
  holidays.push(moveToMonday(new Date(year, 9, 12)));  // Raza
  holidays.push(moveToMonday(new Date(year, 10, 1)));  // Todos los Santos
  holidays.push(moveToMonday(new Date(year, 10, 11))); // Independencia Cartagena

  // 3. Festivos relacionados con Pascua
  const easter = getEasterDate(year);
  
  // Jueves Santo (Pascua - 3 días)
  const thursdayHoly = new Date(easter); thursdayHoly.setDate(easter.getDate() - 3);
  holidays.push(thursdayHoly);
  
  // Viernes Santo (Pascua - 2 días)
  const fridayHoly = new Date(easter); fridayHoly.setDate(easter.getDate() - 2);
  holidays.push(fridayHoly);
  
  // Ascensión (Pascua + 43 días -> lunes)
  const ascension = new Date(easter); ascension.setDate(easter.getDate() + 39); // Cae en jueves, se mueve a lunes (+43 total)
  holidays.push(moveToMonday(ascension));
  
  // Corpus Christi (Pascua + 64 días -> lunes)
  const corpus = new Date(easter); corpus.setDate(easter.getDate() + 60); // Cae en jueves
  holidays.push(moveToMonday(corpus));
  
  // Sagrado Corazón (Pascua + 71 días -> lunes)
  const sacredHeart = new Date(easter); sacredHeart.setDate(easter.getDate() + 68); // Cae en lunes normalmente (viernes + fin de semana)
  holidays.push(moveToMonday(sacredHeart));

  return holidays.map(d => d.toISOString().split('T')[0]);
};

export const getAvailableDates = (days = 14): Date[] => {
  const dates: Date[] = [];
  const today = new Date();
  let currentDay = new Date(today);
  currentDay.setDate(currentDay.getDate() + 1); // Empezar mañana

  const currentYear = today.getFullYear();
  const nextYear = currentYear + 1;
  
  // Cache holidays strings for quick lookup
  const holidayStrings = new Set([
    ...getColombianHolidays(currentYear),
    ...getColombianHolidays(nextYear)
  ]);

  while (dates.length < days) {
    const dateString = currentDay.toISOString().split('T')[0];
    const dayOfWeek = currentDay.getDay(); // 0 = Domingo

    // Excluir Domingos (0) y Festivos
    if (dayOfWeek !== 0 && !holidayStrings.has(dateString)) {
      dates.push(new Date(currentDay));
    }

    // Avanzar al siguiente día
    currentDay.setDate(currentDay.getDate() + 1);
  }
  
  return dates;
};

export const getAvailableSlots = (date: Date): string[] => {
  // Mock logic: return standard slots
  // Morning: 9-12, Afternoon: 14-19
  return [
    "09:00", "10:00", "11:00",
    "14:00", "15:00", "16:00", "17:00", "18:00"
  ];
};

export const formatDate = (date: Date): string => {
  // Formato corto para los botones (ej: Lun, 24 Nov)
  return date.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' });
};

export const formatDateFull = (dateString: string): string => {
  // Formato largo para confirmación (ej: Lunes, 24 de noviembre de 2025)
  // Agregamos T00:00:00 para evitar problemas de timezone al parsear
  const date = new Date(dateString + 'T00:00:00'); 
  const options: Intl.DateTimeFormatOptions = { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  };
  // Capitalizar primera letra
  const formatted = date.toLocaleDateString('es-CO', options);
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
};
