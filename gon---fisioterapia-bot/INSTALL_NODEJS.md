# Guía de Instalación de Node.js y Dependencias

## 📦 Paso 1: Instalar Node.js

### Descargar Node.js
1. Visita: https://nodejs.org/
2. Descarga la versión **LTS** (Long Term Support) - Recomendada
3. Ejecuta el instalador descargado
4. Durante la instalación:
   - ✅ Acepta la licencia
   - ✅ Mantén la ruta de instalación por defecto
   - ✅ **IMPORTANTE:** Marca la opción "Automatically install the necessary tools"
   - ✅ Completa la instalación

### Verificar la instalación
Abre una **nueva** terminal PowerShell y ejecuta:
```powershell
node --version
npm --version
```

Deberías ver algo como:
```
v20.x.x
10.x.x
```

---

## 📦 Paso 2: Instalar Dependencias del Proyecto Web

Una vez que Node.js esté instalado:

```powershell
# Navegar a la carpeta del proyecto web
cd C:\Users\Casa\Downloads\Chatbot_fisioterapia_7.0\gon---fisioterapia-bot

# Instalar TODAS las dependencias (incluyendo @types/node)
npm install
```

Esto instalará:
- `@types/node` (tipos de TypeScript para Node.js)
- React
- TypeScript
- Vite
- Y todas las demás dependencias listadas en `package.json`

---

## ✅ Paso 3: Verificar que el error desapareció

Después de ejecutar `npm install`:
1. Cierra y vuelve a abrir el archivo `tsconfig.json` en el IDE
2. El error debería haber desaparecido

---

## 🚀 Bonus: Comandos útiles del proyecto web

Una vez instaladas las dependencias, podrás usar:

```powershell
# Ejecutar el servidor de desarrollo
npm run dev

# Compilar para producción
npm run build

# Vista previa de la compilación
npm run preview
```

---

## ❓ Si algo sale mal

**Si Node.js no se instala correctamente:**
- Reinicia tu computadora después de la instalación
- Verifica que Node.js esté en el PATH del sistema
- Intenta abrir PowerShell como Administrador

**Si npm install falla:**
- Verifica tu conexión a internet
- Ejecuta: `npm cache clean --force`
- Intenta de nuevo: `npm install`

---

## 📝 Resumen

1. ✅ Restauré la línea en `tsconfig.json` (ahora está correcta)
2. ⏳ Instala Node.js desde https://nodejs.org/
3. ⏳ Ejecuta `npm install` en la carpeta del proyecto web
4. ✅ El error del IDE desaparecerá

**Siguiente paso:** Instala Node.js y luego avísame para continuar con `npm install`.
