# Arquitectura Completa del Ecosistema Quantex

Este diagrama representa el flujo completo de datos y razonamiento del sistema `Quantex`, desde las fuentes de datos externas hasta la respuesta final entregada al usuario.

La arquitectura se basa en un modelo de agentes y sub-agentes modulares, donde cada componente tiene una responsabilidad única y bien definida.

```mermaid
graph TD
    subgraph "A. Fuentes de Datos Externas"
        A1["Fuente 1:\nExcel de Bloomberg"]
        A2["Fuente 2:\nFeeds RSS de Noticias"]
    end

    subgraph "B. Pipelines de Ingesta (Los Sentidos)"
        B1["price_ingestion_service"] -- Lee --> A1
        B2["news_ingestion_service"] -- Lee --> A2
        B1 --> B_OUT_1["Datos Cuantitativos"]
        B2 --> B_OUT_2["Datos Cualitativos (Resumenes + Vectores)"]
    end

    subgraph "C. Base de Conocimiento (La Memoria)"
        C1[("Supabase\n(Almacen de Hechos)\n- time_series_data\n- news_articles")]
        C2[("Pinecone\n(Indice de Significados)\n- Vectores de noticias")]
        B_OUT_1 -- "Guarda en" --> C1
        B_OUT_2 -- "Guarda en" --> C1
        B_OUT_2 -- "Indexa en" --> C2
    end
    
    subgraph "D. Aplicacion Principal: Quantex"
        D0(Usuario) <--> D1{app.py - El Orquestador}
    end

    subgraph "E. Mente del Agente (El Proceso de Razonamiento)"
        D1 -- "1. Recibe Pregunta" --> D_REFORMULATOR{"Sub-Agente Reformulador"};
        D_REFORMULATOR -- "Lee\nprompt_reformulator.txt" --> P1(("Prompt\nReformulador"));
        D_REFORMULATOR -- "2. Devuelve Consulta Limpia" --> D_PLANNER{"Sub-Agente Planificador"};

        D_PLANNER -- "Lee\nprompt_jefe_de_herramientas.txt" --> P2(("Prompt\nPlanificador"));
        D_PLANNER -- "3. Devuelve Plan de Accion" --> D1;
        
        D1 -- "4. Ejecuta Herramientas" --> D_TOOLS[Herramientas: get_news, etc.];
        D_TOOLS -- "5. Busca en Memoria" --> C1;
        D_TOOLS -- "y/o en" --> C2;
        C1 & C2 -- "6. Devuelven Evidencia" --> D_TOOLS;
        D_TOOLS -- "7. Entrega Evidencia" --> D1;

        D1 -- "8. Pide Sintesis" --> D_SYNTH{Agente Sintetizador};
        D_SYNTH -- "Lee\nprompt_quantex.txt" --> P3(("Prompt\nQuantex"));
        D_SYNTH -- "9. Devuelve Respuesta Final" --> D1;
    end
```
### Explicación de los Componentes
* **A. Fuentes de Datos:** Origen de la información cruda.
* **B. Pipelines de Ingesta:** Servicios automáticos que procesan y preparan los datos.
* **C. Base de Conocimiento:** La memoria dual del sistema, separando hechos (Supabase) de significados (Pinecone).
* **D. Aplicación Principal:** El punto de entrada y el orquestador que dirige todo el proceso.
* **E. Mente del Agente:** El flujo de razonamiento interno, mostrando la cadena de mando desde que se recibe una pregunta hasta que se genera una respuesta, pasando por la reformulación, la planificación, la ejecución de herramientas y la síntesis final.