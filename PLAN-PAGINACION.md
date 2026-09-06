# Plan: paginación con `--all`

## Objetivo

Añadir `--all` a los informes históricos de la CLI para poder descargar un
informe completo en varias peticiones. El comando debe entregar el informe
completo o devolver un error; no debe terminar correctamente con un resultado
parcial conocido.

## Comportamiento previsto

Sin `--all`, los comandos mantienen su comportamiento actual:

```bash
ga4 pages --property 123456789 --limit 25
```

Con `--all`, se recorren páginas de 10.000 filas hasta completar el informe:

```bash
ga4 pages --property 123456789 --all --format csv
```

La primera versión tendrá estos límites internos:

- Máximo de 100.000 filas por descarga.
- Máximo de 20 peticiones.
- `--all` y `--limit` serán incompatibles.
- Si se alcanza un límite sin completar el informe, se explica el motivo por
  stderr, se devuelve el código de salida `3` y no se imprime un informe
  parcial.

## Implementación

### `src/ga4_toolkit/client.py`

Modificar `AnalyticsClient.run_report()` y extraer la construcción de la
consulta para poder reutilizarla en cada página.

- Añadir `fetch_all=False` a `run_report()`.
- En cada petición enviar `offset` y `limit`.
- Avanzar según las filas realmente recibidas.
- Parar cuando el número acumulado alcance el `rowCount` declarado por Google.
- Detectar una página vacía antes de completar el informe.
- Detectar cambios inesperados en `rowCount`.
- Propagar errores de API sin imprimir el resultado acumulado como si estuviera
  completo.
- Mantener una propiedad, rango de fechas, filtros y orden idénticos en todas
  las peticiones.
- Para informes paginados, el orden debe ser estable. Mantener la ordenación
  principal y añadir las dimensiones como criterios de desempate cuando sea
  necesario.

La respuesta final debe conservar los campos actuales y reflejar la descarga:

```json
{
  "row_count": 23500,
  "returned_row_count": 23500,
  "truncated": false,
  "pagination": {
    "pages_fetched": 3,
    "next_offset": null,
    "stop_reason": "complete"
  }
}
```

No se deben sumar los `rowCount` de las páginas: cada respuesta describe el
mismo informe completo. La paginación concatena filas.

### `src/ga4_toolkit/cli.py`

- Añadir `--all` a `overview`, `pages`, `acquisition`, `events` y `report`.
- Añadir `--max-rows` sólo si resulta necesario para hacer visible el límite;
  de lo contrario mantenerlo como constante interna en esta primera versión.
- Rechazar `--all` junto con `--limit`.
- Imprimir el resultado sólo después de completar todas las páginas.
- Reservar el código de salida `3` para una descarga incompleta por límite o
  inconsistencia de paginación.

### `src/ga4_toolkit/presets.py`

Pasar `fetch_all=True` desde los comandos de resumen, páginas, adquisición y
eventos. Realtime queda fuera porque `runRealtimeReport` no ofrece `offset`.

### `src/ga4_toolkit/mcp_server.py`

Queda fuera de esta iteración. MCP seguirá devolviendo páginas explícitas para
mantener el tamaño de contexto controlado. Podrá añadirse más adelante con
`offset` y `next_offset`.

## Pruebas

Añadir pruebas sin credenciales que cubran:

- Informe vacío.
- Una sola página.
- Varias páginas concatenadas sin saltos ni duplicados.
- Última página corta.
- Límite de 100.000 filas o 20 peticiones alcanzado.
- `--all` combinado con `--limit`.
- Página vacía inesperada.
- Cambio de `rowCount` entre respuestas.
- Error de API a mitad de la descarga.
- Ausencia de salida parcial cuando falla la descarga.
- CSV con una sola cabecera.
- JSON válido.
- Comportamiento actual conservado cuando no se usa `--all`.

## Documentación y publicación

- Actualizar `README.md` con ejemplos, límites y códigos de salida.
- Actualizar `CHANGELOG.md`.
- Ejecutar la suite completa y `uv build`.
- Ejecutar CI en Python 3.11, 3.12 y 3.13.
- Publicar como versión `0.3.0` si todo pasa.

## Criterio de aceptación

`--all` nunca termina con éxito entregando un informe que el cliente sabe que
está incompleto. Una descarga completa debe cumplir:

```text
returned_row_count == row_count
truncated == false
pagination.stop_reason == "complete"
```

La API de Google admite `offset` y `limit` en `runReport`, con hasta 250.000
filas por petición. La operación no garantiza una instantánea inmutable si los
datos cambian mientras se descargan.
