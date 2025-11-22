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

## Arquitectura del Proyecto

El proyecto ha sido reestructurado en una arquitectura modular para mejorar la escalabilidad y el mantenimiento:

```
project_root/
├── src/                    # Código fuente principal
│   ├── data/               # Módulos de carga y validación de datos (loader.py, schema.py)
│   ├── core/               # Lógica de negocio y optimización
│   │   ├── optimization/   # Modelos MILP, heurísticas y solvers
│   │   ├── batching.py     # Generación de lotes
│   │   ├── analysis.py     # Análisis de soluciones
│   │   ├── reporting.py    # Generación de reportes
│   │   └── validation.py   # Verificación de restricciones
│   ├── visualization/      # Generación de gráficos (Gantt)
│   ├── context.py          # Gestión de estado compartido
│   ├── config.py           # Configuración del sistema
│   └── main.py             # Punto de entrada principal
├── input/                  # Archivos de datos de entrada (CSV, JSON)
├── output/                 # Resultados generados (Logs, Gráficos)
└── requirements.txt        # Dependencias del proyecto
```

## Instalación

1. Clona o descarga los archivos del proyecto.
2. Instala los paquetes requeridos:
   ```bash
   pip install -r requirements.txt
   ```
   O manualmente:
   ```bash
   pip install pulp pandas numpy tabulate highspy matplotlib
   ```

## Uso

1. **Preparar Datos**: Asegúrate de que los archivos de entrada estén en la carpeta `input/`:
   - `construction_sites.csv`
   - `trucks.csv`
   - `units.csv`
   - `params.json`

2. **Ejecutar**: Desde la raíz del proyecto, ejecuta el módulo principal:
   ```bash
   python -m src.main
   ```

3. **Resultados**: Revisa la carpeta `output/` para ver:
   - `gantt_optimal_schedule_full.png`: Diagrama de Gantt.
   - Logs de ejecución y reportes en consola.

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

El sistema ejecuta los siguientes pasos secuenciales:

1. **Carga de Datos**: `src.data.loader` lee y valida los archivos CSV/JSON.
2. **Batching**: `src.core.batching` divide la demanda en lotes de producción.
3. **Modelado**: `src.core.optimization.model` construye el modelo matemático MILP.
4. **Heurística**: `src.core.optimization.heuristic` genera una solución inicial (Warm Start).
5. **Optimización**: `src.core.optimization.solver` resuelve el problema usando HiGHS.
6. **Validación**: `src.core.validation` verifica el cumplimiento de todas las restricciones.
7. **Reporte**: `src.core.reporting` genera métricas de desempeño.
8. **Visualización**: `src.visualization.gantt` crea el diagrama de Gantt en `output/`.

## Restricciones Clave

- Límites de capacidad de producción por unidad
- Capacidad y disponibilidad de camiones
- Ventanas de tiempo para entregas
- Límites de tiempo de fraguado del concreto
- Requisitos de secuencia de vertido
- Tiempos de viaje y procesamiento

## Objetivo de Optimización

Minimizar: `α × (costos de transporte + costos fijos) + β × retraso total + penalización × violaciones de restricciones`

Donde α y β son pesos configurables.

## 🏆 Resultados de la Réplica y Validación Experimental

Esta sección presenta los resultados finales obtenidos tras la ejecución completa del *pipeline* de optimización (`orchestrator.py`). El objetivo fue replicar el **Caso de Estudio Real** descrito en la Sección 4 del paper de Tibaldo et al. (2025), validando tanto la factibilidad física como la eficiencia económica del modelo propuesto.

### 🖥️ Entorno de Ejecución
El modelo fue resuelto en una instancia de computación en la nube con arquitectura **ARM64**, demostrando la portabilidad y eficiencia del código desarrollado.

* **Sistema Operativo:** Ubuntu 22.04.5 LTS (GNU/Linux 6.8.0-1022-oracle aarch64)
* **Hardware:** Servidor Oracle Cloud (Ampere Altra)
* **Recursos:** 4 vCPUs, 24 GB RAM
* **Solver:** Highs 1.12.0 (Open Source)

### 📊 Resumen de la Solución Óptima

