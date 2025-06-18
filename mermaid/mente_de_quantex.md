# Diagrama de Flujo: La Mente de Quantex (Arquitectura de Triage)

Este diagrama detalla el proceso de razonamiento completo que sigue el agente `Quantex` para responder a una pregunta del usuario, implementando una arquitectura de "Triage" para diferenciar entre peticiones estructuradas y no estructuradas.

```mermaid
graph TD
    A["Usuario Pregunta\n'noticias del cobre de hoy'"] --> B{"Fase 1: Deconstruccion y Triage\n(Sub-Agente Reformulador y Planificador)"};
    
    B --> C{"Diagnostico:\nLa pregunta es Estructurada o No Estructurada?"};

    C -- "Estructurada" --> D_PATH;
    C -- "No Estructurada" --> E_PATH;

    subgraph "Camino Estructurado (Busqueda Directa y Validada)"
        D_PATH["Paso A: Validar Entidades en Catalogo\nVerifica si 'cobre' y 'hoy' son validos"];
        D_PATH -- Si, es valido --> D_TOOL["Paso B: Formular Consulta Precisa\nSabe que debe buscar noticias de cobre para la fecha X"];
        D_TOOL --> D_DB["Paso C: Consulta SQL Directa\nVa a Supabase con un WHERE exacto en topic y fecha"];
        D_DB --> F{"Paso D: Recoleccion de Evidencia"};
    end

    subgraph "Camino No Estructurado (Busqueda Semantica)"
        E_PATH["Paso A: Busqueda Conceptual\nEl agente no tiene un filtro exacto"];
        E_PATH --> E_TOOL["Paso B: Ejecuta Herramienta Semantica\nUsa Pinecone para encontrar los IDs de articulos relevantes"];
        E_TOOL --> E_DB["Paso C: Recuperacion de Datos\nUsa los IDs para pedir los articulos a Supabase"];
        E_DB --> F;
    end
    
    F --> G{"Fase Final: Sintesis\n(El Agente Quantex recibe la evidencia)"};
    G --> H["Respuesta Final para el Usuario"];
```

### Explicación de esta Arquitectura

Este flujo representa un agente de IA de última generación:

1.  **Triage Inteligente:** No trata todas las preguntas por igual. Primero, diagnostica la naturaleza de la petición para decidir la ruta más eficiente.
2.  **Ruta Rápida (Estructurada):** Para preguntas directas, valida los datos y va directamente a la base de datos con una consulta precisa, lo que es rápido y fiable.
3.  **Ruta Creativa (No Estructurada):** Para preguntas abiertas, utiliza el poder de la búsqueda semántica (Pinecone) para encontrar conexiones conceptuales y descubrir información relevante que una búsqueda normal no encontraría.

Esta arquitectura dual hace que `Quantex` sea a la vez **eficiente** y **profundamente inteligente**.