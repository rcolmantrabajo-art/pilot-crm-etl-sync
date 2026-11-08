# Pipeline ETL: ClickHouse a PostgreSQL (Pilot CRM)

Script automatizado en Python diseñado para realizar extracciones incrementales de datos desde un entorno de Business Intelligence en ClickHouse hacia una base de datos relacional PostgreSQL, 
implementando una estrategia robusta de carga tipo *Staging* y *UPSERT*.

##  Características Principales
* **Extracción Incremental:** Consulta optimizada basada en ventanas de tiempo (`INTERVAL 30 DAY`) para procesar únicamente registros recientes.
* **Manejo de Staging:** Carga temporal de datos mediante Pandas y SQLAlchemy para garantizar la integridad antes de impactar las tablas finales.
* **UPSERT Dinámico:** Inserción de nuevos registros y actualización automática de modificaciones existentes basadas en la clave primaria (`id`) utilizando `ON CONFLICT`.
* **Seguridad y Buenas Prácticas:** Configuración desacoplada mediante variables de entorno (`.env`) para proteger credenciales y rutas de certificados.

##  Stack Tecnológico
* **Python** (Pandas, ClickHouse Connect, SQLAlchemy, pg8000, python-dotenv)
* **ClickHouse** (Origen de datos analíticos del CRM)
* **PostgreSQL** (Destino y almacenamiento relacional)

##  Configuración y Ejecución

1. Clonar el repositorio e instalar las dependencias necesarias:
