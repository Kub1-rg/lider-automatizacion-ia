# Respuestas conceptuales

Cada respuesta tiene como máximo ocho líneas y busca contestar de forma directa.

1. Consultaría precios/stock vigentes y pasaría esos datos al modelo.  
   Limitaría el contexto, pediría aclaración y validaría antes de responder.  
   No confirmaría entregas ni permitiría cambios. Mediría y revisaría errores.

2. RAG (generación aumentada por recuperación) entrega fragmentos pertinentes como contexto.  
   Lo usaría con contenido amplio o cambiante.  
   Para doce productos, consultaría el catálogo directamente.

3. Function calling permite proponer una herramienta estructurada.  
   `consultar_solicitud(id)` podría llamar `GET /solicitudes/{id}`.  
   La aplicación autentica y verifica propiedad antes de ejecutarla.  
   El modelo propone; la aplicación autoriza y devuelve contexto.

4. Un chatbot responde; un agente también usa herramientas.  
   Por ejemplo, un agente consulta catálogo y crea una solicitud tras validar los datos.  
   Pediría confirmación cuando la acción lo requiera.  
   La API aplica permisos y reglas de negocio.

5. Mediría tokens y calidad; limitaría mensaje, contexto, salida y reintentos.  
   Aplicaría cuotas, deduplicación y caché solo si los datos no cambian.  
   Elegiría según calidad y costo medidos.  
   Proyectaría 5.000 solicitudes con consumo y precios vigentes.