El orquestador ejecutó exitosamente la construcción del modelo matemático (versión compacta robusta), una heurística constructiva de *Warm Start*, y la optimización global exacta mediante el solver Highs.

| Métrica | Valor Obtenido (Nuestra Réplica) | Valor de Referencia (Paper) | Notas |
| :--- | :--- | :--- | :--- |
| **Estado del Solver** | **Optimal** (Gap 0.01%) | Optimal | Convergencia exitosa. |
| **Tiempo de Ejecución** | **~19.5 minutos** (1177s) | ~4 minutos (232s) | Diferencia esperada por hardware (i7 3.6GHz vs ARM vCPU) y solver (Gurobi vs Highs). |
| **Costo Objetivo Total** | **$13,591.00** | $14,474.00 | Nuestra solución encontró una logística ligeramente más económica. |
| **Uso de Flota** | **14 Camiones** | 12 Camiones | Diferencia marginal aceptable dada la discretización temporal ($\Delta t=10$). |
| **Total de Viajes** | **46** (Todos los lotes) | 47 | Cobertura total de la demanda. |

### 📉 Estadísticas del Modelo: Comparativa Paper vs. Réplica

A continuación se detallan las dimensiones del modelo matemático (variables y restricciones) reportadas por los autores para el Caso de Estudio, comparadas con las generadas por nuestra implementación.

| Métrica | Paper Original (Tibaldo et al., 2025) | Nuestra Réplica (Highs/ARM64) |
| :--- | :--- | :--- |
| **Total Variables** | 23,550 | 52,841 |
| **Variables Binarias** | *No especificado* | 52,684 |
| **Variables Continuas** | *No especificado* | 157 |
| **Restricciones** | 3,344  | 2,081 |
| **Gap de Optimalidad** | 0% [cite: 1732] | 0.01% |

> **Nota Técnica sobre las Dimensiones:**
> * **Variables:** Nuestra réplica genera aproximadamente el doble de variables que el paper. Esto es intencional: utilizamos una estrategia de generación de variables "robusta" (Safety Net) que cubre todo el horizonte de tiempo $[T_1, T_2]$ con una discretización de $\Delta t=10$ min, en lugar de podar agresivamente el dominio (como sugieren los Algoritmos 2 y 3 del paper). Esto garantiza la factibilidad matemática ante datos reales ruidosos a cambio de un mayor consumo de memoria.
> * **Restricciones:** A pesar de tener más variables, nuestro modelo utiliza **menos restricciones** (2,081 vs 3,344). Esto se debe a la implementación de una formulación **compacta** para las ecuaciones de sincronización y capacidad, aprovechando las capacidades de presolve del solver Highs.

### ✅ Validación de Calidad y Factibilidad

El módulo de verificación (`cell10_checker.py`) auditó la solución final contra las restricciones físicas estrictas del problema, confirmando **cero violaciones**:

* **✅ 0 Violaciones de Setting Time (Eq. 8):** Todo el concreto fue entregado y descargado antes de su tiempo de fraguado.
* **✅ 0 Juntas Frías (Eq. 14):** La continuidad de vertido en obra se respetó estrictamente (Max Time Lag).
* **✅ 0 Solapamientos de Descarga (Eq. 13):** Secuenciación perfecta de camiones en cada sitio de construcción.
* **✅ 0 Conflictos de Recursos:** Ningún camión o unidad de producción fue asignado a dos tareas simultáneas.

### 📈 Visualización de Resultados

El sistema generó automáticamente un **Diagrama de Gantt Detallado** (`gantt_optimal_schedule_full.png`) que ilustra la sincronización precisa de:
1.  **Carga:** Producción en unidades $u_1, u_2$.
2.  **Ciclo del Camión:** Espera $\to$ Lavado $\to$ Viaje $\to$ Descarga $\to$ Retorno.

> **Conclusión:** La réplica ha sido exitosa. Se logró implementar un modelo MILP complejo de la literatura científica utilizando herramientas *open source* y hardware accesible, obteniendo una solución óptima que respeta todas las restricciones operativas críticas de la industria del hormigón premezclado.

---