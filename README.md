# Bot Gasolineras

Bot publico de Telegram para monitorizar bajadas de precio del combustible en gasolineras de Espana usando el dataset oficial de `EstacionesTerrestres`.

[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/avisadorgasolina_bot)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/mikolatero/botGasolineras)



## 1. Arquitectura

El sistema se divide en dos procesos:

- `bot`: expone la UX de Telegram con `aiogram`, busca siempre contra MySQL y gestiona watchlists.
- `worker`: ejecuta un job periodico con `APScheduler`, descarga el dataset completo, actualiza la base local, detecta bajadas y envia notificaciones pendientes.

Flujo principal:

1. El `worker` descarga el JSON oficial completo con `Accept: text/json`.
2. Parsea y normaliza estaciones y precios.
3. Hace upsert masivo en MySQL.
4. Compara `station_prices_current` con el nuevo snapshot.
5. Inserta cambios en `station_price_history`.
6. Crea notificaciones `pending` solo para bajadas y solo para watchlists activas.
7. Envia mensajes de Telegram y marca cada notificacion como `sent` o `failed`.

Las busquedas del bot nunca van a la API oficial. Siempre usan la base local, por lo que el bot sigue funcionando aunque la API falle temporalmente.

## 2. Analisis JSON real

Fuente oficial:

- Endpoint: [EstacionesTerrestres](https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/)
- Referencia oficial del contrato JSON: [help/operations/PreciosEESSTerrestres](https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/help/operations/PreciosEESSTerrestres)

Estructura raiz observada en la documentacion oficial:

- `Fecha`
- `ListaEESSPrecio`
- `Nota`
- `ResultadoConsulta`

Campos relevantes por estacion en `ListaEESSPrecio`:

- `IDEESS`
- `C.P.`
- `Dirección`
- `Horario`
- `Latitud`
- `Localidad`
- `Longitud_x0020__x0028_WGS84_x0029_`
- `Margen`
- `Municipio`
- `Provincia`
- `Remisión`
- `Rótulo`
- `Tipo_x0020_Venta`
- `IDMunicipio`
- `IDProvincia`
- `IDCCAA`
- multiples columnas `Precio_x0020_*`

Mapping aplicado en el proyecto:

- `IDEESS` -> `stations.ideess` como clave estable de estacion
- `Dirección` -> `stations.address`
- `C.P.` -> `stations.postal_code` como valor oficial bruto
- `Latitud` + `Longitud_x0020__x0028_WGS84_x0029_` -> `stations.postal_code_resolved` usando reverse geocoding de CartoCiudad cuando esta disponible
- `Municipio` -> `stations.municipality`
- `Provincia` -> `stations.province`
- `Localidad` -> `stations.locality`
- `Rótulo` -> `stations.brand`
- `Horario` -> `stations.schedule`
- `Latitud` -> `stations.latitude`
- `Longitud_x0020__x0028_WGS84_x0029_` -> `stations.longitude`
- `Precio_x0020_*` -> catalogo `fuels` + snapshot actual en `station_prices_current`

Normalizacion y limpieza:

- Los precios llegan con coma decimal, por ejemplo `1,459`; se convierten a `Decimal(10,3)`.
- Valores vacios, cero, no numericos o invalidos se ignoran.
- Coordenadas con coma decimal se convierten a `Numeric(10,7)`.
- Los textos se guardan en version original y version normalizada sin acentos para filtrar rapido.
- El bot usa como CP efectivo `stations.postal_code_resolved` y si no existe cae a `stations.postal_code`.
- Los filtros por CP aceptan tanto el CP oficial como el resuelto por coordenadas para no perder estaciones en limites postales muy pegados.

## 3. Modelo de base de datos

Motor obligatorio elegido: MySQL 8+ con `SQLAlchemy ORM` y migraciones `Alembic`.

Tablas:

- `users`: usuarios Telegram.
- `stations`: estaciones normalizadas por `IDEESS`.
- `fuels`: catalogo limpio y estable de combustibles soportados.
- `station_prices_current`: ultimo precio conocido por estacion y combustible.
- `station_price_history`: historico de cambios detectados.
- `user_watchlists`: suscripciones usuario + estacion + combustible.
- `notifications_sent`: cola idempotente de notificaciones y trazabilidad de envio.
- `sync_runs`: auditoria de cada sincronizacion.

Indices clave:

- `stations`: indices por `postal_code`, `postal_code_resolved`, `municipality_normalized`, `province_normalized`, `brand_normalized`, `locality_normalized`, `address_normalized`.
- `stations`: `FULLTEXT` MySQL en `brand`, `address`, `municipality`, `locality`.
- `station_prices_current`: indice compuesto unico `(station_id, fuel_id)`.
- `user_watchlists`: indice compuesto unico `(user_id, station_id, fuel_id)`.
- `notifications_sent`: unico `(watchlist_id, sync_run_id)`.

## 4. Estructura del proyecto

```text
app/
  bot/
  config/
  integrations/
  models/
  repositories/
  scheduler/
  services/
  utils/
tests/
alembic/
Dockerfile
docker-compose.yml
.env.example
README.md
```

## 5. Codigo completo

El repositorio ya contiene codigo real y ejecutable para:

- cliente HTTP con retries y timeout
- sincronizacion completa del dataset oficial
- upserts y persistencia en MySQL
- deteccion de bajadas
- cola idempotente de notificaciones
- bot `aiogram` con `/start`, `/help`, `/buscar`, `/mis_seguimientos`, `/eliminar`, `/pausar`, `/reanudar`
- filtros por CP, provincia, municipio, localidad, marca, direccion y combustible
- paginacion e inline keyboards
- scheduler con `APScheduler`
- `Dockerfile`, `docker-compose.yml`, Alembic y tests

