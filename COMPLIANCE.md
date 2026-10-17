# ⚖️ Declaración de Cumplimiento Legal y Términos de Servicio (Compliance)

El diseño de **Radar de Contenido 30X** fue concebido bajo el principio rector de **cumplimiento estricto de las directrices del hackathon y la legislación aplicable**.

---

## 1. Principios de Cumplimiento

1. **Exclusivamente Contenido Público:**
   - No se accede a cuentas privadas, grupos cerrados, mensajes directos ni datos protegidos por autenticación.
   - Solo se procesan publicaciones, artículos, repositorios y videos abiertos al público en internet.

2. **Cero Violaciones de Términos de Servicio (ToS):**
   - **No al scraping con login:** Radar30X **no** realiza scraping de LinkedIn, Instagram ni TikTok mediante sesiones automatizadas o elusión de mecanismos anti-bot.
   - **No al scraping de endpoints internos:** No se utiliza `pytrends` ni peticiones a endpoints no documentados o privados de Google.
   - **Solo APIs Oficiales y Feeds RSS/Atom Estándar:** Hacker News (Algolia), YouTube (Data API v3), Google News (RSS estándar), Medium (RSS público) y GitHub (Search API).

3. **Sin Tratamiento de Datos Personales Sensibles:**
   - No se extraen correos electrónicos, números telefónicos, direcciones IP ni perfiles personales de usuarios.
   - Los nombres de autor y canales se almacenan únicamente con fines de **atribución de autoría** exigida por licencias de contenido público y estándares de prensa.

---

## 2. Estrategia Compliant para LinkedIn, Instagram y TikTok

Dado que las APIs públicas de lectura masiva de LinkedIn y Meta están restringidas para terceros sin acuerdos corporativos o requieren credenciales privadas, Radar30X resuelve la cobertura mediante tres mecanismos 100% legales:

### A. Captura Manual Asistida ("La Comunidad y el Equipo como Sensor")
El equipo editorial de 30X observa las redes de manera natural y humana (como parte de su trabajo diario) y registra enlaces y métricas públicas en `data/manual.csv`. El pipeline procesa estos datos con los mismos estándares que las fuentes automatizadas, integrándolos al motor de decisiones de Jev.

### B. Proxy Semántico del Web Abierto
Los temas de mayor impacto en redes profesionales no nacen de forma aislada: se discuten previamente en Hacker News, GitHub, artículos de Medium o publicaciones de noticias especializadas. Al detectar la aceleración en el web abierto, el radar **anticipa con días de ventaja** el contenido que despegará en LinkedIn e Instagram.

### C. Hoja de Ruta para Producción Comercial
Para la evolución comercial posterior al hackathon:
- Integración de las APIs oficiales de Meta Graph y LinkedIn Marketing para las cuentas y páginas oficiales de 30X.
- Reddit Data API bajo el tier comercial oficial ($0.24 por cada 1.000 llamadas).
