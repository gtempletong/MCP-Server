graph TD
    subgraph "Fuentes Externas"
        A["Fuente 1:\nExcel de Bloomberg"]
        B["Fuente 2:\nFeeds RSS de Noticias"]
    end

    subgraph "Pipelines de Ingesta (Tus Scripts)"
        C["price_ingestion_service"]
        D["news_ingestion_service"]
    end

    subgraph "Base de Conocimiento (La Memoria)"
        E[("Supabase & Pinecone")]
    end

    A -- "Datos Cuantitativos" --> C -- "Guarda en" --> E;
    B -- "Datos Cualitativos" --> D -- "Guarda en" --> E;