Entrypoints:

- `python -m app.run_bot`
- `python -m app.run_worker`
- `python -m app.run_postal_code_backfill`

## 6. Instalacion local

### Opcion A: Docker

1. Copia `.env.example` a `.env` y rellena `TELEGRAM_BOT_TOKEN`.
2. Levanta la pila:

```bash
docker compose up --build
```

Servicios:

- `mysql`
- `migrator`
- `bot`
- `worker`

### Opcion B: entorno local

1. Crea entorno virtual.
2. Instala el paquete:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

3. Configura `.env`.
4. Ejecuta migraciones:

```bash
alembic upgrade head
```

5. Lanza procesos:

```bash
python -m app.run_bot
python -m app.run_worker
```

## 7. Variables de entorno

Variables principales:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `MINETUR_API_URL`
- `MINETUR_API_TIMEOUT_SECONDS`
- `MINETUR_API_RETRIES` (por defecto `6`)
- `MINETUR_API_ENABLE_CURL_FALLBACK` (por defecto `true`)
- `POSTAL_CODE_GEOCODER_ENABLED`
- `POSTAL_CODE_GEOCODER_URL`
- `POSTAL_CODE_GEOCODER_TIMEOUT_SECONDS`
- `POSTAL_CODE_GEOCODER_BATCH_SIZE`
- `POSTAL_CODE_GEOCODER_CONCURRENCY`
- `SYNC_INTERVAL_MINUTES`
- `RUN_SYNC_ON_STARTUP`
- `SEARCH_RESULT_PAGE_SIZE`
- `WATCHLIST_PAGE_SIZE`
- `RATE_LIMIT_WINDOW_SECONDS`
- `RATE_LIMIT_MAX_EVENTS`
- `TIMEZONE`
- `OUTBOUND_HTTP_TRUST_ENV` (por defecto `false`)
- `OUTBOUND_HTTP_CA_BUNDLE` (en Docker se fija a `/etc/ssl/certs/ca-certificates.crt`)

## 8. Scheduler

`APScheduler` ejecuta un job cada `SYNC_INTERVAL_MINUTES`:

- descarga dataset completo
- actualiza estaciones
- actualiza precios actuales
- registra historico
- detecta bajadas
- genera notificaciones pendientes
- envia notificaciones por Telegram

No se consulta la API por cada busqueda. Solo se hace sync completo.

## 8.1 Backfill manual de codigos postales

Para refrescar los codigos postales resueltos sin mezclarlo con la sync de precios existe un comando dedicado:

```bash
python -m app.run_postal_code_backfill --reset-all --delay-seconds 2 --max-batches 0
```

Notas:

- `--reset-all` reabre toda la cola de estaciones activas con coordenadas.
- `--clear-resolved` borra tambien `postal_code_resolved` antes del refresco; normalmente no hace falta.
- `--delay-seconds` mete una pausa entre lotes para no cargar el geocoder.
- `--max-batches 0` significa procesar hasta vaciar la cola.
- Recomendacion practica: ejecutar este comando con el `worker` parado o con `POSTAL_CODE_GEOCODER_ENABLED=false` en el `worker` habitual, para evitar lookups duplicados mientras dura el backfill.

## 9. Notificaciones

Formato enviado:

```text
⛽ Ha bajado el precio!
📍 Repsol — Av. X, Murcia
🛢 Gasoleo A
💸 Antes: 1.489 €/L
💚 Ahora: 1.459 €/L
📉 -0.030 €/L
🕒 25/03/2026 12:30
```

## 10. Migraciones

Aplicar:

```bash
alembic upgrade head
```

Crear una nueva:

```bash
alembic revision -m "describe-change"
```

## 11. Despliegue en VPS

Recomendacion simple:

1. Instala Docker y Docker Compose.
2. Clona el repositorio.
3. Crea `.env`.
4. Ejecuta `docker compose up -d --build`.
5. Configura reinicio automatico con `unless-stopped`.
6. Haz backup de MySQL y del `.env`.
7. Monitoriza logs con `docker compose logs -f bot worker`.

## 12. Tests

Ejecutar:

```bash
pytest
```

Cobertura incluida:

- parseo de precios
- deteccion de bajadas
- no duplicados
- busqueda
- watchlists

## 13. Decisiones justificadas

### MySQL vs SQLite

MySQL 8 es mejor aqui porque:

- soporta concurrencia real para bot + worker
- ofrece indices y `FULLTEXT` mas utiles para busqueda
- aguanta mejor crecimiento de historico y notificaciones
- es la opcion pedida para produccion

SQLite sirve bien para tests, pero no como motor principal de este caso multi-proceso.

### IDEESS como clave

`IDEESS` es el identificador estable publicado por la fuente oficial. Usarlo como clave de estacion evita duplicados artificiales y simplifica el sync completo.

### Estrategia de sync completo

Se descarga siempre el dataset completo porque:

- la fuente se actualiza por lotes
- todas las busquedas deben resolverse localmente
- permite seguir operando si la API cae entre sincronizaciones
- simplifica comparacion de snapshots e historico

### Como se evitan duplicados

- una watchlist es unica por `user + station + fuel`
- una notificacion es unica por `watchlist + sync_run`
- si el precio no cambia, no se genera historico ni notificacion
- el envio marca cada notificacion y hace commit por mensaje

### Escalabilidad

Si el volumen crece:

- separar `bot` y `worker` ya permite escalar horizontalmente
- se pueden particionar historicos por fecha
- se puede mover la cola de notificaciones a un broker externo
- se puede afinar `FULLTEXT` o buscador dedicado si aumenta mucho el trafico de busqueda
