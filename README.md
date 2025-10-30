## Desarrollo local

### Requisitos

- Docker y Docker Compose
- Python 3.12 (si vas a ejecutar la app localmente)

### Base de datos

Si solo necesitás la base para pruebas puntuales, podés levantarla en segundo plano:

```bash
docker compose up -d postgres
```

La instancia expone `localhost:5432` con credenciales `postgres/postgres`, base `nodo_documentos`.  
La app ya apunta a ese DSN por defecto (`postgresql+asyncpg://postgres:postgres@localhost:5432/nodo_documentos`), por lo que no se necesita configuración extra.  
Para detenerla usá `docker compose down`.

### Aplicación (API + DB con Docker Compose)

1. Construir la imagen y levantar ambos servicios (pensado para entornos productivos o staging):

   ```bash
   docker compose up --build -d
   ```

   - El servicio `api` se expone en `localhost:8000` y usa la imagen ya construida (sin hot-reload).  
     Después de cambios en el código hay que volver a ejecutar `docker compose up --build`.
   - El servicio `postgres` queda accesible para la app mediante `postgresql+asyncpg://postgres:postgres@postgres:5432/nodo_documentos`.

2. Logs:

   ```bash
   docker compose logs -f api
   ```

3. Documentación interactiva: `http://localhost:8000/api/docs`.

4. Para detener todo:

   ```bash
   docker compose down
   ```

Si necesitás parámetros personalizados (por ejemplo otra URL de base), podés definir `ASYNC_DATABASE_URL` en tu entorno o en un archivo `.env`.

### Almacenamiento S3

La app genera un `presigned URL` para que el front-end suba los binarios directamente al bucket.
Configurá estas variables antes de exponer el nuevo endpoint:

- `S3_BUCKET_NAME`: bucket donde vivirán los documentos (obligatoria).
- `S3_REGION_NAME`: región de AWS o MinIO (por defecto `us-east-1`).
- `S3_ENDPOINT_URL`: opcional si usás un endpoint custom (p. ej. LocalStack).
- `S3_PRESIGNED_EXPIRATION_SECONDS`: TTL en segundos del URL generado (default `900`).

El endpoint `POST /api/documents/upload-url` recibe `clinic_id`, `file_name` (y opcionalmente `content_type`) y devuelve tanto el `upload_url` como el `s3_url` que luego debe usarse en `POST /api/documents`. Cada archivo queda almacenado bajo `bucket/<clinic_id>/<uuid>/<archivo>`.

### Autenticación por API Key

Podés exigir que todos los requests incluyan un header `X-API-Key` configurando las siguientes variables:

- `API_KEY`: valor secreto obligatorio para los clientes.
- `API_HEADER_NAME`: opcional, si querés usar otro nombre de header (por defecto `x-api-key`).

Cuando el valor está presente el middleware rechaza cualquier request sin el header correcto devolviendo `401`.
