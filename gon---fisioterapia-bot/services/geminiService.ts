import { GoogleGenAI, Type } from "@google/genai";
import { SYSTEM_INSTRUCTION } from "../constants";
import { GeminiResponseSchema } from "../types";

// Initialize Gemini Client
// Note: Ensure process.env.API_KEY is set in your environment
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const responseSchema = {
  type: Type.OBJECT,
  properties: {
    message: { type: Type.STRING },
    intent: { 
      type: Type.STRING, 
      enum: ['greeting', 'symptom_analysis', 'show_all_services', 'booking_request', 'cancellation', 'price_inquiry', 'general', 'invoice_analysis', 'check_appointment', 'revenue_report', 'reschedule'] 
    },
    suggestedServiceIds: {
      type: Type.ARRAY,
      items: { type: Type.INTEGER }
    },
    extractedInvoiceData: {
      type: Type.OBJECT,
      properties: {
        amount: { type: Type.NUMBER },
        date: { type: Type.STRING }
      }
    }
  },
  required: ['message', 'intent'],
  propertyOrdering: ['message', 'intent', 'suggestedServiceIds', 'extractedInvoiceData']
};

export const sendMessageToGemini = async (
  history: { role: string; parts: { text: string }[] }[],
  textMessage: string,
  imageBase64?: string
): Promise<GeminiResponseSchema> => {
  try {
    // Use gemini-2.5-flash for both text and multimodal tasks to ensure JSON schema support.
    const modelId = 'gemini-2.5-flash';

    // Calculate current date info to inject into context
    const now = new Date();
    const dayName = now.toLocaleDateString('es-CO', { weekday: 'long' });
    const dateString = now.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
    
    const contextInstruction = `
      ${SYSTEM_INSTRUCTION}
      
      CONTEXTO TEMPORAL OBLIGATORIO:
      - HOY es: ${dayName.toUpperCase()}, ${dateString}.
      - Si el usuario dice "mañana", se refiere al día siguiente a ${dayName}.
      - REGLA DE ORO: Agendar para "mañana" ESTÁ PERMITIDO. Solo está prohibido agendar para "hoy" (${dayName}).
    `;

    const parts: any[] = [];
    if (imageBase64) {
        const cleanBase64 = imageBase64.split(',')[1] || imageBase64;
        parts.push({
            inlineData: {
                mimeType: 'image/jpeg',
                data: cleanBase64
            }
        });
        parts.push({ text: "Analiza esta imagen. Si es una factura médica, extrae el monto total y la fecha." });
    }
    
    if (textMessage) {
        parts.push({ text: textMessage });
    }
    
    const response = await ai.models.generateContent({
      model: modelId,
      contents: {
        parts: parts
      },
      config: {
        systemInstruction: contextInstruction,
        responseMimeType: "application/json",
        responseSchema: responseSchema,
        temperature: 0.2, // Lower temperature for stricter rule adherence
      }
    });

    if (response.text) {
      return JSON.parse(response.text) as GeminiResponseSchema;
    } else {
      throw new Error("No response text from Gemini");
    }

  } catch (error) {
    console.error("Gemini API Error:", error);
    return {
      message: "Lo siento, tuve un problema técnico momentáneo. ¿Podrías intentarlo de nuevo?",
      intent: 'general'
    };
  }
};