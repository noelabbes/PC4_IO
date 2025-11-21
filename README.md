# Herramienta de Optimización de Logística RMC

Este proyecto implementa un sistema avanzado de optimización para la logística de entrega de concreto premezclado (RMC) utilizando Programación Lineal Entera Mixta (MILP). Programa la producción en plantas de mezcla y coordina el transporte de camiones a sitios de construcción, minimizando los costos totales mientras respeta ventanas de tiempo, capacidades y restricciones operativas.

## Características

- **Programación de Producción**: Optimiza el tiempo de producción de lotes en múltiples unidades de mezcla
- **Optimización de Transporte**: Asigna camiones a lotes considerando capacidad, costos y tiempos de viaje
- **Gestión de Ventanas de Tiempo**: Garantiza entregas dentro de ventanas de tiempo especificadas con penalizaciones por retraso
- **Restricciones de Secuencia**: Mantiene secuencias adecuadas de vertido de concreto en cada sitio
- **Minimización de Costos**: Equilibra costos de transporte, costos fijos de camiones y penalizaciones por retraso
- **Verificación de Factibilidad**: Valida restricciones de la solución e identifica violaciones
- **Generación de Diagrama de Gantt**: Produce horarios visuales mostrando cronogramas de producción y entrega

## Requisitos

- Python 3.7+
- PuLP (biblioteca de modelado de optimización)
- pandas
- numpy
- tabulate
- HiGHS solver (via highspy para rendimiento óptimo)

## Instalación

1. Clona o descarga los archivos del proyecto
2. Instala los paquetes requeridos:
   ```bash
   pip install pulp pandas numpy tabulate highspy
   ```

## Uso

1. Prepara archivos de datos de entrada en formato CSV:
   - `construction_sites.csv`: Información de sitios con demandas y ventanas de tiempo
   - `trucks.csv`: Detalles de la flota de camiones con capacidades y costos
   - `units.csv`: Especificaciones de unidades de producción

2. Configura parámetros en `params.json`:
   - Ventanas de tiempo (T1, T2)
   - Tiempos de procesamiento (wash_time, unload_time, etc.)
   - Pesos de costos (alpha, beta)

3. Ejecuta el orquestador:
   ```bash
   python orchestrator.py
   ```

El sistema ejecutará el pipeline de optimización y generará:
- Horario óptimo de producción y entrega
- Desglose de costos
- Reporte de factibilidad
- Diagrama de Gantt (`gantt_optimal_schedule_full.png`)

## Formatos de Datos

### construction_sites.csv
| Columna | Descripción |
|---------|-------------|
| site_id | Identificador único del sitio |
| demand_m3 | Volumen de concreto requerido (m³) |
| tw_start_h | Inicio de ventana de tiempo (horas o HH:MM) |
| tw_end_h | Fin de ventana de tiempo (horas o HH:MM) |
| concrete_type | Tipo de concreto |
| dist_km | Distancia desde la planta (km) |
| travel_time_min | Tiempo de viaje (minutos) |

### trucks.csv
| Columna | Descripción |
|---------|-------------|
| truck_id | Identificador único del camión |
| capacity_m3 | Capacidad máxima de carga (m³) |
| min_load_m3 | Requisito mínimo de carga (m³) |
| fixed_cost | Costo fijo por uso |
| var_cost_per_km | Costo variable por km |

### units.csv
| Columna | Descripción |
|---------|-------------|
| unit_id | Identificador único de la unidad |
| process_time_min | Tiempo de procesamiento por lote (minutos) |
| capacity_m3 | Capacidad de la unidad (m³) |

### params.json
```json
{
  "T1": 420,
  "T2": 1020,
  "wash_time": 10,
  "unload_time": 30,
  "wait_before_departure": 0,
  "setting_time": 90,
  "max_tardiness_allowed": 120,
  "alpha": 1.0,
  "beta": 1.0
}
```

## Resumen del Pipeline

El orquestador ejecuta los siguientes pasos:

1. **Cell 2**: Importa utilidades y muestra requisitos de datos
2. **Cell 5**: Carga y valida datos de entrada
3. **Cell 6**: Genera lotes a partir de demandas de sitios
4. **Cell 7**: Construye modelo MILP optimizado con restricciones físicas duras
5. **Cell 8**: Genera solución heurística con variables de holgura
6. **Cell 9**: Reconstruye y analiza la solución óptima
7. **Cell 11**: Resuelve MILP completo usando solver HiGHS
8. **Cell 10**: Valida factibilidad de la solución
9. **Cell 12**: Genera visualización de diagrama de Gantt

## Salidas

- **Logs de Consola**: Progreso detallado de ejecución y resultados
- **orchestrator.log**: Log completo de ejecución
- **gantt_optimal_schedule_full.png**: Diagrama visual de horario
- **Datos Compartidos**: Horarios optimizados y resúmenes de costos en memoria

## Restricciones Clave

- Límites de capacidad de producción por unidad
- Capacidad y disponibilidad de camiones
- Ventanas de tiempo para entregas
- Límites de tiempo de fraguado del concreto
- Requisitos de secuencia de vertido
- Tiempos de viaje y procesamiento

## Objetivo de Optimización

Minimizar: `α × (costos de transporte + costos fijos) + β × retraso total + penalización × violaciones de restricciones`

Donde α y β son pesos configurables, y las penalizaciones se aplican a restricciones suaves como tiempo de fraguado y retraso máximo entre vertidos.