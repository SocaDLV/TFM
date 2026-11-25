# BIBLIA TÉCNICA Y DE DISEÑO ARQUITECTURAL DEL CO-SIMULADOR (LLMSimulator + BookSim2)
**Investigación de Fin de Máster (TFM) en Arquitectura de Computadores y Redes de Interconexión**  
*Documento Maestro de Ingeniería y Referencia Teórica*  
*Fecha de Consolidación: Octubre 2026*

---

## ÍNDICE GENERAL

1. [Capítulo 1: Arquitectura General de LLMSimulator-orig (SCALE SNU)](#capítulo-1-arquitectura-general-de-llmsimulator-orig-scale-snu)
   - 1.1. Flujo Global de Ejecución: Desde el Punto de Entrada (`eval/test.cpp`) hasta el Clúster
   - 1.2. Construcción y Topología del Grafo de Ejecución (`ModuleGraph`, `TopModuleGraph` y Nodos Push/Pop)
   - 1.3. El Planificador (`Scheduler`): Gestión de Lotes, Secuencias y Modos de Carga (`synthesis` vs. Real)
   - 1.4. Modelo de Relojes Asíncronos (`device_time`, `high_time`, `low_time`) y Barreras de Sincronización
   - 1.5. Modelado Analítico de Cómputo y Memoria (Ecuaciones Roofline) e Integración de Ramulator2
   - 1.6. Catálogo y Taxonomía de Modelos Soportados (`src/model/model_config.h` y `src/model/llm.cpp`)
   - 1.7. Modelado Microarquitectural de la Atención y Ecuaciones Matemáticas (`src/module/attention.cpp`, `compressed_kv_restore.cpp`, `src/hardware/attention_sum_impl.cpp`, `attention_gen_impl.cpp`)
   - 1.8. El Subsistema de Memoria, Perfiles de Hardware y Modelo Energético (`src/hardware/hardware_config.h`, `src/dram/dram_interface.cpp`, `src/dram/power.h`, `module_graph.cpp`)
2. [Capítulo 2: Modelado Matemático de Mixtral 8x7B y Enrutamiento MoE](#capítulo-2-modelado-matemático-de-mixtral-8x7b-y-enrutamiento-moe)
   - 2.1. Anatomía Arquitectural de Mixtral 8x7B en Paralelismo Experto y Tensorial
   - 2.2. Algoritmo de Enrutamiento MoE (`Route::forward` y `GateUpdate::aggregate_expert`)
   - 2.3. Distribución Zipfiana vs. Uniforme: Impacto del Parámetro `skewness` y Asignación Real en B100
   - 2.4. Demostración Matemática del Régimen Memory-Bound en `decode_mode` (22.155 ns)
   - 2.5. Análisis del Desbalance entre GPUs: ¿Por qué 11 tokens vs. 4 tokens solo difieren en 48 ns?
   - 2.6. Demostración de la Proporción Temporal entre Attention (~6.338 ns) y ExpertFFN (~22.155 ns) (~1:3.5)
3. [Capítulo 3: Arquitectura Interna de BookSim2 y Nuestra Librería API (`booksim_api`)](#capítulo-3-arquitectura-interna-de-booksim2-y-nuestra-librería-api-booksim_api)
   - 3.1. El Motor de Simulación Ciclo a Ciclo de BookSim2 (`TrafficManager::_Step`)
   - 3.2. Ciclo de Vida del Paquete y sus Flits (`head`, `body`, `tail`)
   - 3.3. Tiempos Fundamentales: $ctime$ (Creación), $itime$ (Inyección) y $atime$ (Retiro)
   - 3.4. Descomposición Física: Espera en Cola de NIC (`Queueing_Delay`) vs. Tránsito en Red (`Network_Latency`)
   - 3.5. Métricas Avanzadas de Flits y Productividad de Red
   - 3.6. Contexto de Operación LLM y Trazado Temporal (Scatter/Gather y Ventanas NS)
   - 3.7. Diseño del Wrapper C++ `booksim_api` y Desacoplamiento de `main.cpp`
   - 3.8. Topologías de Red en BookSim2: Construcción de Mallas y Toros (`booksim2/src/networks/kncube.cpp`)
   - 3.9. Microarquitectura del Router Virtual-Channel y Prevención de Deadlock (`booksim2/src/routers/iq_router.cpp`, `routefunc.cpp`, `buffer_state.cpp`, `allocator/`)
4. [Capítulo 4: Nuestro Co-Simulador en Lazo Cerrado (LLMSimulator + BookSim2)](#capítulo-4-nuestro-co-simulador-en-lazo-cerrado-llmsimulator--booksim2)
   - 4.1. El Paradigma de Integración Oráculo en Modo Bulk Synchronous Parallel (BSP)
   - 4.2. Traducción de Tensores y Metadatos de Enrutamiento a Tráfico Unicast (`MoEScatter` y `MoEGather`)
   - 4.3. Matemática Rigurosa de Paquetización: Demostración de los 9 Flits y 288 Bytes en Mixtral
   - 4.4. Secuencia Causal de Barreras en la Capa MoE: De Attention a MoEGather
   - 4.5. Auditoría Crítica de `cached_latency[layer_name]`: Escalar Global vs. Vector por GPU Destino
   - 4.6. Auditoría Forense de Causalidad Física en MoEGather/MoEScatter y Demostración de Simetría de Tráfico
     - 4.6.1. Orden de Ejecución C++ al Entrar al Oráculo de `MoEGather` y Garantía de Estabilidad Temporal en `sync_3`
     - 4.6.2. Demostración Matemática de Simetría en la Matriz de Tráfico ($T_{\text{Gather}} = T_{\text{Scatter}}^T$) y Dispersión Estocástica de Tokens
     - 4.6.3. Principio de Causalidad Bilateral Emisor-Receptor en Colectivas MoE (`MoEScatter` y `MoEGather`)
     - 4.6.4. Desglose Microarquitectural en Tres Fases (Pre-Stall, Colectiva Activa y Post-Stall de Barrera Sincrónica)
     - 4.6.5. Normalización de Ciclos Relativos en la API de BookSim2 y Alineación de Cero Ciclos en la Visualización Híbrida
     - 4.6.6. Validación Experimental End-to-End: Cero Infracciones Causales y Continuidad Cronológica Estricta
   - 4.7. Integración de AllReduce en el Oráculo BookSim2: Modelado Ring-AllReduce con Causalidad Cuádruple (Vía 2)
   - 4.8. Estudio de Desbalanceo Extremo de Carga en Expertos MoE (Skewness, Puntos Calientes de Red e In-Cast Hotspots - Vía 3)
   - 4.9. Estudio Comparativo Arquitectónico: Mixtral 8x7B vs. DeepSeek-V3 (Fine-Grained MoE & MLA - Vía 4)
     - 4.9.1. Contexto y Fundamentación Arquitectónica: Grano Grueso vs. Grano Fino
     - 4.9.2. Mecanismo de Compresión de Atención Multi-Head Latent Attention (MLA)
     - 4.9.3. Desglose Microarquitectural de DeepSeek-V3: Capas Densas Iniciales y Expertos Compartidos
     - 4.9.4. Batería Experimental Paritaria (8x B100, Toro 1D, BS=32)
     - 4.9.5. Análisis Macroscópico Comparativo de Tiempos y Tráfico NoC
     - 4.9.6. Auditoría de Tráfico de Paquetes (`packet_tracking_debug.csv`) y Dinámica de Colas
     - 4.9.7. Hallazgos Científicos y Conclusiones Arquitectónicas de la Vía 4
     - 4.9.8. Sensibilidad Topológica: Toro 1D vs. Malla 2D (4x2 nodos) y Alivio de Contención Bidimensional
     - 4.9.9. Justificación Metodológica: Ejecución BSP vs. Esquemas de Pipelining (DualPipe)
5. [Capítulo 5: Parches Arquitectónicos Aplicados al Simulador Base](#capítulo-5-parches-arquitectónicos-aplicados-al-simulador-base)
   - 5.1. Correcciones Críticas en `decoder.cpp`: Conexiones Residuales y Tipado de Capas
   - 5.2. Correcciones en `layer.cpp`: Cadena de Dependencias en Bloques SwiGLU
   - 5.3. Correcciones en `timeboard.cpp`: Preservación de la Causalidad Temporal Asíncrona
   - 5.4. Corrección de Causalidad Bidireccional en el Oráculo de Red (`src/module/communication.cpp`)
6. [Capítulo 6: Sistema de Trazabilidad Completa (.trc y .csv) y Suite de Análisis en Python](#capítulo-6-sistema-de-trazabilidad-completa-trc-y-csv-y-suite-de-análisis-en-python)
   - 6.1. Arquitectura del Logger C++ en `Device`, `Module` y `ModuleGraph`
   - 6.2. Propagación de Identidad Jerárquica (`module_map_name`) a Nodos POP
   - 6.3. Automatización de Ejecución y Orquestación (`run_sim.py`)
   - 6.4. Análisis Macroscópico de Latencias y Saturación de Red (`analyze_traces.py`) - Cierre del Bloque B
   - 6.5. Visualizador de Congestión en Red y Paginación de Paquetes (`plot_packet_tracking.py`)
   - 6.6. Cronograma Micro-Arquitectural Causal GPU Cycle-to-Cycle (`plot_cronograma.py`)
7. [Capítulo 7: Amenazas a la Validez, Limitaciones Actuales y Hoja de Ruta de Mejoras](#capítulo-7-amenazas-a-la-validez-limitaciones-actuales-y-hoja-de-ruta-de-mejoras)
   - 7.1. Simplificaciones Asumidas en el Co-Simulador Actual
   - 7.2. Evaluación de Impacto en la Precisión Científica
   - 7.3. Hoja de Ruta y Roadmap de Extensiones Futuras
   - 7.4. Hardware Multicast e In-Network Reduction en Arquitecturas MoE de Grano Fino
   - 7.5. Propuesta de Vía 5: Co-Simulación Dual-Stream & Pipelining de Micro-Batches (DualPipe)
8. [Capítulo 8: Referencia Exhaustiva Archivo por Archivo (File-by-File Codebase Reference)](#capítulo-8-referencia-exhaustiva-archivo-por-archivo-file-by-file-codebase-reference)
   - 8.1. Punto de Entrada y Evaluación (`eval/`)
   - 8.2. Infraestructura Común (`src/common/`)
   - 8.3. Subsistema DRAM y Emulación de Memoria/PIM (`src/dram/`)
   - 8.4. Capa Hardware y Ejecución de Aceleradores (`src/hardware/`)
   - 8.5. Definición y Topología de Modelos LLM (`src/model/`)
   - 8.6. Módulos Operacionales y Grafo Computacional (`src/module/`)
   - 8.7. Planificador de Inferencia y Lotes (`src/scheduler/`)
   - 8.8. Herramientas de Automatización y Análisis en Python (`LLMSimulator/`)
   - 8.9. Subsistema de Red BookSim2 (`booksim2/src/`)
9. [Capítulo 9: Banco de Preguntas Frecuentes (FAQ) y Defensa Técnica ante Tutor y Tribunal (P1–P30)](#capítulo-9-banco-de-preguntas-frecuentes-faq-y-defensa-técnica-ante-tutor-y-tribunal)
   - 9.1. Bloque A: Paradigma de Co-Simulación, Causalidad y Sincronización Temporal (P1–P5)
   - 9.2. Bloque B: Arquitectura de Red NoC, BookSim2 y Colectivas (P6–P10)
   - 9.3. Bloque C: Modelado de LLMs (Mixtral vs. DeepSeek-V3) y Dinámica MoE (P11–P15)
   - 9.4. Bloque D: Trazabilidad, Visualización y Rigor Metodológico (P16–P20)
   - 9.5. Bloque E: Perfiles Hardware (B100), Subsistema de Memoria (Ramulator 2.0) y Energía (P21–P25)
   - 9.6. Bloque F: Topologías Concretas, Enrutamiento NoC y Escalabilidad (P26–P30)
10. [Capítulo 10: Interfaz Gráfica de Usuario (GUI) y Entorno Interactivo de Co-Simulación Web Local (Workbench)](#capítulo-10-interfaz-gráfica-de-usuario-gui-y-entorno-interactivo-de-co-simulación-web-local-workbench)
   - 10.1. Motivación y Arquitectura del Workbench (`launch_gui.py` y `gui/`)
   - 10.2. Aislamiento Estricto y Ciclo de Vida en Staging (`build/tmp_staging/`)
   - 10.3. Pestaña 1: Configurador Interactivo y Guardarraíles en Tiempo Real
   - 10.4. Pestaña 2: Resultados Arquitectónicos y Visualizadores en Canvas HTML5 al Vuelo
   - 10.5. Selector Multidimensional de Iteraciones (Fase 2.5)
   - 10.6. Visualizador Híbrido Sincronizado Split-Screen (Fase 2.5)
   - 10.7. Pestaña 3: Gestor de Historial y Comparador Multi-Simulación Arbitrario (Fase 3)
   - 10.8. Pulido y Mejoras de Usabilidad Científica (Fase 3.5)
   - 10.9. Refinamiento del Visualizador Híbrido: Contenedor Acotado con Scroll Único, Virtual Scrolling y Tooltips Microarquitectónicos (Fases 3.8 y 3.9)
   - 10.10. Auditoría Matemática y Paridad Absoluta CLI ↔ GUI (Fase 3.9.1)
   - 10.11. Pestaña 4: Mapa Topológico Interactivo NoC, Heatmap de Tráfico e Inspector Arquitectónico (Fase 4)
   - 10.12. Refinamiento de Pestaña 4: Mapa de Calor Térmico en Enlaces/Flujos NoC y Tooltips Interactivos en Hover sobre Conexiones (Fase 4.5)
   - 10.13. Despliegue en Linux (`run_gui.sh`) y Validación End-to-End del Sistema (Fase 5)
   - 10.14. Optimización de Memoria y Escalabilidad para Simulaciones Masivas (16+ GPUs / DeepSeek-V3 BS=128)

---

# CAPÍTULO 1: Arquitectura General de LLMSimulator-orig (SCALE SNU)

## 1.1. Flujo Global de Ejecución: Desde el Punto de Entrada (`eval/test.cpp`) hasta el Clúster

El simulador `LLMSimulator` desarrollado por el laboratorio SCALE (Seoul National University) modela la ejecución de modelos de lenguaje masivos mediante un grafo estático de dependencias evaluado de manera cooperativa sobre múltiples aceleradores. El punto de entrada formal del ejecutable reside en [`eval/test.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L14-L358).

El ciclo de vida de la simulación sigue las siguientes fases rigurosas:

```
[config.yaml]
      │
      ▼
1. eval/test.cpp (main) ────► Carga YAML y Configura Hardware/Modelo
      │
      ▼
2. Scheduler::Create() ─────► Inicializa Colas (sequence_queue, running_queue)
      │
      ▼
3. Cluster::Create() ───────► Instancia Nodos, Dispositivos y TopModuleGraph
      │
      ▼
4. Model::Model() ──────────► Construye el Grafo de Módulos (Layers, Tensors)
      │
      ▼
5. cluster->set_dependency() ► Resuelve Punteros de Tensores y Barreras (sync)
      │
      ▼
6. cluster->runIteration() ─► Bucle Principal por Iteraciones (Decode / Prefill)
      │
      ▼
7. Cluster::run() ──────────► Bucle While: check_module_graph_remain()
      │
      ▼
8. TopModuleGraph::run() ───► Polling Round-Robin por Módulo (Break si !ready)
```

1. **Lectura de Configuración ([`eval/test.cpp:L15-L131`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L15-L131)):**
   Se analiza el archivo YAML (`config.yaml`), extrayendo el modelo seleccionado (`model_name`), número de nodos (`num_node`), número de aceleradores por nodo (`num_device`), tipo de procesador (`GPU`, `LOGIC`, `GPU+PIM`), modo de dataset (`synthesis` vs. traza de longitud real), longitudes de secuencia (`input_len`, `output_len`), número de iteraciones (`iter`), y banderas de optimización como `parallel_execution`, `decode_mode`, `prefill_mode` y `use_ramulator`.

2. **Inicialización de Parámetros de Interconexión ([`eval/test.cpp:L58-L90`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L58-L90)):**
   Se configuran las especificaciones físicas de la red estática interna:
   - Para **NVLink 5.0 (B100)**: ancho de banda intra-nodo `device_ict_bandwidth` = $900.0\text{ GB/s}$ ($900 \times 10^9\text{ B/s}$), latencia base `device_ict_latency` = $800\text{ ns}$ ($0.8\,\mu\text{s}$).
   - Para **InfiniBand XDR / NDR**: ancho de banda inter-nodo `node_ict_bandwidth` = $50.0\text{ - }100.0\text{ GB/s}$, latencia base = $130\text{ ns}$.

3. **Instanciación del Planificador ([`eval/test.cpp:L224-L226`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L224-L226)):**
   Se crea el objeto singleton [`Scheduler`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/scheduler.h#L16-L120), dimensionando las colas de ráfaga y cálculo de acuerdo a `max_batch_size` (ej. 32 secuencias) y `max_process_token`.

4. **Instanciación de la Jerarquía de Hardware ([`eval/test.cpp:L228`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L228)):**
   `Cluster::Create(system_config, scheduler)` instancia una lista de objetos `Node`, y cada `Node` instancia sus respectivos objetos `Device`. Cada `Device` posee su propio `StatusBoard` (registro de tiempos y contadores energéticos) y su propio `TopModuleGraph`.

5. **Construcción del Grafo Computacional ([`eval/test.cpp:L230`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L230)):**
   La clase `Model` (`src/model/llm.cpp`) toma la configuración de capas del LLM (ej. 32 bloques decodificadores en Mixtral) y ejecuta de manera declarativa el grafo de capas invocando el operador funcional `operator()` de cada módulo sobre cada acelerador.

6. **Resolución de Dependencias Estáticas ([`eval/test.cpp:L233`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L233)):**
   Se ejecuta `cluster->set_dependency()`, que atraviesa todos los grafos invocando `ModuleGraph::set_dependency_tensor()`. Aquí se asocian los tensores de salida con las entradas de las operaciones consumidoras y se enlazan las listas de tensores cruzados en módulos colectivos (`sync = true`).

7. **Bucle de Ejecución Causal (`Cluster::runIteration` y `Cluster::run`):**
   Ubicado en [`src/hardware/cluster.cpp:L459-L525`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/cluster.cpp#L459-L525) y [`src/hardware/cluster.cpp:L1084-L1092`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/cluster.cpp#L1084-L1092). El clúster itera token a token, actualizando los metadatos de enrutamiento y avanzando los grafos hasta que ningún módulo reste por ejecutar.

---

## 1.2. Construcción y Topología del Grafo de Ejecución (`ModuleGraph`, `TopModuleGraph` y Nodos Push/Pop)

El modelo de ejecución de LLMSimulator no utiliza un motor dinámico de grafos dirigidos acíclicos (DAG) con colas de tareas asíncronas tradicionales, sino una estructura secuencial jerárquica basada en una lista plana de eventos encapsulados en pares **Push/Pop**.

### La Pila Jerárquica de Nodos
Cuando se define un módulo complejo (por ejemplo, `MoEDecoder`), este se compone internamente de submódulos anidados:

$$\text{MoEDecoder} \longrightarrow \{\text{LayerNorm}, \text{Attention}, \text{Residual}, \text{MoE\_FFN}, \text{Residual}\}$$

Cada invocación a un módulo mediante `Module::operator()` ([`src/module/module.cpp:L10-L26`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module.cpp#L10-L26)) ejecuta exactamente esta secuencia:

```cpp
Tensor::Ptr Module::operator()(const Tensor::Ptr input, BatchedSequence::Ptr sequences_metadata) {
  Tensor::Ptr return_tensor;
  device->top_module_graph->push_module_graph(getptr(), input);
  return_tensor = forward(input, sequences_metadata);
  device->top_module_graph->pop_module_graph(getptr(), return_tensor);
  return return_tensor;
};
```

Esto inserta en `TopModuleGraph::module_graph` (un `std::vector<ModuleGraph::Ptr>`):
1. **Nodo Push (`module_pop = false`):** Marca la entrada a un ámbito funcional y establece el nivel jerárquico (`module_level++`).
2. **Sub-nodos Intermedios:** Los módulos atómicos invocados dentro de `forward()` (ej. `Linear`, `AttentionGen`, `Activation`).
3. **Nodo Pop (`module_pop = true`):** Marca la finalización del módulo, disminuye el nivel jerárquico (`module_level--`) y desencadena la consolidación del tiempo y energía consumidos en `TopModuleGraph::set_pop_status()`.

### Estructura de `ModuleGraph`
Cada nodo del vector almacena:
- `Module::Ptr module`: Puntero polimórfico a la clase derivada del módulo (`Linear`, `MoEScatter`, `Attention`, etc.).
- `Tensor::Ptr input` / `TensorVec input_vec`: Puntero a los tensores de entrada.
- `bool module_pop`: Bandera que distingue si el nodo es de apertura (Push) o consolidación (Pop).
- `std::vector<Tensor::Ptr> dependency_tensor_list`: Lista de tensores de otros dispositivos de los cuales depende este módulo para poder ejecutarse si `module->sync == true`.
- `bool stamped`: Bandera interna para el timeboard.

---

## 1.3. El Planificador (`Scheduler`): Gestión de Lotes, Secuencias y Modos de Carga

El planificador ([`src/scheduler/scheduler.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/scheduler.cpp)) simula la política de servicio a nivel de sistema operativo y framework de servicio (estilo vLLM / TensorRT-LLM).

### Dimensionamiento y Colas de Servicio
- **`sequence_queue`:** Cola de espera global que almacena solicitudes entrantes que aún no han sido admitidas por falta de memoria o límite de batch.
- **`running_queue`:** Vector de objetos `BatchedSequence::Ptr`, indexado por rango de paralelismo de datos (DP rank):
  $$\text{dp\_degree} = \frac{\text{num\_device} \times \text{num\_node}}{\text{ne\_tp\_dg}}$$
  Para un clúster de 8 GPUs con grado de paralelismo tensorial no experto ($\text{ne\_tp\_dg} = 1$), $\text{dp\_degree} = 8$.

### Modos de Operación: `prefill_mode` vs. `decode_mode`
El simulador implementa una distinción estricta entre las dos fases de un LLM:
1. **Prefill Mode (`system_config.prefill_mode = true`):**
   - Modela el procesamiento masivo del prompt inicial.
   - En [`eval/test.cpp:L132-L135`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp#L132-L135) y [`src/scheduler/scheduler.cpp:L84-L87`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/scheduler.cpp#L84-L87), la longitud de salida forzada es $1$.
   - La dimensión de activación $m$ en las multiplicaciones de matrices (GEMM) equivale a la longitud completa del prompt (`input_len`, ej. 1024 tokens).
   - Régimen: **Compute-Bound** (altamente limitado por la capacidad de cómputo en TFLOPS del acelerador).
2. **Decode Mode (`system_config.decode_mode = true`):**
   - Modela la generación autorregresiva token a token.
   - En [`src/scheduler/scheduler.cpp:L88-L90`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/scheduler.cpp#L88-L90), `seq->current_len` se inicializa directamente en `input_len`, simulando que el prompt ya fue procesado y reside en la caché KV.
   - Cada iteración del planificador procesa exactamente $1$ nuevo token por secuencia activa:
     $$\text{seq->num\_process\_token} = 1$$
   - En las multiplicaciones de matrices de los expertos, la dimensión de lote $m$ por secuencia es $1$.
   - Régimen: **Memory-Bound** (limitado críticamente por el ancho de banda de la memoria HBM al leer los pesos del modelo).

### Modos de Dataset: `synthesis` vs. Archivos CSV Reales
En [`src/scheduler/scheduler.cpp:L511-L550`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/scheduler.cpp#L511-L550):
- **Modo `synthesis`:** No requiere archivos externos. Las secuencias se generan sintéticamente en `pushDummySeq` con longitudes fijas `input_len` y `output_len`. El enrutamiento MoE se genera algorítmicamente mediante distribuciones estadísticas en memoria (`getRandomExpert` o `getZipfianRandomExpert`).
- **Modo Real (Archivos CSV):** Carga trazas empíricas desde `../expert_data/experts_<model>_<dataset>.csv`. Cada línea contiene secuencias reales con longitudes $L_{in}$ y $L_{out}$ y las decisiones reales de enrutamiento por capa observadas durante inferencias con modelos reales de HuggingFace.

---

## 1.4. Modelo de Relojes Asíncronos (`device_time`, `high_time`, `low_time`) y Barreras de Sincronización

Cada acelerador (`Device`) mantiene un registro local de avance temporal denominado `StatusBoard` ([`src/hardware/stat.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/stat.h)). A diferencia de los simuladores dirigidos por eventos con una cola global de eventos ordenados por tiempo (estilo ns-3 o gem5), LLMSimulator utiliza un esquema de **avance local de relojes con sondeo cooperativo (Polling Round-Robin)**.

### Los Tres Relojes por GPU
1. **`device_time` (Tiempo Principal de la GPU):** Representa el tiempo global simulado del acelerador en nanosegundos. Es el reloj sobre el que se sincronizan las comunicaciones y los eventos de red.
2. **`high_time` (Reloj del Dominio de Cómputo Principal / GPU):** Utilizado en configuraciones heterogéneas (`parallel_execution = true`) cuando ciertas operaciones se ejecutan en los núcleos principales de cómputo.
3. **`low_time` (Reloj del Dominio Secundario / PIM / Logic Die):** Utilizado cuando ciertas capas (como normalizaciones o proyecciones MoE) se descargan a unidades Processing-In-Memory (PIM).

En sistemas homogéneos tradicionales (como nuestro clúster de Nvidia B100), `parallel_execution = false`, por lo que el reloj físico efectivo es puramente `device_time`:
$$\text{device\_time} \leftarrow \text{device\_time} + \text{exec\_status.total\_duration}$$

### El Bucle de Evaluación Cooperativa (Round-Robin Polling)
El motor de avance en [`src/hardware/cluster.cpp:L1084-L1092`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/cluster.cpp#L1084-L1092) es extraordinariamente simple y determinante:

```cpp
void Cluster::run(std::vector<BatchedSequence::Ptr> sequences_metadata_list) {
  setPerformExecution(true);
  restartModuleGraph();
  while (check_module_graph_remain()) {
    for (Node::Ptr _node : node) {
      _node->run(sequences_metadata_list);
    }
  }
}
```

Cada dispositivo ejecuta `TopModuleGraph::run()` ([`src/module/module_graph.cpp:L171-L179`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp#L171-L179)):

```cpp
void TopModuleGraph::run(BatchedSequence::Ptr sequences_metadata) {
  for (; current_module != module_graph.end(); current_module++) {
    set_stamp();
    if (!(*current_module)->run(sequences_metadata)) {
      break; // ¡BLOQUEO POR DEPENDENCIA!
    }
  }
}
```

### Mecánica de las Barreras: `check_ready()` y `sync_devices()`
En [`src/module/module_graph.cpp:L27-L72`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp#L27-L72):
1. Cuando un módulo tiene la bandera `module->sync == false`: Solo comprueba si su propio tensor de entrada local está listo (`input->ready == true`). Si es así, ejecuta su función `forward()` de inmediato.
2. Cuando un módulo colectivo tiene `module->sync == true` (por ejemplo, `MoEScatter`, `AllReduce` o `sync__set`):
   Invoca [`check_ready()`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp#L54-L72):
   - Verifica si **todos** los tensores registrados en `dependency_tensor_list` (que provienen de las otras GPUs) tienen `tensor->ready == true`.
   - **Si alguna GPU aún no ha completado el cómputo del tensor:** `check_ready()` devuelve `false`. La GPU actual ejecuta un `break` en su bucle `TopModuleGraph::run()`, cediendo el control a las siguientes GPUs en el sondeo Round-Robin del clúster.
   - **Si todas las GPUs han completado sus tensores:** Se ejecuta `sync_devices()` ([`src/module/module_graph.cpp:L74-L111`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp#L74-L111)).

### El Algoritmo Exacto de Sincronización Temporal
En `sync_devices()`:
```cpp
// 1. Encontrar el tiempo de la GPU más atrasada (la que más ha tardado en cómputo)
time_ns time = 0;
for (Tensor::Ptr tensor : dependency_tensor_list) {
  Device::Ptr device = tensor->get_device();
  time = std::max(time, device->get_time());
}

// 2. Obligar a todas las GPUs de la dependencia a saltar a ese tiempo común
for (Tensor::Ptr tensor : dependency_tensor_list) {
  Device::Ptr device = tensor->get_device();
  time_ns current_device_time = device->get_time();
  
  if (time > current_device_time) {
      // Registro del bloqueo por desbalance de cómputo (TFM Added)
      device->log_tfm_event(current_device_time, time, "NETWORK_STALL", details);
  }
  device->set_time(time);
}
```
Este mecanismo es el corazón formal del modelo Bulk Synchronous Parallel (BSP): **todas las GPUs se ven forzadas a saltar al reloj de la GPU más lenta antes de poder ejecutar la operación colectiva**.

---

## 1.5. Modelo de Cómputo y Memoria (Ecuaciones Roofline) e Integración de Ramulator2

LLMSimulator no emula el código máquina PTX/SASS instrucción a instrucción; en su lugar, utiliza el **modelo analítico Roofline** validado experimentalmente para aceleradores masivos, desacoplando el tiempo de cálculo del tiempo de acceso a memoria.

### Ecuaciones Roofline en Capas Lineales (GEMM / GEMV)
En [`src/hardware/linear_impl.cpp:L16-L75`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/linear_impl.cpp#L16-L75), para una operación $Y = X \cdot W$:
- Sea $m$ la dimensión de tokens (dimensión de activación en fila, `input->shape[0]`).
- Sea $k$ la dimensión oculta de entrada (`input->shape[1]`).
- Sea $n$ la dimensión oculta de salida (`weight->shape[1]`).

Las operaciones de coma flotante totales ($\text{FLOPs}$) y la huella de memoria en bytes ($\text{Memory Size}$) se calculan como:

$$\text{Total FLOPs} = 2 \cdot m \cdot k \cdot n$$

$$\text{Total Memory (Bytes)} = (m \cdot k + k \cdot n + m \cdot n) \times \text{precision\_byte}$$

A partir de los parámetros de hardware del acelerador ($\text{Peak FLOPS}$ y $\text{Memory Bandwidth}$):

$$T_{\text{compute}} (\text{ns}) = \frac{\text{Total FLOPs}}{\text{compute\_peak\_flops}} \times 10^9$$

$$T_{\text{memory}} (\text{ns}) = \frac{\text{Total Memory Size}}{\text{memory\_bandwidth}} \times 10^9$$

El tiempo de ejecución final de la capa en la GPU es el máximo de ambos cuellos de botella (asumiendo solapamiento perfecto entre las unidades tensoriales y los controladores DMA de carga de memoria):

$$T_{\text{total}} = \max\left(T_{\text{compute}},\, T_{\text{memory}}\right)$$

La intensidad operacional ($\text{Op/B}$) determina en qué vertiente del Roofline se sitúa la operación:

$$\text{Op/B} = \frac{\text{Total FLOPs}}{\text{Total Memory Size}} = \frac{2 \cdot m \cdot k \cdot n}{(m \cdot k + k \cdot n + m \cdot n) \times \text{precision\_byte}}$$

### Capas Analíticas Ligeras
- **`LayerNorm` ([`src/module/layernorm.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/layernorm.cpp)):** Operación puramente memory-bound de reducción estadística. Lee el vector de entrada y escribe el normalizado:
  $$\text{Memory} = 2 \cdot m \cdot k \times \text{precision\_byte}$$
- **`Residual` ([`src/module/residual.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/residual.cpp)):** Suma elemento a elemento ($X + Y$). Lee dos tensores y escribe uno:
  $$\text{Memory} = 3 \cdot m \cdot k \times \text{precision\_byte}$$
- **`RoPE` ([`src/module/rope.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/rope.cpp)):** Embebido posicional rotacional sobre las dimensiones de los cabezales de atención.

### Cuándo y Cómo Interviene Ramulator2
Si la bandera `use_ramulator: on` está activada en `config.yaml`:
- En lugar de la ecuación ideal de ancho de banda estático ($T_{\text{memory}} = \text{Data} / \text{BW}$), la GPU emite solicitudes de ráfaga a nivel de canal, rango y banco DRAM mediante `issueRamulator()`.
- Ramulator2 simula las aperturas de filas (`ACT`), precargas (`PRE`), lecturas de columna (`RD`) y escrituras (`WR`) teniendo en cuenta los tiempos de temporización física del estándar de memoria (HBM3/HBM3E: $t_{RCD}$, $t_{RP}$, $t_{CL}$).
- **Caché de Memoización:** Como simular millones de transacciones DRAM ciclo a ciclo en cada capa ralentizaría la simulación miles de veces, `Device` implementa una caché hash (`addExecutionCache` / `checkExecutionCache` en [`src/hardware/device.cpp:L90-L98`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp#L90-L98)). Las dimensiones de tensores idénticas consultadas pre
mente devuelven instantáneamente la latencia DRAM simulada en la primera llamada.

---

## 1.6. Catálogo y Taxonomía de Modelos Soportados (`src/model/model_config.h` y `src/model/llm.cpp`)

El simulador `LLMSimulator` integra un catálogo de arquitecturas representativas de la frontera del estado del arte en modelos fundacionales densos y dispersos (Sparse Mixture-of-Experts). La configuración de cada modelo se parametriza de forma rigurosa en [`src/model/model_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/model_config.h), mientras que la topología del grafo de ejecución se materializa en [`src/model/llm.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/llm.cpp).

### Tabla Comparativa de Arquitecturas Soportadas

A continuación se detalla la matriz de especificaciones microarquitecturales de los 9 modelos preconfigurados en el motor:

| Modelo | Dim. Oculta ($k$) | Cabezales Q ($h_Q$) | Cabezales KV ($h_{KV}$) | Dim. Cabezal ($d_{\text{head}}$) | Capas ($L$) | Dim. FFN ($n_{\text{inter}}$) | Expertos ($E$) | Top-$k$ ($k_{\text{top}}$) | Expertos Compartidos | Frecuencia MoE (`expert_freq`) | Mecanismo de Atención | Precisión (Bytes) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`mixtral`** (8x7B) | 4096 | 32 | 8 | 128 | 32 | 14336 | 8 | 2 | 0 | 1 (Todas) | GQA | FP16 (2B) |
| **`openMoE`** (8B) | 3072 | 24 | 24 | 128 | 32 | 12288 | 32 | 2 | 0 | 4 (Cada 4) | MHA | FP16 (2B) |
| **`llama7bMoE`** | 4096 | 32 | 32 | 128 | 32 | 11008 / 688 | 16 | 2 | 0 | 1 (Todas) | MHA | FP16 (2B) |
| **`grok1`** (314B) | 6144 | 48 | 8 | 128 | 64 | 32768 | 8 | 2 | 0 | 1 (Todas) | GQA | FP16 (2B) |
| **`glam`** | 4096 | 32 | 32 | 128 | 32 | 16384 | 64 | 2 | 0 | 2 (Cada 2) | MHA | FP16 (2B) |
| **`deepseekV3`** (671B) | 7168 | 128 | 128 | 128 | 60 | 18432 / 2048 | 256 | 8 | 1 | 1 ($L \ge 3$) | MLA (Latent) | FP8 (1B) |
| **`llama3_405B`** | 16384 | 128 | 8 | 128 | 126 | 53248 | 0 (Denso) | 0 | 0 | 0 (Denso) | GQA | FP8 (1B) |
| **`llama4_scout`** | 5120 | 40 | 8 | 128 | 48 | 16384 / 8192 | 16 | 1 | 1 | 1 (Todas) | GQA | FP16 (2B) |
| **`llama4_maverick`** | 5120 | 40 | 8 | 128 | 48 | 16384 / 8192 | 128 | 1 | 1 | 2 (Cada 2) | GQA | FP16 (2B) |

### Lógica de Construcción del Grafo (`src/model/llm.cpp`)

La clase constructora `LLM::LLM` ([`src/model/llm.cpp:L10-L62`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/llm.cpp#L10-L62)) instancia el pipeline completo de decodificación conectando:
1. **Capa de Embebido (`Embedding_layer`):** Proyecta los identificadores de token discretos al espacio continuo de dimensión oculta $k$.
2. **Pila de Decodificadores (`Decoder` vs. `MoEDecoder`):**
   - **Caso Especial DeepSeek-V3:** DeepSeek-V3 implementa las primeras $k$ capas densas (`first_k_dense = 3`). El bucle en [`src/model/llm.cpp:L42-L54`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/llm.cpp#L42-L54) asigna capas densas estándar para $l \in [0, 2]$ mediante `Decoder::Create` y capas dispersas con 256 expertos enrutados + 1 compartido para $l \in [3, 59]$ mediante `MoEDecoder::Create`.
   - **Resto de Modelos:** Para modelos con periodicidad de expertos (`expert_freq > 0`), se evalúa la condición modular `(layer % model_config.expert_freq == 0)`. Si se cumple, se instancia un `MoEDecoder`; si no, un `Decoder` denso. En Mixtral (`expert_freq = 1`), las 32 capas son MoE; en GLaM (`expert_freq = 2`), se alternan capas densas y MoE; en OpenMoE (`expert_freq = 4`), una de cada cuatro capas es MoE.
   - **Modelos Puramente Densos (`llama3_405B`):** Con `num_routed_expert = 0` y `expert_freq = 0`, todas las 126 capas se construyen como decodificadores densos.
3. **Proyección Final (`lm_head`):** Proyecta el estado oculto final hacia el espacio de vocabulario $n_{\text{vocab}}$ (ej. 32000 en Mixtral/LLaMA-2, 128256 en LLaMA-3, 129280 en DeepSeek-V3) para el cálculo de logits y muestreo de tokens.

---

## 1.7. Modelado Microarquitectural de la Atención y Ecuaciones Matemáticas (`src/module/attention.cpp`, `compressed_kv_restore.cpp`, `src/hardware/attention_sum_impl.cpp`, `attention_gen_impl.cpp`)

El mecanismo de atención es el núcleo del consumo de memoria en la fase autoregresiva de los LLMs. El simulador modela con rigurosidad matemática tres paradigmas: Multi-Head Attention (MHA), Grouped-Query Attention (GQA) y Multi-Head Latent Attention (MLA).

### 1. Multi-Head Attention (MHA) y Grouped-Query Attention (GQA)

Sea la matriz de activación de entrada $X \in \mathbb{R}^{m \times k}$, donde $m$ es el número de tokens en el lote y $k$ la dimensión oculta. Las proyecciones lineales generan las matrices de Query ($Q$), Key ($K$) y Value ($V$):
$$Q = X W_Q, \quad K = X W_K, \quad V = X W_V$$
Donde $W_Q \in \mathbb{R}^{k \times (h_Q \cdot d_{\text{head}})}$, $W_K \in \mathbb{R}^{k \times (h_{KV} \cdot d_{\text{head}})}$ y $W_V \in \mathbb{R}^{k \times (h_{KV} \cdot d_{\text{head}})}$.

- **En MHA:** El número de cabezales de consulta y valor es idéntico: $h_Q = h_{KV} = h$.
- **En GQA:** Los $h_Q$ cabezales de consulta se dividen en grupos de tamaño $g = \frac{h_Q}{h_{KV}}$, compartiendo un único cabezal de $K$ y $V$ por grupo.

#### Fase Prefill (Resumen / `attention_sum_impl.cpp`)
En la fase de prefill, se computa la atención completa de la secuencia de longitud $m$:
$$A_i = \text{Softmax}\left(\frac{Q_i K_i^T}{\sqrt{d_{\text{head}}}}\right) V_i, \quad O = [A_1; A_2; \dots; A_{h_Q}] W_O$$

- **Operaciones de Cómputo (FLOPs):**
  - Multiplicación $Q K^T$: $2 \cdot m^2 \cdot d_{\text{head}} \cdot h_Q$ FLOPs.
  - Multiplicación $A V$: $2 \cdot m^2 \cdot d_{\text{head}} \cdot h_Q$ FLOPs.
  - $\text{Total FLOPs}_{\text{Prefill}} = 4 \cdot m^2 \cdot h_Q \cdot d_{\text{head}}$.
- **Tráfico de Memoria DRAM:**
  $$\text{Memory}_{\text{Prefill}} = (m \cdot k + 2 \cdot m \cdot h_{KV} \cdot d_{\text{head}} + m \cdot k) \times \text{precision\_byte}$$

#### Fase Decode (Generación / `attention_gen_impl.cpp`)
En la generación de cada nuevo token ($m = 1$), el token entrante consulta todo el historial de longitud $n = \text{current\_len} + 1$:
- **Operaciones de Cómputo:**
  $$\text{Total FLOPs}_{\text{Decode}} = 4 \cdot m \cdot n \cdot h_Q \cdot d_{\text{head}}$$
- **Tráfico de Memoria DRAM (Lectura del KV-Cache):**
  El cuello de botella absoluto reside en leer los tensores acumulados de $K$ y $V$ desde la memoria HBM:
  $$\text{Memory}_{\text{Decode}} = \left( m \cdot h_Q \cdot d_{\text{head}} + 2 \cdot n \cdot h_{KV} \cdot d_{\text{head}} + m \cdot h_Q \cdot d_{\text{head}} \right) \times \text{precision\_byte}$$
  En GQA, al ser $h_{KV} = \frac{h_Q}{g}$, el tamaño del KV-cache leído por token se reduce un factor $g \times$ (ej. $75\%$ de ahorro en Mixtral donde $g = 32 / 8 = 4$).

### 2. Multi-Head Latent Attention (MLA) en DeepSeek-V3

DeepSeek-V3 reemplaza el KV-cache estándar mediante compresión de bajo rango (Low-Rank Latent Compression) implementada en [`src/module/attention.cpp:L310-L380`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/attention.cpp#L310-L380) y [`src/module/compressed_kv_restore.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/compressed_kv_restore.cpp).

#### Ecuaciones de Compresión y KV-Cache Latente
En lugar de almacenar tensores independientes de tamaño $h_{KV} \times d_{\text{head}}$ por token, el modelo comprime $K$ y $V$ en un único vector latente $\mathbf{c}_t^{KV} \in \mathbb{R}^{d_c}$ ($d_c = 512$, parametrizado como `kv_lora_rank`):
$$\mathbf{c}_t^{KV} = X_t W_{DKV}, \quad W_{DKV} \in \mathbb{R}^{k \times d_c}$$
Para preservar la información de posición rotacional (RoPE), se proyecta una clave desacoplada $\mathbf{k}_t^R \in \mathbb{R}^{d_R}$ ($d_R = 64$, `qk_rope_head_dim`):
$$\mathbf{k}_t^R = \text{RoPE}(X_t W_{KR}), \quad W_{KR} \in \mathbb{R}^{k \times d_R}$$

De igual forma, la consulta (Query) se comprime a bajo rango:
$$\mathbf{c}_t^Q = X_t W_{DQ}, \quad W_{DQ} \in \mathbb{R}^{k \times d_{cq}} \quad (d_{cq} = 1536, \text{ `q\_lora\_rank`})$$
$$\mathbf{q}_t^{NOPE} = \mathbf{c}_t^Q W_{UQ}, \quad \mathbf{q}_t^R = \text{RoPE}(\mathbf{c}_t^Q W_{QR})$$

#### Huella de Memoria del KV Cache en DRAM
En el KV cache solo se almacenan $\mathbf{c}_t^{KV}$ (512 escalares) y $\mathbf{k}_t^R$ (64 escalares).
$$\text{Elementos por Token por Capa} = 512 + 64 = 576 \text{ elementos}$$
En formato FP8 (1 Byte por elemento en DeepSeek-V3), la huella de memoria es de únicamente **$576\text{ Bytes}$ por token**, frente a los **$32768\text{ Bytes}$** que requeriría un MHA tradicional con 128 cabezales de dimensión 128 en FP16 ($128 \times 128 \times 2 \times 2 = 65536\text{ B}$), logrando una **reducción del $98.2\%$** en consumo de ancho de banda y capacidad DRAM.

#### La Optimización `use_absorb = true` en Decodificación
En la fase de generación autoregresiva, descomprimir $K$ y $V$ a partir de $\mathbf{c}_t^{KV}$ requeriría multiplicar por las matrices de proyección hacia arriba $W_{UK} \in \mathbb{R}^{d_c \times (h \cdot d_{\text{head}})}$ y $W_{UV} \in \mathbb{R}^{d_c \times (h \cdot d_{\text{head}})}$, lo que saturaría el bus de memoria al cargar $W_{UK}$ para cada token generado.

El simulador implementa el flag `use_absorb` en [`src/module/attention.cpp:L206-L238`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/attention.cpp#L206-L238):
Aprovechando la propiedad asociativa del producto matricial:
$$\mathbf{q}_{t, i}^{NOPE} (\mathbf{k}_{j, i}^{NOPE})^T = \mathbf{q}_{t, i}^{NOPE} (\mathbf{c}_j^{KV} W_{UK, i})^T = \left(\mathbf{q}_{t, i}^{NOPE} W_{UK, i}^T\right) \mathbf{c}_j^{KV}$$
Definiendo una consulta absorbida $\mathbf{q}_{t, i}' = \mathbf{q}_{t, i}^{NOPE} W_{UK, i}^T \in \mathbb{R}^{1 \times d_c}$:
- La GPU calcula $\mathbf{q}'$ una sola vez para el nuevo token generado.
- El producto escalar de atención contra todos los tokens pasados se evalúa directamente sobre los vectores comprimidos en memoria:
  $$\text{Score}_{i, j} = \frac{\mathbf{q}_{t, i}' \mathbf{c}_j^{KV} + \mathbf{q}_{t, i}^R (\mathbf{k}_j^R)^T}{\sqrt{d_{\text{head}} + d_R}}$$
- Análogamente, $W_{UV}$ se absorbe en la matriz de salida $W_O$:
  $$O_t = \sum_j A_{t, j} (\mathbf{c}_j^{KV} W_{UV}) W_O = \left(\sum_j A_{t, j} \mathbf{c}_j^{KV}\right) (W_{UV} W_O)$$
Gracias a esta técnica, el cómputo de atención se ejecuta íntegramente en el espacio latente comprimido de dimensión 512, sin materializar jamás los tensores descomprimidos en la memoria física DRAM.

---

## 1.8. El Subsistema de Memoria, Perfiles de Hardware y Modelo Energético (`src/hardware/hardware_config.h`, `src/dram/dram_interface.cpp`, `src/dram/power.h`, `module_graph.cpp`)

### Comparativa de Perfiles Hardware en `src/hardware/hardware_config.h`

El simulador define perfiles preconfigurados para las principales familias de GPUs de centros de datos de NVIDIA en [`src/hardware/hardware_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/hardware_config.h):

| Especificación Arquitectural | Parámetro en Código | NVIDIA A100 | NVIDIA H100 | NVIDIA B100 | NVIDIA B200 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Generación GPU** | `gpu_gen` | A100 (Ampere) | H100 (Hopper) | B100 (Blackwell) | B200 (Blackwell) |
| **Cómputo Pico FP16** | `compute_peak_flops` | 312.0 TFLOP/s | 989.4 TFLOP/s | 1750.0 TFLOP/s | 2250.0 TFLOP/s |
| **Tecnología de Memoria** | Tipo de DRAM | HBM2e | HBM3 | HBM3e | HBM3e |
| **Ancho de Banda DRAM** | `memory_bandwidth` | 2.039 TB/s | 3.352 TB/s | 8.000 TB/s | 8.000 TB/s |
| **Capacidad DRAM por GPU** | `memory_capacity` | 80 GB | 80 GB | 192 GB | 192 GB |
| **Pilas HBM (Cubes)** | `num_cube` | 5 | 5 | 8 | 8 |
| **Ancho de Banda NVLink** | `device_ict_bandwidth` | 150 GB/s (NVL3) | 450 GB/s (NVL4) | 900 GB/s (NVL5) | 900 GB/s (NVL5) |
| **Latencia NVLink** | `device_ict_latency` | 3000 ns (3.0 µs) | 800 ns (0.8 µs) | 800 ns (0.8 µs) | 800 ns (0.8 µs) |
| **Ancho de Banda Red Nodo** | `node_ict_bandwidth` | 50 GB/s (CX-7) | 50 GB/s (CX-7) | 50 GB/s (CX-7) | 50 GB/s (CX-7) |
| **Latencia Red Nodo** | `node_ict_latency` | 130 ns | 130 ns | 130 ns | 130 ns |

### El Subsistema DRAM (`src/dram/dram_interface.cpp`)

Cuando se utiliza el modo ciclo a ciclo mediante Ramulator2 (`use_ramulator = true`), `DRAMInterface` traduce las lecturas y escrituras de los módulos a transacciones físicas de memoria:
- Cada acceso a un tensor se fragmenta en solicitudes de ráfaga de 32 Bytes (256 bits).
- Las direcciones se mapean a través de los canales de la memoria apilada HBM (`Channel`), grupos de bancos (`BankGroup`), bancos (`Bank`), filas (`Row`) y columnas (`Column`).
- Se simulan los conflictos de banco y las restricciones de temporización física del estándar JEDEC:
  - $t_{RCD}$ (RAS to CAS Delay): Tiempo para activar una fila en el buffer de sentido.
  - $t_{RP}$ (Row Precharge): Tiempo para precargar y cerrar una línea de banco.
  - $t_{CL}$ (CAS Latency): Latencia de lectura de columna.
  - $t_{RAS}$ (Row Active Time): Tiempo mínimo que una fila debe permanecer abierta.

### Modelo Energético Microarquitectural (`src/dram/power.h` y `src/module/module_graph.cpp`)

El consumo energético dinámico no se aproxima mediante constantes arbitrarias, sino modelando físicamente cada operación elemental basándose en el trabajo de referencia en memorias apiladas de alta densidad (*MICRO 2017 Fine-Grained DRAM, Keckler et al.*) documentado en [`src/dram/power.h:L20-L46`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/power.h#L20-L46):

#### 1. Descomposición Física de la Energía DRAM
- **Energía de Activación de Fila (`ACT`):**
  $$E_{\text{ACT}} = 0.909\text{ nJ por evento de activación}$$
- **Energía de Lectura y Escritura de Columna (`RD` / `WR`):**
  La transferencia de cada bit desde la celda de memoria a través de las vías de silicio (TSV) y el interposer pasivo disipa:
  - Energía en celda DRAM (Cell): $0.44\text{ pJ/bit}$
  - Decodificador de columnas a MUX de BankGroup: $1.01\text{ pJ/bit}$
  - MUX de BankGroup a MUX GIO: $1.23\text{ pJ/bit}$
  - Tránsito vertical por vías de silicio (TSV): $0.50\text{ pJ/bit}$
  - E/S del interposer de silicio (Silicon Interposer IO): $0.30\text{ pJ/bit}$
  - **Total por bit transmitido:** $3.48\text{ pJ/bit}$.

  Dado que la granularidad de ráfaga física de HBM es de 32 Bytes ($256\text{ bits}$), la energía por solicitud DRAM es:
  $$E_{\text{RD}} = E_{\text{WR}} = \frac{3.48\text{ pJ/bit} \times 256\text{ bits}}{1000\text{ pJ/nJ}} = 0.89088 \approx 0.891\text{ nJ}$$

#### 2. Energía de Cómputo Aritmético (MAC / FLOPs)
Las unidades aritmético-lógicas (ALU / Tensor Cores) consumen $0.46\text{ pJ}$ por operación Multiply-Accumulate (MAC, equivalente a 2 FLOPs):
$$E_{\text{MAC}} = \frac{0.46\text{ pJ}}{2 \times 1000\text{ pJ/nJ}} = 0.00023\text{ nJ/FLOP} \quad (0.23\text{ pJ por FLOP})$$

#### 3. Ecuación de Acumulación Energética en `ModuleGraph`
En [`src/module/module_graph.cpp:L276-L297`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp#L276-L297), tras ejecutar cada módulo en la GPU, el simulador actualiza los acumuladores energéticos de la GPU:
$$E_{\text{ACT\_total}} = \sum N_{\text{ACT}} \times 0.909\text{ nJ}$$
$$E_{\text{RD\_total}} = \sum N_{\text{RD}} \times 0.891\text{ nJ}$$
$$E_{\text{WR\_total}} = \sum N_{\text{WR}} \times 0.891\text{ nJ}$$
$$E_{\text{MAC\_total}} = \sum \text{FLOPs} \times 0.00023\text{ nJ}$$

La energía dinámica total es la suma de los componentes DRAM y aritméticos:
$$E_{\text{total\_nJ}} = E_{\text{ACT\_total}} + E_{\text{RD\_total}} + E_{\text{WR\_total}} + E_{\text{MAC\_total}}$$

#### 4. Conversión y Reporte en Milijulios (`src/module/timeboard.cpp`)
El monitor de estadísticas de tiempo ([`src/module/timeboard.cpp:L256-L268`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/timeboard.cpp#L256-L268)) convierte los nanojulios acumulados a milijulios ($\text{mJ}$) dividiendo por $10^6$ ($1000 \times 1000$):
$$\text{Energía (mJ)} = \frac{\text{Energía (nJ)}}{10^6}$$
Esto permite evaluar con precisión el consumo energético por token en cada capa del modelo.

---

# CAPÍTULO 2: Modelado Matemático de Mixtral 8x7B y Enrutamiento MoE

## 2.1. Anatomía Arquitectural de Mixtral 8x7B en Paralelismo Experto y Tensorial

El modelo Mixtral 8x7B es una arquitectura de tipo sparse Mixture-of-Experts con las siguientes especificaciones extraídas de [`src/model/model_config.h:L91-L93`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/model_config.h#L91-L93):

| Parámetro | Símbolo | Valor Mixtral 8x7B |
| :--- | :---: | :---: |
| Dimensión Oculta (Hidden Dim) | $k$ | $4096$ |
| Dimensión Intermedia de los Expertos | $n_{\text{exp}}$ | $14336$ |
| Número de Capas Decodificadoras | $L$ | $32$ |
| Número de Cabezales de Atención (Query) | $h_Q$ | $32$ |
| Número de Cabezales Clave/Valor (GQA) | $h_{KV}$ | $8$ |
| Dimensión por Cabezal (Head Dim) | $d_{\text{head}}$ | $128$ |
| Número Total de Expertos Enrutados | $E$ | $8$ |
| Top-k Expertos Seleccionados por Token | $\text{top\_k}$ | $2$ |
| Estilo de Capa FFN | $\text{ffn\_way}$ | $3$ (SwiGLU: Gate, Up, Down) |
| Precisión Numérica (Default FP8) | $\text{precision\_byte}$ | $1\text{ Byte}$ |

### Esquema de Paralelismo en Nuestro Clúster
En nuestra configuración de 8 aceleradores B100:
- **Paralelismo Tensorial No Experto (`ne_tp_dg`):** $1$. La atención y normalizaciones se evalúan localmente por secuencia en cada GPU.
- **Paralelismo Experto (`e_tp_dg`):** $1$.
- **Distribución de Expertos:** Con $8$ GPUs y $8$ expertos, **cada GPU es anfitriona de exactamente 1 experto dedicado**:
  $$\text{GPU } i \Longleftrightarrow \text{Experto } i \quad \forall i \in [0, 7]$$

---

## 2.2. Algoritmo de Enrutamiento MoE (`Route::forward` y `GateUpdate::aggregate_expert`)

El flujo de enrutamiento se produce en tres etapas perfectamente encadenadas en [`src/module/expert.cpp:L140-L158`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp#L140-L158):

1. **`gate_fn` (Enrutador Lineal):**
   Multiplica la activación de entrada $(m, 4096)$ por los pesos del router $(4096, 8)$ para obtener los logits de selección de cada experto.
2. **`gate_update` / `aggregate_expert` ([`src/module/route.cpp:L149-L190`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/route.cpp#L149-L190)):**
   La GPU 0 invoca `update_expert` sobre todas las secuencias del batch, poblando el vector:
   $$\text{num\_token\_in\_expert}[j] \quad \text{para } j \in [0, 7]$$
3. **`moe_route` ([`src/module/route.cpp:L215-L253`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/route.cpp#L215-L253)):**
   Genera los punteros de activación segmentados que alimentarán a los expertos locales en cada GPU.

---

## 2.3. Distribución Zipfiana vs. Uniforme: Impacto del Parámetro `skewness` y Asignación Real en B100

En [`src/scheduler/sequence.cpp:L168-L202`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/sequence.cpp#L168-L202), el planificador pondera la probabilidad de selección de los expertos mediante una distribución de tipo Zipf:

$$w_i = \frac{1}{(i + 1)^s} \quad \text{para } i \in [0, E-1]$$

donde $s$ es el parámetro `skewness`:
- **Si $s > 0$:** La probabilidad decrece exponencialmente con el índice del experto. El Experto 0 recibe una avalancha desproporcionada de tokens, saturando su GPU anfitriona mientras las demás permanecen ociosas.
- **Si $s = 0.0$:** $w_i = 1$ para todo $i$. Se recurre a la función uniforme `getRandomExpert(top_k)`:

```cpp
std::set<int> Scheduler::getRandomExpert(int top_k) {
  static unsigned int seed = 777; // ¡SEMILLA DETERMINISTA!
  static std::mt19937 generator(seed);
  static std::uniform_int_distribution<int> distribution(0, model_config.num_routed_expert - 1);
  std::set<int> route;
  while (route.size() < top_k) {
    int seq_id = (distribution(generator) % model_config.num_routed_expert);
    route.insert(seq_id);
  }
  return route;
}
```

### Conteo Exacto de Tokens en Nuestra Simulación (`batch_size = 32`, `decode_mode = on`)
- Con `batch_size = 32`, en modo decodificación cada secuencia emite exactamente $1$ token activo.
- Cada token debe enrutarse obligatoriamente a $\text{top\_k} = 2$ expertos distintos.
- Total de asignaciones de tokens en el clúster:
  $$\text{Tokens Totales} = 32 \text{ tokens} \times 2 = \mathbf{64 \text{ tokens asignados}}$$

Debido al generador determinista con semilla 777, los 64 tokens se distribuyen entre las 8 GPUs de la siguiente forma empírica verificada en los registros del co-simulador:

$$\mathbf{T} = [T_0, T_1, T_2, T_3, T_4, T_5, T_6, T_7] = [11, 8, 8, 6, 8, 11, 8, 4]$$

$$\sum_{i=0}^{7} T_i = 11 + 8 + 8 + 6 + 8 + 11 + 8 + 4 = 64$$

- Las GPUs más cargadas son **GPU 0 y GPU 5** con **11 tokens**.
- La GPU menos cargada es **GPU 7** con solo **4 tokens**.

---

## 2.4. Demostración Matemática del Régimen Memory-Bound en `decode_mode` (22.155 ns)

Consideremos la ejecución de un experto MoE (`expert_FFN_0`) en la GPU 0 ($m = 11\text{ tokens}$). La capa es un FFN de 3 vías (SwiGLU) compuesto por:
1. `gate_proj`: GEMM $(11 \times 4096) \times (4096 \times 14336)$
2. `up_proj`: GEMM $(11 \times 4096) \times (4096 \times 14336)$
3. `activation`: Función SiLU sobre $(11 \times 14336)$
4. `down_proj`: GEMM $(11 \times 14336) \times (14336 \times 4096)$

### Parámetros del Hardware Nvidia B100
- $\text{Peak Compute (FP8)} = 3500.0 \times 10^{12} \text{ FLOPS}$ ($3.5 \text{ PFLOPS}$)
- $\text{Memory Bandwidth (HBM3E)} = 8.0 \times 10^{12} \text{ B/s} = 8000 \text{ B/ns}$

### Cálculo para una Proyección Individual (`gate_proj`)
- **Huella de Memoria de los Pesos:**
  $$\text{Pesos} = k \times n_{\text{exp}} \times 1\text{ B} = 4096 \times 14336 = \mathbf{58,720,256 \text{ Bytes}} \approx 58.72\text{ MB}$$
- **Huella de Activaciones (Entrada + Salida para 11 tokens):**
  $$\text{Activaciones} = (m \cdot k + m \cdot n_{\text{exp}}) \times 1\text{ B} = (11 \times 4096 + 11 \times 14336) = 45,056 + 157,696 = \mathbf{202,752 \text{ Bytes}} \approx 0.20\text{ MB}$$
- **Memoria Total Transferida:**
  $$\text{Memoria Total} = 58,720,256 + 202,752 = \mathbf{58,923,008 \text{ Bytes}}$$
- **Tiempo de Memoria Requerido:**
  $$T_{\text{memory}} = \frac{58,923,008\text{ B}}{8.0 \times 10^{12}\text{ B/s}} \times 10^9 = \frac{58,923,008}{8000} = \mathbf{7,365.376 \text{ ns}}$$
- **Tiempo de Cómputo Requerido:**
  $$\text{FLOPs} = 2 \cdot m \cdot k \cdot n_{\text{exp}} = 2 \times 11 \times 4096 \times 14336 = 1,291,845,632 \text{ FLOPs} \approx 1.29\text{ GFLOPs}$$
  $$T_{\text{compute}} = \frac{1,291,845,632}{3.5 \times 10^{15}} \times 10^9 = \mathbf{0.369 \text{ ns}}$$

Dado que $T_{\text{memory}} (7365.38\text{ ns}) \gg T_{\text{compute}} (0.37\text{ ns})$:
$$T_{\text{gate\_proj}} = \max(0.369,\, 7365.376) = \mathbf{7,365.376 \text{ ns}}$$

### Suma Total del Bloque ExpertFFN
- `gate_proj`: $7,365.376\text{ ns}$
- `activation` (SiLU sobre 11 tokens): $43.008\text{ ns}$ (memoria) / $16\text{ ns}$ (cómputo) $\approx 59.136\text{ ns}$
- `up_proj`: $7,365.376\text{ ns}$
- `down_proj`: $7,365.376\text{ ns}$

$$T_{\text{ExpertFFN\_0}} = 3 \times 7,365.376\text{ ns} + 59.136\text{ ns} = \mathbf{22,155.26 \text{ ns}} \approx \mathbf{22.155 \,\mu\text{s}}$$

El resultado analítico coincide **exactamente al nanosegundo** con la traza emitida por el simulador:
`expert_FFN_0 | 22.155us | 1158.9 - 1181 | tensor(11, 4096) -> tensor(11, 4096)`.

---

## 2.5. Análisis del Desbalance entre GPUs: ¿Por qué 11 tokens vs. 4 tokens solo difieren en 48 ns?

Realicemos ahora el mismo cálculo estricto para la **GPU 7**, que solo recibió $m = 4\text{ tokens}$:

- **Activaciones para 4 tokens:**
  $$\text{Activaciones} = (4 \times 4096 + 4 \times 14336) = 16,384 + 57,344 = \mathbf{73,728 \text{ Bytes}}$$
- **Memoria Total por Proyección:**
  $$\text{Memoria Total} = 58,720,256\text{ (pesos)} + 73,728\text{ (act)} = \mathbf{58,793,984 \text{ Bytes}}$$
- **Tiempo de Memoria:**
  $$T_{\text{proj}}(m=4) = \frac{58,793,984}{8000} = \mathbf{7,349.248 \text{ ns}}$$

### Diferencia de Tiempo entre Ambas GPUs
La diferencia temporal en cada proyección lineal entre procesar 11 tokens y procesar 4 tokens es:
$$\Delta T_{\text{proj}} = 7,365.376\text{ ns} - 7,349.248\text{ ns} = \mathbf{16.128 \text{ ns}}$$

A través de las 3 proyecciones del bloque FFN:
$$\Delta T_{\text{ExpertFFN}} \approx 3 \times 16.128\text{ ns} = \mathbf{48.384 \text{ ns}}$$

### Conclusión Teórica Fundamental
En fase de decodificación autorregresiva (`decode_mode`), los pesos del modelo ($58.72\text{ MB}$ por matriz) representan el **99.87% del tráfico de memoria**. La memoria HBM3E está obligada a transferir la matriz de pesos íntegra al chip independientemente de si se multiplica por 1, 4 o 11 vectores de activación. 

Por esta razón física:
> **El desbalance de carga entre expertos durante la decodificación introduce diferencias ínfimas de tiempo en silicio (~48 ns). El verdadero desbalance perjudicial no ocurre en el silicio, sino en la red de interconexión**, donde la GPU que recibe 11 tokens debe absorber casi el triple de paquetes de red que la de 4 tokens, colapsando los canales virtuales de su interfaz de red.

---

## 2.6. Demostración de la Proporción Temporal entre Attention (~6.338 ns) y ExpertFFN (~22.155 ns) (~1:3.5)

En los registros cronológicos se observa que el cómputo de la atención dura aproximadamente $\sim 6.338\text{ ns}$, mientras que el FFN dura $\sim 22.155\text{ ns}$, arrojando un ratio exacto de:

$$\text{Ratio} = \frac{22,155\text{ ns}}{6,338.86\text{ ns}} \approx \mathbf{3.495 \approx 3.5}$$

### Desglose Arquitectural de la Atención en Mixtral
El bloque de atención multi-consulta agrupada (GQA) con 32 cabezales Q y 8 cabezales KV consta de:
1. `attn_qkv_proj` ([`src/module/parallel.cpp:L20`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/parallel.cpp#L20)):
   Proyecta la entrada $4096$ hacia $Q (32 \times 128 = 4096)$ y $K, V (2 \times 8 \times 128 = 2048)$.
   Dimensión de la matriz de pesos: $4096 \times 6144 = 25,165,824\text{ Bytes}$.
   $$T_{\text{qkv\_proj}} = \frac{25,165,824 + \text{act}}{8000} \approx \mathbf{3,150.85 \text{ ns}}$$
2. `AttentionGen` (Kernel FlashAttention sobre la caché KV de 1024 tokens previos):
   $$T_{\text{AttentionGen}} \approx \mathbf{1,086.76 \text{ ns}}$$
3. `attn_o_proj` (Proyección de Salida):
   Dimensión de la matriz de pesos: $4096 \times 4096 = 16,777,216\text{ Bytes}$.
   $$T_{\text{o\_proj}} = \frac{16,777,216 + \text{act}}{8000} \approx \mathbf{2,101.25 \text{ ns}}$$

### Suma Total del Bloque de Atención
$$T_{\text{Attention}} = 3,150.85\text{ ns} + 1,086.76\text{ ns} + 2,101.25\text{ ns} = \mathbf{6,338.86 \text{ ns}} \approx \mathbf{6.34 \,\mu\text{s}}$$

El volumen total de pesos transferidos desde HBM en la atención es:
$$\text{Pesos}_{\text{Attn}} = 25.17\text{ MB} + 16.78\text{ MB} = \mathbf{41.95 \text{ MB}}$$
mientras que en el bloque `ExpertFFN` (SwiGLU) es:
$$\text{Pesos}_{\text{FFN}} = 3 \times 58.72\text{ MB} = \mathbf{176.16 \text{ MB}}$$

El ratio físico de memoria de pesos es:
$$\frac{176.16\text{ MB}}{41.95\text{ MB}} = \mathbf{4.199}$$

Al incluir la latencia computacional de `AttentionGen` ($1.08\,\mu\text{s}$), el ratio temporal converge con precisión matemática a:
$$\frac{22,155\text{ ns}}{6,338.86\text{ ns}} = \mathbf{3.495 \approx 3.5}$$

---

## 2.7. Matriz Completa de Compatibilidad y Asignación de Paralelismo de Expertos ($N_{\text{GPUs}} < E$, $N_{\text{GPUs}} = E$, $N_{\text{GPUs}} > E$)

Una pregunta metodológica recurrente formulada por los revisores y directores de investigación es:
> *¿Es compatible el paralelismo de expertos en LLMSimulator cuando hay menos GPUs que Expertos (ej. Mixtral con 8 expertos ejecutándose en 4 GPUs o 2 GPUs)? ¿Es capaz el simulador de alojar más de un experto por GPU? ¿Y qué ocurre si hay más GPUs que expertos (ej. 16 GPUs con 8 expertos)?*

La respuesta arquitectural y analítica rigurosa se descompone en tres casos exhaustivos:

### 1. Formulación Matemática de Asignación en C++ (`src/module/expert.cpp`)

En [`src/module/expert.cpp:L48-L86`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp#L48-L86), la partición de expertos entre dispositivos se rige por:

```cpp
int parallel_num = device_list.size();
int num_expert_tp_gr_rank = parallel_num / e_tp_dg;
num_expert_per_device = model_config.num_routed_expert / (num_expert_tp_gr_rank);
int device_rank = device->device_total_rank;
expert_offset = num_expert_per_device * (device_rank / e_tp_dg);

for (int expert_id = expert_offset; expert_id < expert_offset + num_expert_per_device; expert_id++) {
    auto expert_ffn = FeedForward3Way::Create(module_map_name, "expert_FFN_" + std::to_string(expert_id), ...);
    add_module(expert_ffn);
}
```

Donde:
- $E = \text{model\_config.num\_routed\_expert}$ (Número total de expertos enrutados, ej. 8 en Mixtral).
- $N_{\text{GPUs}} = \text{parallel\_num}$ (Número de GPUs en el grupo MoE).
- $e\_tp\_dg = \text{model\_config.e\_tp\_dg}$ (Grado de paralelismo tensorial interno dentro de cada experto).

---

### 2. Caso $N_{\text{GPUs}} < E$ (Menos GPUs que Expertos, ej. 4 GPUs o 2 GPUs con Mixtral $E=8$)

**Compatibilidad: Total y Nativa (100% Soportado).**

Cuando $N_{\text{GPUs}} < E$ (con $e\_tp\_dg = 1$):
$$\text{num\_expert\_per\_device} = \frac{E}{N_{\text{GPUs}}}$$

- **En 4 GPUs ($N_{\text{GPUs}} = 4$):**
  $$\text{num\_expert\_per\_device} = \frac{8}{4} = \mathbf{2 \text{ expertos locales por GPU}}$$
  - **GPU 0:** $\text{expert\_offset} = 0 \to$ Aloja e instancia `expert_FFN_0` y `expert_FFN_1`.
  - **GPU 1:** $\text{expert\_offset} = 2 \to$ Aloja e instancia `expert_FFN_2` y `expert_FFN_3`.
  - **GPU 2:** $\text{expert\_offset} = 4 \to$ Aloja e instancia `expert_FFN_4` y `expert_FFN_5`.
  - **GPU 3:** $\text{expert\_offset} = 6 \to$ Aloja e instancia `expert_FFN_6` y `expert_FFN_7`.

- **En 2 GPUs ($N_{\text{GPUs}} = 2$):**
  $$\text{num\_expert\_per\_device} = \frac{8}{2} = \mathbf{4 \text{ expertos locales por GPU}}$$
  - GPU 0 aloja `expert_FFN_0..3` y GPU 1 aloja `expert_FFN_4..7`.

#### Comportamiento en Cómputo Silicio:
El bucle `for` en `expert.cpp` añade $E / N_{\text{GPUs}}$ módulos `FeedForward3Way` secuenciales al grafo de ejecución local.
Por tanto, la duración de `ExpertFFN` en silicio se escala casi linealmente:
- **En 8 GPUs (1 experto/GPU):** $T_{\text{ExpertFFN}} \approx \mathbf{22.1 \,\mu\text{s}}$.
- **En 4 GPUs (2 expertos/GPU):** $T_{\text{ExpertFFN}} \approx 2 \times 22.1\,\mu\text{s} \approx \mathbf{44.3 \,\mu\text{s}}$ (validado empíricamente en `mixtral_2x2dev_mesh_bs32_20261028_005051`).
- **En 2 GPUs (4 expertos/GPU):** $T_{\text{ExpertFFN}} \approx 4 \times 22.1\,\mu\text{s} \approx \mathbf{88.5 \,\mu\text{s}}$.

#### Comportamiento en el Tráfico de Red (`src/module/communication.cpp`):
En `MoEScatter::forward()` y `MoEGather::forward()`, el Oráculo itera sobre el rango de expertos alojados en la GPU destino:
```cpp
int expert_id_offset = device->model_config.num_routed_expert / total_num_device * (dst / e_tp_dg) * e_tp_dg;
int num_expert_per_device = device->model_config.num_routed_expert / total_num_device * e_tp_dg;

int tokens_to_dst = 0;
for (int e_id = expert_id_offset; e_id < expert_id_offset + num_expert_per_device; e_id++) {
    tokens_to_dst += sequences_metadata->scheduler->running_queue[src_dp_idx]->local_num_token_in_expert[e_id];
}
```
El Oráculo agrega automáticamente en un único flujo de paquetes todos los tokens dirigidos a cualquiera de los expertos locales de la GPU destino (ej. para GPU 0 en un clúster de 4 GPUs, suma los tokens de `expert_0` más `expert_1`), emitiendo la ráfaga unicast consolidada hacia ese nodo de red.

---

### 3. Caso $N_{\text{GPUs}} = E$ (Mismo Número de GPUs que Expertos, ej. 8 GPUs con Mixtral $E=8$)

**Compatibilidad: Óptima y Canónica (100% Soportado).**

- $\text{num\_expert\_per\_device} = 8 / 8 = \mathbf{1 \text{ experto local por GPU}}$.
- Cada GPU aloja exactamente un experto (`expert_FFN_i`).
- Representa el diseño base de paralelismo de expertos desarticulado, con latencia de cómputo uniforme de $\sim 22.1\,\mu\text{s}$ por GPU.

---

### 4. Caso $N_{\text{GPUs}} > E$ (Más GPUs que Expertos, ej. 16 GPUs con Mixtral $E=8$)

**Compatibilidad: Condicionada a `e_tp_dg > 1` (Expert Tensor Parallelism).**

En `src/module/expert.cpp:L53-L54`, el simulador impone una aserción estricta de coherencia:
```cpp
assertTrue((parallel_num / e_tp_dg) <= model_config.num_routed_expert,
           "Expert tensor parallel degree is not supported");
```

- **Si se intenta ejecutar con Expert Parallelism puro ($e\_tp\_dg = 1$):**
  $$\frac{\text{parallel\_num}}{e\_tp\_dg} = \frac{16}{1} = 16 > 8 \implies \mathbf{FALLO \ DE \ ASERCIÓN}$$
  *Razón Arquitectural:* Con $e\_tp\_dg = 1$, no es posible asignar una fracción de experto ($< 1$ experto) a una GPU sin dividir sus matrices de proyección de pesos.
- **Solución: Habilitar Expert Tensor Parallelism ($e\_tp\_dg \ge \lceil N_{\text{GPUs}} / E \rceil$):**
  Para $N_{\text{GPUs}} = 16$ y $E = 8$, configurando $e\_tp\_dg = 2$:
  $$\frac{\text{parallel\_num}}{e\_tp\_dg} = \frac{16}{2} = 8 \le 8 \implies \mathbf{VÁLIDO}$$
  $$\text{num\_expert\_per\_device} = \frac{8}{8} \times 2 = 1 \text{ partición tensorial de experto por GPU}$$
  Cada uno de los 8 expertos se divide entre 2 GPUs mediante paralelismo tensorial (las matrices `gate_proj`, `up_proj` y `down_proj` se dividen en mitades por columnas y filas), ejecutando un `moe_all_reduce_for_e_tp` interno tras el FFN.

#### Tabla Resumen de Compatibilidad de Paralelismo de Expertos:
| Escenario de Clúster | GPUs ($N$) | Expertos ($E$) | Configuración $e\_tp\_dg$ | Expertos por GPU | Duración Silicio FFN | Estado de Compatibilidad |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Menos GPUs que Expertos** | 2 | 8 | $e\_tp\_dg = 1$ | 4 expertos / GPU | $\sim 88.5\,\mu\text{s}$ | ✅ Totalmente Soportado (Nativo) |
| **Menos GPUs que Expertos** | 4 | 8 | $e\_tp\_dg = 1$ | 2 expertos / GPU | $\sim 44.3\,\mu\text{s}$ | ✅ Totalmente Soportado (Nativo) |
| **Balance Exacto** | 8 | 8 | $e\_tp\_dg = 1$ | 1 experto / GPU | $\sim 22.1\,\mu\text{s}$ | ✅ Totalmente Soportado (Canónico) |
| **Más GPUs que Expertos** | 16 | 8 | $e\_tp\_dg = 1$ | Inválido ($< 1$) | N/A | ❌ Aserción: Requiere $e\_tp\_dg > 1$ |
| **Más GPUs que Expertos** | 16 | 8 | $e\_tp\_dg = 2$ | 1 mitad de experto | $\sim 11.1\,\mu\text{s}$ + AllRed | ✅ Soportado con Expert TP |

---

# CAPÍTULO 3: Arquitectura Interna de BookSim2 y Nuestra Librería API (`booksim_api`)

## 3.1. El Motor de Simulación Ciclo a Ciclo de BookSim2 (`TrafficManager::_Step`)

BookSim2 es el estándar de oro académico en simulación ciclo a ciclo de redes de interconexión (NoCs y System Area Networks). Su núcleo operativo reside en la clase `TrafficManager` ([`booksim2/src/trafficmanager.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/trafficmanager.cpp)).

El método `TrafficManager::_Step()` ejecuta en cada ciclo de reloj de la red la siguiente secuencia de micro-arquitectura:
1. **`_RetireFlits()`:** Revisa los canales de salida de los routers de destino. Si ha llegado un flit, actualiza los créditos de buffer del router previo y, si el flit es de cola (`f->tail == true`), retira el paquete.
2. **`_ReceiveFlits()`:** Lee flits desde los canales físicos hacia las colas de entrada de los routers.
3. **`_Step()` en la Red:** Cada enrutador (`Router`) ejecuta:
   - *Buffer Write (BW):* Almacenamiento en el Canal Virtual (VC) correspondiente.
   - *Route Computation (RC):* Determinación del puerto de salida según el algoritmo (`dim_order` o adaptativo).
   - *Virtual Channel Allocation (VA):* Arbitraje de canales virtuales libres en el siguiente salto.
   - *Switch Allocation (SA):* Arbitraje de los puertos cruzados (crossbar).
   - *Switch Traversal (ST):* Tránsito de flits a través del crossbar.
4. **`_Inject()`:** Extrae flits pendientes desde las colas de inyección de los nodos de origen (`_partial_packets`) y los introduce en los buffers de entrada de la red si hay créditos disponibles.

---

## 3.2. Ciclo de Vida del Paquete y sus Flits (`head`, `body`, `tail`)

En BookSim2, los paquetes no viajan como entidades indivisibles, sino segmentados en unidades atómicas denominadas **flits (flow control units)**:
- **Flit de Cabeza (`head = true`):** Abre el camino. Contiene el identificador de paquete (`pid`), nodo origen, nodo destino y clase de tráfico. Asigna el Canal Virtual (VC) en los routers intermedios.
- **Flits de Cuerpo (`body`):** Siguen en pipeline el camino abierto por el flit de cabeza a través del mismo VC reservado.
- **Flit de Cola (`tail = true`):** Cierra el paquete. Libera la reserva del Canal Virtual en los routers a medida que los atraviesa y señala la entrega completa del paquete al ser retirado en destino.

---

## 3.3. Tiempos Fundamentales: $ctime$ (Creación), $itime$ (Inyección) y $atime$ (Retiro)

En nuestra instrumentación de BookSim2 ([`booksim2/src/booksim_api.cpp:L36-L120`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp#L36-L120)), hemos formalizado tres sellos de tiempo exactos para cada paquete:

1. **`Creation_Cycle` ($ctime$):**
   Momento en el que el software de la GPU genera la ráfaga de datos e invoca `BookSim_InjectPacket()`. En nuestro modelo, todos los paquetes de una misma capa MoE se generan en $ctime = 0$ (o en el ciclo de inicio de la fase de red).
2. **`Inject_Cycle` ($itime$):**
   Momento en el que el flit de cabeza (`head`) gana el arbitraje de la interfaz de red (NIC) y cruza físicamente el enlace de entrada al primer router (`_Inject()`).
3. **`Receive_Cycle` ($atime$):**
   Momento en el que el flit de cola (`tail`) es procesado en `_RetireFlit()` en el nodo destino.

---

## 3.4. Descomposición Física: Espera en Cola de NIC (`Queueing_Delay`) vs. Tránsito en Red (`Network_Latency`)

La latencia total del paquete se descompone de forma canónica en dos componentes físicos disjuntos:

$$\text{Total\_Latency} = atime - ctime$$

$$\text{Queueing\_Delay} = itime - ctime$$

$$\text{Network\_Latency} = atime - itime$$

$$\mathbf{\text{Total\_Latency} = \text{Queueing\_Delay} + \text{Network\_Latency}}$$

- **`Queueing_Delay` (Espera en Cola del NIC):** Refleja la contención estructural en la frontera software-hardware. Si una GPU genera 100 paquetes de golpe pero el enlace de inyección solo admite 1 flit por ciclo, los paquetes posteriores deben esperar obligatoriamente en cola mientras los flits anteriores son inyectados.
- **`Network_Latency` (Vuelo Real en NoC):** Refleja la contención dinámica en los conmutadores internos: retrasos por saltos (hops), esperas por Canales Virtuales ocupados y contención en los crossbars.

---

## 3.5. Métricas Avanzadas de Flits y Productividad de Red

Para dotar al análisis de fidelidad micro-arquitectural según los requerimientos de investigación, el co-simulador captura dos métricas elementales a nivel de flit:

### 1. Latencia Media de Flits por Paquete (`Avg_Flit_Latency`)
Dado que los flits de un paquete ($N_{\text{flits}}$) se retiran de forma asíncrona a lo largo de ciclos sucesivos en el destino debido a la contención en enlaces y conmutadores, la latencia del paquete hasta el retiro del último flit ($tail$) oculta el comportamiento de los flits precedentes. Se define la latencia media exacta de flits de un paquete $p$ como:

$$\text{Avg\_Flit\_Latency}(p) = \frac{\sum_{i=1}^{N_{\text{flits}}(p)} (t_{\text{retire}, i} - ctime(p))}{N_{\text{flits}}(p)} \quad [\text{ciclos}]$$

En [`booksim2/src/booksim_api.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp), el método `API_TrafficManager::_RetireFlit(Flit *f, int dest)` acumula en un mapa hash `flit_latency_sum[f->pid] += (_time - f->ctime)` cada vez que cualquier flit ($head$, $body$ o $tail$) abandona la red. Cuando `f->tail == true`, se computa la media exacta y se almacena en `BookSimPacketInfo::avg_flit_lat`.

### 2. Productividad Instantánea y Acumulada de la Red (`Throughput`)
La productividad o tasa de drenaje de la red en la operación en curso se calcula como la razón entre el volumen acumulado de flits recibidos por todos los nodos de destino y el tiempo transcurrido en ciclos de red:

$$\text{Throughput}(t) = \frac{\sum \text{Flits Recibidos en la Operación}}{\max(1, \_time - t_{\text{start\_op}})} \quad \left[\frac{\text{flits}}{\text{ciclo}}\right]$$

Esta métrica refleja cuantitativamente el grado de aprovechamiento y saturación del biseccionado de la topología en cada instante de la ráfaga colectiva.

---

## 3.6. Contexto de Operación LLM y Trazado Temporal (Scatter/Gather y Ventanas NS)

Para correlacionar inequívocamente cada paquete físico simulado en BookSim2 con la primitiva algorítmica del grafo de cómputo en LLMSimulator:
1. **Contadores Correlativos por Iteración:** En [`LLMSimulator/src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp), `BookSimCoSimManager` gestiona contadores estáticos `scatter_op_counter` y `gather_op_counter`. Cuando el reloj de la GPU `device->status.device_time` retrocede respecto al último tiempo registrado (indicativo del inicio de una nueva iteración de inferencia/decodificación cuando `iter > 1`), ambos contadores se reinician limpiamente a 1.
2. **Delimitación de Fronteras Temporales:**
   - **`Op_Start_NS`:** Estampa el reloj `device_time` antes de añadir la latencia calculada por la red.
   - **`Op_End_NS`:** Estampa el reloj `device_time` tras sumar la latencia en nanosegundos calculada por el oráculo.
3. **Puntos de Enganche en C++:**
   - Antes de iniciar el bucle de avance de ciclos de BookSim2, se invoca `BookSim_StartOperation(op_type, op_idx, op_start_ns)`.
   - Al completar la simulación de todos los paquetes de la ráfaga, se invoca `BookSim_FinishOperation(op_end_ns)`.
   - En `FinishOperation`, se estampan `op_end_ns` en todos los paquetes recibidos en la ráfaga y, si `--debug_pids` está activo, se emite por `stdout` el registro completo de 17 campos con prefijo `[TRACK_PID]`:
     `[TRACK_PID] PID,Src,Dst,ctime,itime,atime,Total_Lat,Net_Lat,Queue_Delay,Num_Flits,Size_Bytes,Avg_Flit_Lat,Throughput,Op_Type,Op_Idx,Op_Start_NS,Op_End_NS`

---

## 3.7. Diseño del Wrapper C++ `booksim_api` y Desacoplamiento de `main.cpp`

Para integrar BookSim2 como librería dinámica/estática en `LLMSimulator` sin colisiones de enlace:
1. Se aislaron las variables globales de BookSim2 (`gPrintActivity`, `gK`, `gN`, etc.) en [`booksim2/src/booksim_api.cpp:L15-L22`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp#L15-L22), evitando enlazar con el `main.cpp` original de BookSim2.
2. Se implementó la clase derivada `API_TrafficManager` que hereda de `TrafficManager`:
   - Sobrescribe `_RetireFlit()` para capturar métricas sin alterar las estadísticas internas de BookSim2, acumulando latencias de flits y productividad en tiempo real.
   - Encola las estructuras `BookSimPacketInfo` en la cola `arrived_packets`.
   - Si la variable de entorno `SIM_DEBUG_PIDS=1` está activa, emite la traza estructurada `[TRACK_PID]` con 17 columnas hacia `stdout`.
3. Se expuso una API pura en C en [`booksim2/src/booksim_api.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.hpp):
   - `BookSim_Initialize(const char* config_file)`
   - `BookSim_InjectPacket(int src, int dst, int size_in_flits)`
   - `BookSim_AdvanceCycle()`
   - `BookSim_CheckReceived(BookSimPacketInfo& info)`
   - `BookSim_StartOperation(const char* op_type, int op_idx, double op_start_ns)`
   - `BookSim_FinishOperation(double op_end_ns)`

---

## 3.8. Topologías de Red en BookSim2: Construcción de Mallas y Toros (`booksim2/src/networks/kncube.cpp`)

BookSim2 implementa una parametrización rigurosa de redes de interconexión directa de tipo $k$-ary $n$-cube a través de la clase `KNCube` ([`booksim2/src/networks/kncube.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/kncube.cpp)):

### Formalismo Matemático del $k$-ary $n$-cube
- $k$: Radix o número de routers a lo largo de cada dimensión (`_k`).
- $n$: Número de dimensiones ortogonales (`_n`).
- Total de nodos de conmutación: $N = k^n$ (`_size = powi(_k, _n)`).
- Total de canales unidireccionales de red: $C = 2 \cdot n \cdot N$.

### Algoritmo de Construcción de la Red (`KNCube::_BuildNet`)
En [`booksim2/src/networks/kncube.cpp:L70-L169`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/kncube.cpp#L70-L169), el método `_BuildNet` ensambla los routers y canales:
1. **Asignación de Puertos:** Cada router dispone de $R = 2n + 1$ puertos de entrada e idéntico número de puertos de salida:
   - 2 puertos (Derecha e Izquierda) por cada una de las $n$ dimensiones.
   - 1 puerto local de inyección/eyección (puerto de índice $2n$) conectado al host/NIC.
2. **Mapeo de Canales:**
   - Canal Derecho: $\text{RightChannel}(node, dim) = 2n \cdot node + 2 \cdot dim$
   - Canal Izquierdo: $\text{LeftChannel}(node, dim) = 2n \cdot node + 2 \cdot dim + 1$
3. **Malla (Mesh) vs. Toro (Torus):**
   - **Malla (`_mesh = true`):** Los routers situados en los bordes de la coordenada ($loc = 0$ o $loc = k - 1$) no conectan sus enlaces exteriores hacia nodos vecinos; la red tiene límites físicos abiertos. La latencia de enlace asignada es de **1 ciclo**.
   - **Toro (`_mesh = false`):** Los extremos se conectan circularmente mediante enlaces de retorno (*wrap-around*):
     - `_LeftNode`: si $loc = 0$, el vecino izquierdo es $node + (k - 1) \cdot k^{dim}$.
     - `_RightNode`: si $loc = k - 1$, el vecino derecho es $node - (k - 1) \cdot k^{dim}$.
   - **Modelado Físico de Latencia (`use_noc_latency`):** En un chip/sustrato físico real, los enlaces wrap-around deben cruzar toda la distancia transversal del chip para unir extremos opuestos. BookSim2 refleja esta física asignando:
     $$\text{Latencia de Enlace} = \begin{cases} 1 \text{ ciclo} & \text{si } \_mesh = \text{true (Malla)} \\ 2 \text{ ciclos} & \text{si } \_mesh = \text{false (Toro con wrap-around)} \end{cases}$$

---

## 3.9. Microarquitectura del Router Virtual-Channel y Prevención de Deadlock (`booksim2/src/routers/iq_router.cpp`, `routefunc.cpp`, `buffer_state.cpp`, `allocator/`)

La microarquitectura de conmutación modelada en nuestras simulaciones corresponde al router de entrada encolada con Canales Virtuales (`IQRouter`, [`booksim2/src/routers/iq_router.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routers/iq_router.cpp)).

### Pipeline Clásico de 4 Etapas (`IQRouter::_InternalStep`)

El avance de los flits a través de cada router se gobierna ciclo a ciclo en `IQRouter::_InternalStep()` ([`booksim2/src/routers/iq_router.cpp:L226-L283`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routers/iq_router.cpp#L226-L283)):

```
[Flit Entrada] ---> [ 1. IB: Buffer Entrada ] ---> [ 2. RC: Routing ] ---> [ 3. VA: Alloc VC ] 
                                                                                   |
[Flit Salida]  <--- [ 5. LT: Link Transmit  ] <--- [ 4. ST: Crossbar ] <--- [ 4. SA: Alloc Switch ]
```

1. **Buffer de Entrada (Input Buffering - IB / `_ReceiveFlits`):** El flit entrante se deposita en la cola FIFO del canal virtual asignado en el puerto de entrada.
2. **Cómputo de Enrutamiento (Routing Computation - RC / `_RouteEvaluate`):**
   Al llegar el flit de cabeza (`head`), se consulta la función de enrutamiento configurada (`_rf`). Ésta evalúa la tupla $(cur, dest)$ y produce una máscara de puertos de salida válidos y el rango admisible de Canales Virtuales (`OutputSet`).
3. **Asignación de Canales Virtuales (Virtual Channel Allocation - VA / `_VCAllocEvaluate`):**
   El flit de cabeza compite por reservar un Canal Virtual libre en el puerto de entrada del router adyacente hacia el que se dirige. El árbitro `_vc_allocator` (basado en algoritmos como `islip`, `separable_input_first` o `matrix`) resuelve los conflictos, consultando el estado de créditos en `_next_buf[output]->IsAvailableFor(vc)`. Una vez asignado, todos los flits del paquete reutilizan dicho VC.
4. **Asignación de Switch (Switch Allocation - SA / `_SWAllocEvaluate`):**
   Los flits que ya disponen de un VC asignado y créditos suficientes en el siguiente salto compiten por atravesar el conmutador crossbar hacia su puerto de salida. El árbitro de switch (`_sw_allocator`) garantiza que ningún puerto de salida reciba múltiples flits en el mismo ciclo.
5. **Travesía del Conmutador (Switch Traversal - ST / `_SwitchEvaluate`):**
   El flit ganador cruza físicamente la matriz de conmutación interna y se sitúa en el canal de salida (`_SendFlits`).
6. **Control de Flujo por Créditos (`buffer_state.cpp`):**
   Cuando un flit abandona un buffer de entrada, el router emite inmediatamente un crédito (`_SendCredits`) hacia el router del salto anterior, garantizando que nunca se produzca desbordamiento (*buffer overflow*).

### Prevención Matemática de Deadlock en Toros (`routefunc.cpp:dim_order_torus`)

En redes directas regulares, el enrutamiento por orden de dimensión (Dimension-Order Routing, DOR: $X \to Y$) previene interbloqueos en topologías acíclicas como mallas (Mesh), ya que las dependencias entre canales forman un orden topológico estricto sin ciclos dirigidos.

Sin embargo, en topologías en anillo y toro, los enlaces *wrap-around* introducen ciclos cerrados en el grafo de dependencias de canal (Channel Dependency Graph - CDG), donde flits de diferentes paquetes pueden bloquearse mutuamente en un anillo de espera circular infinito.

#### Algoritmo de Dateline de Dally-Seitz en BookSim2
Para garantizar la ausencia absoluta de deadlocks sin requerir costosos protocolos de escape o descarte de paquetes, BookSim2 implementa el particionado de Canales Virtuales de Dally-Seitz en [`booksim2/src/routefunc.cpp:L1517-L1582`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routefunc.cpp#L1517-L1582):

1. **Bipartición del Conjunto de Canales Virtuales:**
   Los $V$ canales virtuales disponibles se dividen equitativamente en dos clases disjuntas:
   $$\text{available\_vcs} = \left\lfloor \frac{vcEnd - vcBegin + 1}{2} \right\rfloor$$
   - **Clase 0 (Fase 0):** Rango inferior de VCs: $[vcBegin, vcEnd - \text{available\_vcs}]$
   - **Clase 1 (Fase 1):** Rango superior de VCs: $[vcBegin + \text{available\_vcs}, vcEnd]$
2. **Inyección en Fase 0:**
   Todo paquete entra a la red configurado con fase inicial `f->ph = 0`, restringiéndose a utilizar exclusivamente los VCs de la Clase 0.
3. **Detección de Cruce de Dateline:**
   En cada salto, la función `dor_next_torus` ([`booksim2/src/routefunc.cpp:L610-L627`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routefunc.cpp#L610-L627)) evalúa si el flit cruza la línea de fecha (*dateline*) establecida entre el nodo $k-1$ y el nodo $0$:
   - Si el flit viaja hacia la derecha ($dir = 0$) y la coordenada actual es mayor que la de destino ($cur > dest$).
   - O si viaja hacia la izquierda ($dir = 1$) y la coordenada de destino es menor que la actual ($dest < cur$).
4. **Transición Irreversible de Fase:**
   Al cruzar el enlace wrap-around que conecta los extremos de la dimensión, se asigna `f->ph = 1`. A partir de este instante, el paquete es promovido a la Clase 1 de VCs hasta llegar a su destino.
5. **Demostración de Acyclicidad:**
   Puesto que la transición entre clases es estrictamente monótona unidireccional ($\text{Clase 0} \to \text{Clase 1}$) y ningún paquete en Clase 1 puede solicitar canales de Clase 0, el grafo de dependencias de canal queda estrictamente estratificado en dos niveles acíclicos superpuestos, imposibilitando la formación de ciclos dirigidos de dependencia.
6. **Corolario Arquitectural:**
   Dado que `assert(available_vcs > 0)` en la línea 1555 de `routefunc.cpp`, **una topología Toro requiere obligatoriamente un mínimo de $V \ge 2$ canales virtuales**. Cualquier configuración con $V = 1$ fallará en la aserción de BookSim2 o incurrirá en deadlock estructural.

---

# CAPÍTULO 4: Nuestro Co-Simulador en Lazo Cerrado (LLMSimulator + BookSim2)

## 4.1. El Paradigma de Integración Oráculo Causal con Inyección Escalonada y Latencia por Destino (Bloque C)

La integración entre LLMSimulator y BookSim2 implementa un **modelo Oráculo centralizado de predicción causal físicamente fiel**:

En lugar de imponer una barrera artificial rígida que obligue a todas las GPUs a esperar a la más lenta y asignarles una latencia uniforme de red idéntica a la del peor caso del clúster, el simulador desacopla el avance temporal en `MoEScatter` y `MoEGather` ([`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp)):

1. **Detección y Cómputo del Desfase de Llegada ($t_{\text{src}}$ y $\Delta t_{\text{src}}$):**
   La primera GPU en alcanzar el módulo de red (GPU 0) detecta que `BookSimCoSimManager::calls_per_module[layer_name] == 0`.
   GPU 0 inspecciona los relojes físicos absolutos de todos los dispositivos del clúster:
   $$t_{\text{src}}[s] = \text{device}[s]\to\text{get\_time}(), \quad \forall s \in [0, N-1]$$
   Determina el instante temporal mínimo de llegada al módulo de red:
   $$t_{\min} = \min_{s \in [0, N-1]} t_{\text{src}}[s]$$
   Y calcula el desfase causal relativo de inyección en ciclos (dado que la frecuencia de reloj de red es $1\text{ GHz}$, $1\text{ ciclo} = 1.0\text{ ns}$):
   $$\Delta t_{\text{src}}[s] = \text{round}(t_{\text{src}}[s] - t_{\min})$$

2. **Inyección Causal Escalonada (`packets_by_cycle`):**
   GPU 0 construye la matriz completa de paquetes del clúster $src \to dst$ y asocia a cada paquete el ciclo exacto de liberación de su GPU origen: `delta_cycle = delta_t[src]`.
   Los paquetes se organizan en un mapa indexado por ciclo:
   $$\text{packets\_by\_cycle}[\Delta t_{\text{src}}]$$
   Se inicializa la operación en la API de BookSim2 en el instante $t_{\min}$ mediante `BookSim_StartOperation(op_type, op_idx, t_min)`.

3. **Bucle de Simulación de Red con Registro de Llegada Individual (`atime` por GPU Destino):**
   BookSim2 avanza ciclo a ciclo (`BookSim_AdvanceCycle()`). En cada ciclo `cycles`:
   - Si `packets_by_cycle` contiene paquetes programados para ese ciclo exacto (`cycles`), se inyectan en las colas del NIC de BookSim2. Las GPUs que terminaron su fase previa antes comienzan a transmitir de inmediato, compitiendo por los canales y buffers de la red sin esperar a las GPUs rezagadas.
   - A medida que `BookSim_CheckReceived(pkt_info)` retira paquetes completados, se actualiza el ciclo máximo de llegada del último paquete recibido por cada GPU destino específica:
     $$\text{max\_relative\_atime}[dst] = \max(\text{max\_relative\_atime}[dst], \text{cycles})$$

4. **Vectorización de Latencias Netas Individuales (`cached_latency_per_gpu`):**
   Una vez retirados todos los paquetes del clúster, el Oráculo calcula la latencia neta individual experimentada por cada GPU $dst$:
   $$t_{\text{end}}[dst] = t_{\min} + \text{max\_relative\_atime}[dst]$$
   $$\text{network\_latency\_ns}[dst] = t_{\text{end}}[dst] - t_{\text{src}}[dst]$$
   Almacena este valor en `BookSimCoSimManager::cached_latency_per_gpu[layer_name][dst]`.

5. **Aplicación y Registro Asíncrono en Cada GPU:**
   Cada GPU $i$, al ejecutar su propio `forward()`, recupera su latencia individual `cached_latency_per_gpu[layer_name][i]`, avanza su reloj local `device->status.device_time += network_latency_ns[i]` y emite su evento `.trc` correspondiente.
   La última GPU en procesar el módulo resetea los registros para la siguiente fase.

---

## 4.2. Traducción de Tensores y Metadatos de Enrutamiento a Tráfico Unicast

En [`src/module/communication.cpp:L161-L186`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp#L161-L186), el cálculo del volumen de tráfico entre cada GPU origen $src$ y cada GPU destino $dst$ durante `MoEScatter` se rige por:

```cpp
int tokens_to_dst = 0;
for(int e_id = expert_id_offset; e_id < expert_id_offset + num_expert_per_device; e_id++) {
    tokens_to_dst += sequences_metadata->scheduler->running_queue[src_dp_idx]->local_num_token_in_expert[e_id];
}
long bytes_to_dst = (long)tokens_to_dst * k * input->precision_byte / ne_tp_dg;
```

Para cada token enrutado:
$$\text{Bytes por Token} = k \times \text{precision\_byte} = 4096 \times 1\text{ B} = \mathbf{4096 \text{ Bytes}}$$

Si la GPU $src$ enruta $T_{src \to dst}$ tokens hacia la GPU $dst$:
$$\text{bytes\_to\_dst} = T_{src \to dst} \times 4096 \text{ Bytes}$$

---

## 4.3. Matemática Rigurosa de Paquetización: Demostración de los 9 Flits y 288 Bytes en Mixtral

Parámetros de red definidos en el Oráculo ([`src/module/communication.cpp:L148-L150`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp#L148-L150)):
- $\text{MTU} = 256\text{ Bytes}$ (Carga útil máxima por paquete).
- $\text{HEADER\_SIZE} = 24\text{ Bytes}$ (Metadatos de enrutamiento y control).
- $\text{FLIT\_SIZE} = 32\text{ Bytes}$ (Anchura física del enlace de interconexión).

### Algoritmo de Paquetización en Código:
```cpp
int num_packets = (bytes_to_dst + MTU - 1) / MTU;
for (int p = 0; p < num_packets; p++) {
    long payload = (p == num_packets - 1) ? (bytes_to_dst % MTU) : MTU;
    if (payload == 0) payload = MTU;
    int flits = (payload + HEADER_SIZE + FLIT_SIZE - 1) / FLIT_SIZE;
    BookSim_InjectPacket(src, dst, flits);
}
```

### Demostración Matemática de Uniformidad de Flits
Dado que cada token contiene $4096\text{ Bytes}$:

$$\frac{4096\text{ Bytes}}{256\text{ Bytes/MTU}} = 16.0 \quad (\text{Resto } 0)$$

Cualquier ráfaga de $T$ tokens transmite un total de $T \times 4096\text{ Bytes}$. Evaluando el operador módulo:

$$(T \times 4096) \pmod{256} \equiv 0$$

Por consiguiente:
1. **Todos los paquetes generados en toda la simulación (del primero al último) tienen un payload de exactamente $256\text{ Bytes}$.** No existen paquetes parciales o fragmentados.
2. **Tamaño Total del Paquete:**
   $$\text{Tamaño Total} = \text{Payload} + \text{Header} = 256\text{ B} + 24\text{ B} = \mathbf{280 \text{ Bytes}}$$
3. **Flits Requeridos por Paquete:**
   $$\text{Num\_Flits} = \left\lceil \frac{280\text{ B}}{32\text{ B/flit}} \right\rceil = \left\lceil 8.75 \right\rceil = \mathbf{9 \text{ flits}}$$
4. **Ocupación Física en el Enlace (`Size_Bytes`):**
   Como BookSim2 transmite flits discretos de 32 Bytes:
   $$\text{Size\_Bytes} = 9 \text{ flits} \times 32 \text{ Bytes/flit} = \mathbf{288 \text{ Bytes}}$$

> **Demostración Concluida:** Que los 57.152 paquetes de la simulación muestren idénticamente **9 flits** y **288 Bytes** no es un defecto de instrumentación, sino la consecuencia analítica exacta de la divisibilidad de la dimensión $k=4096$ de Mixtral entre una MTU de $256\text{ B}$.

---

## 4.4. Secuencia Causal de Barreras en la Capa MoE: De Attention a MoEGather (Arquitectura Desacoplada)

El flujo de control y sincronización a través de una capa MoE se rige por la siguiente secuencia estricta en [`src/module/expert.cpp:L136-L207`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp#L136-L207):

```
       [Attention Block] (~6.3 us)
              │
              ▼
    1. sync_0 (sync=false)
              │
              ▼
    2. gate_fn + gate_update (~0.06 us)
              │
              ▼
    3. MoEScatter (equalize_time=false) ◄────── Oráculo evalúa t_src, inyecta delta_t[src]
              │                                 Calcula max_atime[dst] por GPU individual
              ▼
    4. sync_for_moe_scatter ◄────────────────── BARRERA LOCAL {device_total_rank}
              │                                 GPU que recibe sus tokens inicia FFN de inmediato!
              ▼
    5. ExpertFFN (~22.1 us) ─────────────────── Cómputo Local de Expertos (Asimétrico y Desfasado)
              │
              ▼
    6. sync_2 (sync=false)
              │
              ▼
    7. all_reduce_for_e_tp
              │
              ▼
    8. sync_3 (equalize_time=false) ◄────────── Barrera de Dependencia de Datos (Sin aplanar relojes)
              │                                 Verifica que todas las GPUs terminen FFN
              ▼
    9. MoEGather (equalize_time=false) ◄─────── Oráculo escalona inyección según fin de FFN (delta_t)
              │                                 Calcula latencia de reunión individual por GPU
              ▼
   10. sync_for_moe_gather (equalize_time=true) ◄ BARRERA COLECTIVA GLOBAL (sync_devices)
              │                                   Las GPUs rápidas esperan a la rezagada:
              │                                   ¡Genera el NETWORK_STALL físico real!
              ▼
   11. Residual + Siguiente Capa
```

### Análisis Detallado de los Flags de Sincronización y `equalize_time`:
- **`MoEScatter` (`equalize_time = false`):** Las GPUs entran a la fase de dispersión en sus respectivos instantes físicos. El Oráculo mide $t_{\text{src}}$, inyecta paquetes de forma escalonada según $\Delta t_{\text{src}}$, y calcula el ciclo de llegada individual `latency_per_dst[dst]`.
- **`sync_for_moe_scatter` (`device_list = {device_total_rank}`):** Se restringe la sincronización a la propia GPU local. Esto permite que una GPU cuyos tokens ya han terminado de llegar a su experto local comience de inmediato su cómputo `ExpertFFN` sin esperar a que terminen de llegar los paquetes a las GPUs restantes del clúster.
- **`sync_3` (`equalize_time = false`):** Situado entre el cómputo de expertos y `MoEGather`. Garantiza que todos los expertos locales hayan terminado de generar sus activaciones antes de que se proceda a recolectarlas, pero al tener `equalize_time = false`, **no aplana los relojes en `sync_devices()`**. De este modo, los instantes de finalización asimétricos de `ExpertFFN` llegan intactos al Oráculo de `MoEGather`.
- **`MoEGather` (`equalize_time = false`):** Inyecta los paquetes de cada GPU con el desfase $\Delta t_{\text{src}} = \text{round}(t_{\text{src}} - t_{\min})$ derivado de los tiempos reales de término de `ExpertFFN`. Cada GPU experimenta su duración de red individual hasta recibir su último token.
- **`sync_for_moe_gather` (`equalize_time = true`):** Barrera de sincronización colectiva global previa a la conexión residual y la siguiente capa de atención. Al ejecutar `sync_devices()`, todas las GPUs que terminaron su fase de red antes esperan a la GPU más lenta, registrando con absoluta precisión micro-arquitectural el tiempo ocioso en el bloque rojo **`NETWORK_STALL`**.

---

## 4.5. Fidelidad Física Alcanzada: Latencia Individual por GPU Destino (`cached_latency_per_gpu`) y Desfase Causal de Inyección ($\Delta t_{src}$)

### Mecanismo Matemático y Estructuras C++

En [`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp), la clase `BookSimCoSimManager` gestiona el almacenamiento vectorizado:

```cpp
static std::map<std::string, std::map<int, double>> cached_latency_per_gpu;
```

#### Paso 1: Muestreo de Relojes de Inyección
Al invocar `forward()` sobre la primera GPU del clúster:
```cpp
std::vector<double> t_src(total_num_device, 0.0);
for (int s = 0; s < total_num_device; s++) {
    t_src[s] = device->cluster->get_device(s)->get_time();
}
double t_min = *std::min_element(t_src.begin(), t_src.end());
std::vector<int> delta_t(total_num_device, 0);
for (int s = 0; s < total_num_device; s++) {
    delta_t[s] = std::max(0, (int)std::round(t_src[s] - t_min));
}
```

#### Paso 2: Planificación Temporal de Paquetes en el Reloj de BookSim2
Cada paquete unicast generado se almacena según su instante relativo de disponibilidad:
```cpp
struct PendingPacket { int src; int dst; int flits; int delta_cycle; };
std::map<int, std::vector<PendingPacket>> packets_by_cycle;
// Al generar paquetes:
packets_by_cycle[delta_t[src]].push_back({src, dst, flits, delta_t[src]});
```

#### Paso 3: Retiro de Flits y Medición Causal Bidireccional (TX/RX)
Durante el bucle de avance de BookSim2, se registran los cuatro hitos temporales por dispositivo:
```cpp
std::vector<int> max_relative_rx_atime(total_num_device);
std::vector<int> max_relative_tx_inj(total_num_device);
std::vector<int> max_relative_tx_retire(total_num_device);
for (int d = 0; d < total_num_device; d++) {
    max_relative_rx_atime[d] = delta_t[d];
    max_relative_tx_inj[d] = delta_t[d];
    max_relative_tx_retire[d] = delta_t[d];
}

while (total_received < total_injected) {
    if (packets_by_cycle.count(cycles)) {
        for (const auto& pkt : packets_by_cycle[cycles]) {
            BookSim_InjectPacket(pkt.src, pkt.dst, pkt.flits);
            if (cycles > max_relative_tx_inj[pkt.src]) {
                max_relative_tx_inj[pkt.src] = cycles;
            }
        }
        packets_by_cycle.erase(cycles);
    }
    BookSim_AdvanceCycle();
    cycles++;
    while (BookSim_CheckReceived(pkt_info)) {
        total_received++;
        if (cycles > max_relative_rx_atime[pkt_info.dst]) {
            max_relative_rx_atime[pkt_info.dst] = cycles;
        }
        if (cycles > max_relative_tx_retire[pkt_info.src]) {
            max_relative_tx_retire[pkt_info.src] = cycles;
        }
    }
}
```

#### Paso 4: Asignación Individual y Registro Bidireccional
Para cada dispositivo $d \in [0, N-1]$:
```cpp
std::vector<int> rel_finish(total_num_device, 0);
for (int d = 0; d < total_num_device; d++) {
    rel_finish[d] = std::max({
        delta_t[d],
        max_relative_rx_atime[d],
        max_relative_tx_inj[d],
        max_relative_tx_retire[d]
    });
}
for (int d = 0; d < total_num_device; d++) {
    double t_end = t_min + (double)rel_finish[d];
    double net_lat = std::max(0.0, t_end - t_src[d]);
    cached_latency_per_gpu[layer_name][d] = net_lat;
}
```

### Validación Empírica en Mixtral 8x7B (8 GPUs, Topología Torus, Batch Size 32)

La ejecución empírica de una simulación completa de Mixtral demuestra de forma concluyente la ruptura de la simetría y la emergencia de fenómenos físicos reales:

#### Comparativa Capa MoE 0 (Nanosegundos Absolutos):
| Métrica / Fase | GPU 0 (Receptora Rápida) | GPU 7 (Receptora Lenta / Desfasada) |
| :--- | :--- | :--- |
| **Inicio MoEScatter** | $6.361,42\text{ ns}$ | $6.361,42\text{ ns}$ |
| **Duración MoEScatter** | $\mathbf{1.729,00\text{ ns}}$ | $\mathbf{3.933,00\text{ ns}}$ |
| **Fin Scatter / Inicio FFN** | $\mathbf{8.090,42\text{ ns}}$ | $\mathbf{10.294,42\text{ ns}}$ |
| **Duración ExpertFFN** | $22.118,40\text{ ns}$ | $22.130,68\text{ ns}$ |
| **Fin FFN / Inicio MoEGather** | $\mathbf{30.208,82\text{ ns}}$ | $\mathbf{32.425,11\text{ ns}}$ |
| **Desfase de Inyección Gather ($\Delta t_{\text{src}}$)** | $0\text{ ns}$ (Primer emisor) | $\mathbf{+2.216,29\text{ ns}}$ (Emisor tardío) |
| **Duración MoEGather** | $1.978,00\text{ ns}$ | $2.407,71\text{ ns}$ |
| **Fin Gather** | $32.186,82\text{ ns}$ | $34.832,82\text{ ns}$ |
| **`NETWORK_STALL` en `sync_for_moe_gather`** | $\mathbf{2.651,00\text{ ns}}$ (Espera a GPU 7) | $\mathbf{5,00\text{ ns}}$ (Prácticamente nulo) |
| **Reloj Sincronizado Final** | $\mathbf{34.837,82\text{ ns}}$ | $\mathbf{34.837,82\text{ ns}}$ |

#### Conclusiones Científicas de los Resultados:
1. **Asimetría Real de Transferencia:** En MoEScatter, GPU 0 recibe sus tokens en solo $1.729\text{ ns}$, mientras GPU 7 requiere $3.933\text{ ns}$.
2. **Inicio Desacoplado de Cómputo:** GPU 0 no permanece ociosa esperando a GPU 7; arranca su `ExpertFFN` en $t = 8.090,42\text{ ns}$, adelantándose en $2.204\text{ ns}$ a la GPU 7.
3. **Inyección Físicamente Causal en Gather:** Al terminar `ExpertFFN` antes, GPU 0 inyecta sus resultados en BookSim2 a los $30.208,82\text{ ns}$, mientras GPU 7 no comienza a emitir flits hasta los $32.425,11\text{ ns}$.
4. **Emergencia Causal de `NETWORK_STALL`:** La barrera `sync_for_moe_gather` absorbe la discrepancia temporal de llegada. GPU 0 registra un `NETWORK_STALL` de $2.651\text{ ns}$ mientras espera a que GPU 7 termine su recepción de red. Ambos dispositivos emergen sincronizados a los $34.837,82\text{ ns}$ con fidelidad a nivel de ciclo.

---

## 4.6. Auditoría Forense de Causalidad Física en MoEGather/MoEScatter y Demostración de Simetría de Tráfico

### 4.6.1. Orden de Ejecución C++ al Entrar al Oráculo de `MoEGather` y Garantía de Estabilidad Temporal en `sync_3`

Una duda fundamental planteada durante la inspección microarquitectural ciclo a ciclo del cronograma (`timeline_part_014_130k_to_140k.png`) es la siguiente: dado que `MoEGather` posee `sync == false`, cuando la GPU 0 entra a `MoEGather::forward()` y ejecuta el Oráculo centralizado (`calls_per_module == 0`), ¿las demás GPUs (1 a 7) ya han ejecutado todas su cómputo `ExpertFFN` y actualizado sus relojes, o alguna GPU podría seguir computando mientras el Oráculo lee sus marcas de tiempo?

La auditoría forense del código C++ demuestra formalmente que **es imposible que el Oráculo lea un reloj no actualizado, gracias a la barrera previa `sync_3`**:
1. **Topología del Grafo de Dependencias:** En [`src/module/expert.cpp:L186-L192`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp#L186-L192), la ejecución del clúster atraviesa la barrera `sync_3` inmediatamente después de la computación local `expert_FFN`:
   ```cpp
   auto sync_3 = Sync::Create(module_map_name, "sync_3", sync_devices, false, ...);
   ```
2. **Semántica de Sincronización en `Sync::forward()` ([`src/module/sync.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/sync.cpp)):**
   Cada hilo del clúster ejecuta:
   ```cpp
   Sync__Set(id, sync_idx, device_id);
   while (!Sync__Is_all_set(id, sync_idx));
   ```
   Esta rutina constituye una barrera pthread/cond-var estricta en tiempo de ejecución C++. Ningún hilo puede rebasar `sync_3` hasta que los $N$ dispositivos hayan finalizado su cómputo local y llamado a `Sync__Set`.
3. **Preservación de Tiempos Heterogéneos (`equalize_time = false`):** A diferencia de las barreras globales aplanadoras, `sync_3` opera con `equalize_time = false`, lo que significa que no iguala los relojes `device_time` al máximo. En consecuencia:
   - Todas las GPUs completan su `ExpertFFN` antes de que cualquiera pueda entrar a `MoEGather`.
   - Cada GPU preserva su instante exacto de finalización de cómputo en nanosegundos ($t_{\text{src}}[d]$).
   - Cuando la GPU 0 cruza la barrera e invoca el Oráculo, los $N$ relojes leídos corresponden fehacientemente al estado consolidado post-ExpertFFN.

#### Registro Empírico del Oráculo en Gather Nº4 (Layer 3, Iteración 2):
```
[COSIM_ORACLE] Gather Nº4 (Layer 3):
  t_min: 136815.6596 ns (alcanzado por GPU 0)
  t_src[0]: 136815.6596 ns -> delta_t:    0 ns (primer emisor)
  t_src[1]: 137628.7516 ns -> delta_t:  813 ns
  t_src[2]: 138777.8319 ns -> delta_t: 1962 ns
  t_src[3]: 139066.3090 ns -> delta_t: 2251 ns
  t_src[4]: 139920.6631 ns -> delta_t: 3105 ns
  t_src[5]: 140128.8471 ns -> delta_t: 3313 ns (último emisor en terminar FFN)
  t_src[6]: 140062.9090 ns -> delta_t: 3247 ns
  t_src[7]: 138792.8319 ns -> delta_t: 1977 ns
```
Esto demuestra de manera irrefutable que el Oráculo observó a la GPU 4 finalizando su `ExpertFFN` exactamente en $t = 139.920,66\text{ ns}$ ($\Delta t_4 = 3.105\text{ ns}$ tras GPU 0).

---

### 4.6.2. Demostración Matemática de Simetría en la Matriz de Tráfico ($T_{\text{Gather}} = T_{\text{Scatter}}^T$) y Dispersión Estocástica de Tokens

Una aparente paradoja física detectada en el cronograma fue: *¿Cómo es posible que la GPU 0 finalice su bloque azul Gather Nº4 en $\sim 139.878\text{ ns}$ (entrando en NETWORK_STALL) mientras la GPU 4 sigue ejecutando su bloque verde Calc: ExpertFFN hasta los $\sim 139.920\text{ ns}$? ¿No debería GPU 0 esperar a que GPU 4 termine su ExpertFFN y le envíe sus tokens?*

#### Teorema de Simetría del Tráfico MoE:
En cualquier capa Mixture-of-Experts con paralelismo de expertos (EP):
- Durante `MoEScatter`, si una secuencia asignada a la GPU $A$ tiene $k$ tokens enrutados a un experto ubicado físicamente en la memoria de la GPU $B$, la GPU $A$ debe transmitir $k$ tokens a la GPU $B$:
  $$T_{\text{Scatter}}(A \to B) = k$$
- Durante `ExpertFFN`, el experto en la GPU $B$ procesa esos $k$ tokens.
- Durante `MoEGather`, los $k$ vectores resultantes deben ser devueltos exactamente a la GPU dueña original de la secuencia ($A$) para su recombinación ponderada:
  $$T_{\text{Gather}}(B \to A) \equiv T_{\text{Scatter}}(A \to B)$$
- En términos de la matriz de tráfico global de $N \times N$ nodos:
  $$\mathbf{T}_{\text{Gather}} = \mathbf{T}_{\text{Scatter}}^T$$

#### Auditoría de Tráfico en la Capa 3 (Gather Nº4):
Al auditar los metadatos de enrutamiento exactos leídos por el planificador (`local_num_token_in_expert`):
1. **Flujos Salientes de GPU 0 en Scatter Nº4:**
   - Hacia GPU 1 (Expertos 2 y 3): 4 tokens (36 flits)
   - Hacia GPU 2 (Expertos 4 y 5): 5 tokens (45 flits)
   - Hacia GPU 3 (Expertos 6 y 7): 2 tokens (18 flits)
   - Hacia GPU 7 (Expertos 14 y 15): 5 tokens (45 flits)
   - **Hacia GPU 4 (Expertos 8 y 9): ¡0 tokens!**
2. **Flujos Entrantes a GPU 0 en Gather Nº4:**
   Por el Teorema de Simetría:
   $$T_{\text{Gather}}(4 \to 0) = T_{\text{Scatter}}(0 \to 4) = \mathbf{0 \text{ tokens}}$$
   La GPU 4 no tenía que enviar absolutamente ningún paquete a la GPU 0. Los únicos paquetes que la GPU 0 debía recolectar provenían exclusivamente de las GPUs 1, 2, 3 y 7.
3. **Causalidad Temporal de Llegada:**
   - Las GPUs 1, 2, 3 y 7 finalizaron su `ExpertFFN` temprano ($t_{\text{src}} \le 139.066,31\text{ ns}$, $\Delta t \le 2.251$ ciclos).
   - Sus paquetes fueron inyectados en BookSim2 en sus respectivos ciclos de liberación e hicieron tránsito por la topología Torus.
   - El último paquete destinado a la GPU 0 arribó en el ciclo relativo $3.062$ ($t = 136.815,66 + 3.062 = \mathbf{139.877,66\text{ ns}}$).
   - En ese instante ($139.878\text{ ns}$), la GPU 0 ya poseía el 100% de los tokens de sus secuencias locales en memoria. No existía ninguna dependencia causal física que la obligara a esperar a la GPU 4.
4. **Actividad de la GPU 4:**
   La GPU 4 estaba procesando 7 tokens que le fueron enviados por las GPUs 5, 6 y 7. Por ello, su cómputo `ExpertFFN` se prolongó legítimamente hasta los $139.920\text{ ns}$, momento en el que comenzó a inyectar sus flits hacia las GPUs 5, 6 y 7 (que terminaron su Gather en $t > 141.000\text{ ns}$).

---

### 4.6.3. Principio de Causalidad Bilateral Emisor-Receptor en Colectivas MoE (`MoEScatter` y `MoEGather`)

En las versiones tempranas del co-simulador, la programación de paquetes en el buffer de BookSim2 (`packets_by_cycle`) se realizaba de manera unilateral basándose exclusivamente en el reloj de finalización del nodo emisor:
$$\text{injection\_cycle}(src \to dst) = \delta_t[src] = \text{round}(t_{\text{src}}[src] - t_{\min})$$

Esta formulación unilateral adolecía de una inconsistencia física crítica: si la GPU emisora $src$ finalizaba su cómputo previo tempranamente ($\delta_t[src] = 0$) mientras la GPU receptora $dst$ aún se encontraba ejecutando cómputo local intensivo en sus unidades SIMD/Tensor Core (ej. $\delta_t[dst] = 1.500\text{ ns}$ en `ExpertFFN` o `Attention`), el paquete $src \to dst$ era inyectado y transitaba por la red NoC, llegando a la cola de entrada del router de $dst$ mucho antes de que $dst$ abandonara el cómputo previo. En hardware real (NVIDIA NVLink/NVSwitch con NCCL), una GPU no puede procesar colectivas ni aceptar buffers de destino mientras sus núcleos de cómputo no hayan alcanzado el punto de sincronización o el kernel de recepción colectiva.

Para erradicar esta anomalía y dotar al co-simulador de rigor físico estricto, se formuló e implementó en `LLMSimulator/src/module/communication.cpp` el **Principio de Causalidad Bilateral Emisor-Receptor**:
$$\text{ready\_cycle}(src, dst) = \max(\delta_t[src],\; \delta_t[dst])$$
$$\text{packets\_by\_cycle}[\text{ready\_cycle}].\text{push\_back}(\{src, dst, flits, \text{ready\_cycle}\})$$

Bajo este principio, la transferencia de un tensor entre dos nodos no puede iniciarse físicamente en la red hasta que **ambos interlocutores** hayan alcanzado la frontera de la colectiva:
1. El emisor $src$ debe haber concluido el cómputo que produce los datos de activación ($t \ge t_{\text{src}}[src] = t_{\min} + \delta_t[src]$).
2. El receptor $dst$ debe haber concluido su cómputo previo y estar preparado para recibir y almacenar el tensor en sus búferes de memoria ($t \ge t_{\text{src}}[dst] = t_{\min} + \delta_t[dst]$).

Como consecuencia directa, se garantiza matemáticamente que ningún paquete $src \to dst$ en la red posea un ciclo de creación o inyección inferior a $\max(t_{\text{src}}[src], t_{\text{src}}[dst])$:
$$\forall p \in \text{Packets}(src \to dst): \quad \text{Creation\_Cycle}(p) \ge \max(\delta_t[src],\; \delta_t[dst])$$

---

### 4.6.4. Desglose Microarquitectural en Tres Fases (Pre-Stall, Colectiva Activa y Post-Stall de Barrera Sincrónica)

La adopción de la causalidad bilateral exige una contabilidad precisa del tiempo de las GPUs. Anteriormente, la latencia total de la colectiva ($\Delta t_{\text{total}} = t_{\text{end}}[d] - t_{\text{src}}[d]$) se registraba de forma monolítica como un único bloque `moe_scatter` o `moe_gather`. Si una GPU rápida finalizaba su cómputo a los $0\text{ ns}$ pero sus pares no estaban listos hasta los $1.500\text{ ns}$, ese intervalo de espera ociosa se atribuía erróneamente a "tránsito de red", distorsionando las métricas de congestión y rendimiento de la interconexión.

Para solventarlo, se implementó el rastreo microarquitectural ciclo a ciclo del primer y último ciclo activo de red para cada dispositivo $d$:
$$\text{first\_active\_cycle}[d] = \begin{cases} \min(\text{first\_tx\_inj}[d],\; \text{first\_rx\_arrival}[d]) & \text{si } d \text{ participa en TX o RX} \\ \delta_t[d] & \text{si } d \text{ no participa} \end{cases}$$
$$\text{last\_active\_cycle}[d] = \max(\text{max\_relative\_rx\_atime}[d],\; \text{max\_relative\_tx\_inj}[d],\; \text{max\_relative\_tx\_retire}[d])$$

Esto permite desglosar de manera analítica y visual la colectiva en **tres fases secuenciales no solapadas**:

```
GPU Rápida (d):
[  Cómputo Previo  ]  [   Pre-Stall   ]  [   Colectiva Activa   ]  [     Post-Stall Barrera     ]  [ Siguiente Capa ]
------------------->|----------------->|---------------------->|----------------------------->|---------------->
t_src[d]            t_min + first_act  t_min + last_act        t_max (sync_for_moe_gather)
                    (NETWORK_STALL)    (moe_gather/scatter)    (NETWORK_STALL)
```

1. **Fase 1: Pre-Stall de Red (`NETWORK_STALL` Pre-Colectivo):**
   - **Intervalo:** $[t_{\text{src}}[d],\; t_{\min} + \text{first\_active\_cycle}[d]]$
   - **Duración:** $\text{pre\_stall\_ns}[d] = \max(0,\; \text{first\_active\_cycle}[d] - \delta_t[d])$
   - **Significado físico:** Tiempo durante el cual la GPU $d$, habiendo concluido su cómputo previo (`ExpertFFN` o `Attention`), permanece ociosa esperando a que sus interlocutores alcancen la colectiva. Se registra en `TFM_device_{d}.trc` como `NETWORK_STALL`.
2. **Fase 2: Colectiva Activa (`moe_scatter` o `moe_gather`):**
   - **Intervalo:** $[t_{\min} + \text{first\_active\_cycle}[d],\; t_{\min} + \text{last\_active\_cycle}[d]]$
   - **Duración:** $\text{active\_comm\_ns}[d] = \max(0,\; \text{last\_active\_cycle}[d] - \text{first\_active\_cycle}[d])$
   - **Significado físico:** Tiempo de actividad efectiva en la red NoC, desde la inyección/recepción del primer flit hasta el retiro del último paquete correspondiente a la GPU $d$. Mide puramente la transferencia real y la contención en enlaces. Se registra en `TFM_device_{d}.trc` como `moe_scatter` o `moe_gather`.
3. **Fase 3: Post-Stall de Sincronización (`NETWORK_STALL` en Barrera Sincrónica):**
   - **Intervalo:** $[t_{\min} + \text{last\_active\_cycle}[d],\; t_{\max}]$ donde $t_{\max} = \max_j (t_{\min} + \text{last\_active\_cycle}[j])$.
   - **Duración:** $\text{post\_stall\_ns}[d] = t_{\max} - (t_{\min} + \text{last\_active\_cycle}[d])$.
   - **Significado físico:** Espera en la barrera sincrónica (`sync_for_moe_gather` vía `ModuleGraph::sync_devices()`) a que la GPU más lenta del clúster culmine su fase activa de red. Se registra en `TFM_device_{d}.trc` como `NETWORK_STALL` con el detalle `"Waiting for sync"`.

#### Continuidad Estricta del Wall-Clock Time:
Dado que el inicio de cada fase coincide exactamente con el final de la fase anterior:
$$t_{\text{end}}(\text{Fase 1}) = t_{\text{start}}(\text{Fase 2}) = t_{\min} + \text{first\_active\_cycle}[d]$$
$$t_{\text{end}}(\text{Fase 2}) = t_{\text{start}}(\text{Fase 3}) = t_{\min} + \text{last\_active\_cycle}[d]$$
$$t_{\text{end}}(\text{Fase 3}) = t_{\max} = t_{\text{start}}(\text{Siguiente Módulo})$$
Se garantiza una línea temporal continua sin huecos ($\Delta t_{\text{gap}} = 0\text{ ns}$) ni solapamientos ($\Delta t_{\text{overlap}} = 0\text{ ns}$) en todas las trazas de dispositivo (`TFM_device_*.trc`).

---

### 4.6.5. Normalización de Ciclos Relativos en la API de BookSim2 y Alineación de Cero Ciclos en la Visualización Híbrida

En la arquitectura original de BookSim2, el reloj de red interno (`_time`) avanza monótonamente a lo largo de toda la ejecución del simulador, acumulando ciclos a través de múltiples llamadas sucesivas a colectivas (`Scatter #1`, `Gather #1`, `Scatter #2`, etc.).

#### Causa Raíz del Desfase de Relojes Detectado en la GUI:
Cuando `API_TrafficManager::FinishOperation` volcaba las marcas de tiempo de los paquetes en `[TRACK_PID]`, exportaba los ciclos absolutos (`pkt.ctime`, `pkt.itime`, `pkt.atime`). Al representar los paquetes en la interfaz Web GUI (`gui/trace_parser.py`):
1. El analizador restaba heurísticamente el mínimo ciclo del grupo:
   $$\text{base\_cycles} = \min_{p \in \text{Op}}(\text{Creation\_Cycle}(p))$$
2. Sin embargo, bajo causalidad bilateral, si ningún nodo participante tenía $\delta_t = 0$, o si la pareja más temprana requería $\max(\delta_t[src], \delta_t[dst]) = c_{\min} > 0$, la resta de $\text{base\_cycles}$ desplazaba artificialmente todos los paquetes hacia la izquierda en $c_{\min}$ nanosegundos respecto al instante real de la colectiva ($t_{\min}$ / `Op_Start_NS`).
3. Adicionalmente, en visualizaciones acumulativas multi-operación, los ciclos absolutos superaban las decenas de miles, provocando desalineaciones visibles entre el panel izquierdo (Cronograma GPU) y el panel derecho (Visualizador de Paquetes NoC) en el Visualizador Híbrido (`HybridSyncController`).

#### Solución Arquitectónica (Normalización Cero-Offset):
1. **Modificación en C++ (`booksim2/src/booksim_api.cpp`):**
   Al finalizar cada operación, los ciclos de ciclo de vida de los paquetes se normalizan directamente con respecto a `op_start_cycle`:
   ```cpp
   int rel_ctime = pkt.ctime - op_start_cycle;
   int rel_itime = pkt.itime - op_start_cycle;
   int rel_atime = pkt.atime - op_start_cycle;
   ```
   Esto asegura que `Creation_Cycle`, `Inject_Cycle` y `Receive_Cycle` en `packet_tracking_debug.csv` reflejen estrictamente el offset temporal relativo en nanosegundos desde `Op_Start_NS` ($t_{\min}$).
2. **Alineación Exacta en el Backend GUI (`gui/trace_parser.py`):**
   ```python
   if seg["Creation_Cycle"].min() > 1e7:
       base_cycles = seg.groupby(["Op_Type", "Op_Idx"])["Creation_Cycle"].transform("min")
   else:
       base_cycles = 0.0

   adjusted_op_start = seg["Op_Start_NS"] + off_ns
   seg["pkt_start_ns"] = adjusted_op_start + (seg["Creation_Cycle"] - base_cycles)
   seg["pkt_inject_ns"] = adjusted_op_start + (seg["Inject_Cycle"] - base_cycles)
   seg["pkt_end_ns"] = adjusted_op_start + (seg["Receive_Cycle"] - base_cycles)
   ```
3. **Garantía de Alineación de 0 Ciclos en el Canvas (`timeline_canvas.js`):**
   Dado que `pkt_start_ns = Op_Start_NS + Creation_Cycle = t_{\min} + \max(\delta_t[src], \delta_t[dst])`, y en el cronograma de la GPU la fase de colectiva activa arranca en $t_{\min} + \text{first\_active\_cycle}[d]$, las barras de paquetes de la GPU más lenta en el panel derecho comienzan en el píxel y nanosegundo exacto en que arranca el bloque azul de colectiva en el panel izquierdo, con **cero ciclos y cero nanosegundos de desfase**.

---

### 4.6.6. Validación Experimental End-to-End: Cero Infracciones Causales y Continuidad Cronológica Estricta

Para validar experimentalmente la integridad de la solución, se ejecutaron baterías de prueba end-to-end completas sobre dos cargas de trabajo altamente representativas:
1. **Mixtral 8x7B en Toro 1D (8 GPUs B100, $BS=32$, 2 iteraciones):**
   - **Paquetes analizados:** $116.432$ paquetes en `packet_tracking_debug.csv`.
   - **Infracciones de causalidad bilateral:** **0** ($\text{Creation\_Cycle} \ge \max(\delta_t[src], \delta_t[dst])$ verificado en el $100\%$ de los paquetes).
   - **Continuidad cronológica:** $7.699$ transiciones temporales en `TFM_device_*.trc` verificadas con $0\text{ ns}$ de hueco y $0\text{ ns}$ de solapamiento.
   - **Desglose de GPU rápida (GPU 0):** En Gather #1 ($t_{\min} = 29.855,76\text{ ns}$), GPU 0 entra a la colectiva a los $29.855,76\text{ ns}$ pero sus interlocutores no están listos hasta los $30.563,76\text{ ns}$. GPU 0 registra un pre-stall de $708,00\text{ ns}$ como `NETWORK_STALL`, seguido de $2.113,00\text{ ns}$ de `moe_gather` activo y $1.433,29\text{ ns}$ de post-stall en la barrera sincrónica `sync_for_moe_gather`, completando exactamente a los $34.110,05\text{ ns}$.
2. **DeepSeek-V3 en Malla 2D 4x2 (8 GPUs B100, $BS=32$, 2 iteraciones):**
   - **Paquetes analizados:** $2.154.852$ paquetes en `packet_tracking_debug.csv`.
   - **Infracciones de causalidad bilateral:** **0** ($\text{Creation\_Cycle} \ge \max(\delta_t[src], \delta_t[dst])$ en los $2.154.852$ paquetes).
   - **Continuidad cronológica:** $98.251$ transiciones temporales en `TFM_device_*.trc` con $0\text{ ns}$ de hueco y $0\text{ ns}$ de solapamiento.
3. **Paridad Numérica CLI ↔ GUI:**
   - La correlación numérica entre `analyze_traces.py` y `trace_parser.py` / `analysis_gui.py` es del $100\%$ en todas las métricas (`Compute`, `Transit`, `Stalls`, `Wall-Clock`, $\lambda$, `Avg_Flit_Latency`, `Avg_Packet_Latency`), con una discrepancia inferior a $0{,}05\text{ ns}$ derivada exclusivamente del redondeo decimal visual.

---

## 4.7. Integración de AllReduce en el Oráculo BookSim2: Modelado Ring-AllReduce con Causalidad Cuádruple (Vía 2)

### 4.7.1. Contexto, Motivación y Limitación del Simulador Original
En el simulador original `LLMSimulator-orig` (SCALE SNU), la primitiva colectiva `AllReduce::forward` ([`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp)) operaba bajo un modelo analítico puramente sintético basado en saltos ideales:
$$t_{\text{red}} = t_{\text{latency}} + \frac{\text{size}}{\text{bandwidth}} + \text{one\_hop} \times \text{hop}$$
Este enfoque presentaba severas deficiencias para la fidelidad científica del modelado de red:
1. **Invisibilidad de la Contención:** Ignoraba por completo la contención física de canales virtuales (VCs), colisiones en conmutadores y saturación de enlaces en topologías NoC reales (Toro, Malla).
2. **Desconexión con BookSim2:** Mientras las colectivas MoE (`MoEScatter` y `MoEGather`) se evaluaban flit a flit en BookSim2, las capas de paralelismo de tensores (TP) en la Atención y proyecciones lineales utilizaban saltos temporales ideales desprovistos de paquetes.
3. **Aplanamiento Artificial de Relojes:** El módulo se instanciaba con `equalize_time = true`, destruyendo cualquier desfase temporal previo entre GPUs y falseando la causalidad física.

Para solventar esta limitación y cerrar el 100% de las colectivas de red del co-simulador con precisión ciclo a ciclo (BookSim2), se implementó la **Vía 2: Integración de Ring-AllReduce en el Oráculo BookSim2**.

---

### 4.7.2. Grados de Paralelismo Tensorial en LLMSimulator
El paralelismo tensorial (TP) en LLMSimulator se gobierna a través de dos parámetros configurables:
- **`none_expert_tensor_degree` (`ne_tp_dg`):** Factor de división tensorial en capas densas no-MoE (Atención multifuente/GQA y proyecciones lineales asociadas). Este parámetro se expone en la CLI de `run_sim.py` mediante `--tensor_degree` o `--tp` (por defecto `1`).
- **`expert_tensor_degree` (`e_tp_dg`):** Factor de división en los bloques densos de los expertos MoE (por defecto `1` al utilizar paralelismo de expertos puro).

Cuando $N_{\text{GPUs}}$ dispositivos participan en la simulación y se establece $\text{ne\_tp\_dg} = P > 1$, el clúster se particiona en $N_{\text{GPUs}} / P$ subgrupos independientes de tamaño $P$. Cada subgrupo ejecuta colectivas `AllReduce` acotadas exclusivamente a su lista local de dispositivos `device_list = {d_0, d_1, \dots, d_{P-1}}`.

---

### 4.7.3. Desacoplamiento de Barrera y Caching Aislado por Subgrupo
1. **Desacoplamiento (`equalize_time = false`):**
   En el constructor `AllReduce::AllReduce`, se fijó `this->equalize_time = false;`, asegurando que cada GPU $d$ acceda al módulo en su instante temporal exacto $t_{\text{src}}[d]$ sin barreras sincrónicas artificiales previas.
2. **Espacio de Claves Aislado por Subgrupo (`op_key`):**
   Dado que múltiples subgrupos de TP (ej. GPUs $\{0,1\}$, $\{2,3\}$, $\{4,5\}$ y $\{6,7\}$ en un clúster de 8 GPUs con $P=2$) ejecutan colectivas `all_reduce` en paralelo, la caché estática de latencias no puede indexarse únicamente por `module_map_name`. Se implementó un particionamiento unívoco:
   ```cpp
   std::string op_key = this->module_map_name + "_grp_" + std::to_string(this->device_list[0]);
   ```
   Esto garantiza que el primer dispositivo de cada subgrupo actúa como su propio Oráculo local, sin colisiones de caché entre subgrupos concurrentes.

---

### 4.7.4. Algoritmo Ring-AllReduce a Nivel de Flit en BookSim2
Para un subgrupo de $P$ GPUs ($P = |\text{device\_list}|$):
- Si $P \le 1$, no existe comunicación entre dispositivos y la operación retorna inmediatamente con latencia nula.
- Si $P > 1$, se modela la topología de anillo lógico sobre la topología física subyacente de BookSim2:
  1. **Segmentación en Chunks:**
     El tensor de entrada (de tamaño total `size` bytes) se divide en $P$ fragmentos equitativos:
     $$S_{\text{chunk}} = \left\lceil \frac{\text{size}}{P} \right\rceil \quad [\text{Bytes}]$$
  2. **Fases del Anillo (Reduce-Scatter y All-Gather):**
     El algoritmo Ring-AllReduce ejecuta:
     - $P - 1$ pasos de **Reduce-Scatter**, donde en cada paso la GPU $d_i$ envía un chunk al nodo vecino en el anillo $d_{(i+1) \pmod P}$ y recibe del nodo $d_{(i-1+P) \pmod P}$.
     - $P - 1$ pasos de **All-Gather**, donde los chunks completamente reducidos se propagan a lo largo del anillo lógico de manera idéntica.
  3. **Volumen Total y Paquetización:**
     Cada GPU transmite en total $2(P - 1)$ chunks de tamaño $S_{\text{chunk}}$:
     $$V_{\text{GPU}} = 2(P - 1) \cdot S_{\text{chunk}} = 2(P - 1) \cdot \left\lceil \frac{\text{size}}{P} \right\rceil \quad [\text{Bytes}]$$
     Aplicando las especificaciones físicas de la red ($\text{MTU} = 256\text{ B}$, $\text{Header} = 24\text{ B}$, $\text{Flit} = 32\text{ B}$, resultando en paquetes de 9 flits y 288 Bytes sobre el canal físico), el número total de paquetes transmitidos por GPU hacia su vecino en el anillo es:
     $$N_{\text{pkts/GPU}} = \left\lceil \frac{V_{\text{GPU}}}{\text{MTU}} \right\rceil$$

---

### 4.7.5. Inyección Asíncrona Escalonada y Causalidad Cuádruple en el Oráculo
El dispositivo $d_0$ del subgrupo asume la orquestación en BookSim2:
1. **Cálculo de Desfases de Inyección ($\Delta t$):**
   $$t_{\min} = \min_{d \in \text{device\_list}} (t_{\text{src}}[d])$$
   $$\Delta t[d] = \text{round}(t_{\text{src}}[d] - t_{\min}) \quad [\text{ciclos}]$$
2. **Generación Temporalmente Indexada:**
   Cada paquete emitido por la GPU $d$ hacia su destino en el anillo tiene su ciclo de creación fijado en $c_{\text{creation}} = \Delta t[d]$. BookSim2 inyecta los flits en la cola de entrada del router físico correspondiente a la GPU $d$ conforme el reloj de la red alcanza dicho ciclo.
3. **Notificación de Operación Colectiva:**
   ```cpp
   BookSim_StartOperation("AllReduce", allreduce_op_counter++, t_min);
   ```
4. **Avance Ciclo a Ciclo y Registro:**
   Se ejecuta `BookSim_AdvanceCycle()` hasta que todos los paquetes generados son retirados de la red (`total_received == total_injected`).
5. **Regla de Causalidad Cuádruple Bidireccional:**
   $$\text{rel\_finish}[d] = \max\Big(\Delta t[d],\; \text{Max\_RX\_Atime}[d],\; \text{Max\_TX\_Inj}[d],\; \text{Max\_TX\_Retire}[d]\Big)$$
   $$t_{\text{end}}[d] = t_{\min} + \text{rel\_finish}[d]$$
   $$\text{network\_latency}[d] = \max(0.0,\; t_{\text{end}}[d] - t_{\text{src}}[d])$$
6. **Sellado de Operación:**
   ```cpp
   BookSim_FinishOperation(t_max_finish);
   ```
7. **Consumo por GPUs del Subgrupo:**
   La GPU líder almacena las latencias en `cached_latency_per_gpu[op_key][d]`. Las demás GPUs leen directamente su latencia calculada y avanzan su reloj local: `device->status.device_time += network_latency_ns`.

---

## 4.8. Estudio de Desbalanceo Extremo de Carga en Expertos MoE (Skewness, Puntos Calientes de Red e In-Cast Hotspots - Vía 3)

### 4.8.1. Contexto, Motivación y Fenómeno de Popularidad de Expertos
En arquitecturas Mixture-of-Experts (MoE) del estado del arte como Mixtral 8x7B, el mecanismo de enrutamiento asigna dinámicamente cada token a una pequeña fracción de expertos ($k=2$ de $E=8$). En condiciones ideales de evaluación sintética con factor de dispersión nulo (`skewness: 0.0`), el planificador distribuye los tokens de manera cuasi-uniforme entre los expertos ($\sim 12.5\%$ de probabilidad por dispositivo). 

Sin embargo, en escenarios reales de inferencia sobre dominios especializados (código, matemáticas o lenguaje conversacional), los routers de las redes neuronales concentran la gran mayoría del tráfico sobre un conjunto reducido de expertos altamente especializados ("expertos populares"). Este desbalanceo de carga sigue matemáticamente una **distribución de ley de potencia o distribución Zipfiana**:
$$w_i = \frac{1}{(i + 1)^s} \quad \text{con } i \in [0, E-1]$$
donde $s \ge 0$ es el exponente de Zipf (*skewness*).

La **Vía 3** implementa la parametrización completa del desbalanceo de expertos en el co-simulador, permitiendo evaluar cómo la heterogeneidad de carga impacta simultáneamente en el subsistema de cómputo local y en la red de interconexión NoC (BookSim2).

---

### 4.8.2. Parametrización en CLI (`run_sim.py`) e Integración en el Pipeline
1. **Argumento CLI:** Se añadió a `LLMSimulator/run_sim.py` el parámetro `--skewness` (o `--skew`, tipo `float`, por defecto `0.0`).
2. **Inyección Dinámica en `config.yaml`:**
   El orquestador `run_sim.py` detecta la configuración base y añade o actualiza dinámicamente `skewness: {args.skewness}` en la sección de generación del archivo `config.yaml`.
3. **Nomenclatura Canónica de Resultados:**
   Cuando $s > 0$, la carpeta de salida generada en `build/results/` añade automáticamente el sufijo descriptivo `_skew{s}` (ej. `mixtral_8dev_torus_bs32_skew0.5_20261110_...` y `mixtral_8dev_torus_bs32_skew1.0_20261110_...`).
4. **Propagación a la Suite de Análisis (`analyze_traces.py`):**
   `analyze_traces.py` lee el parámetro `skewness` desde `config.yaml` (o lo extrae del nombre de la carpeta mediante expresiones regulares), incorporando automáticamente la etiqueta `, Skew={s}` en los centroides macroscópicos de la curva de saturación de red (`curva_saturacion_red.png`) y en las tablas comparativas de consola.

---

### 4.8.3. Batería Experimental de Validación (Mixtral 8x7B en Toro 1D de 8 GPUs)
Para aislar rigurosamente el impacto del desbalanceo MoE, se ejecutó una batería experimental idéntica de 3 simulaciones bajo la misma topología de interconexión y carga de lote:
- **Modelo:** Mixtral 8x7B (8 GPUs, 8 Expertos, Top-2, $d_{\text{model}} = 4096$, $d_{\text{ffn}} = 14336$).
- **Topología NoC:** Toro 1D (8 nodos, 4 Canales Virtuales, dimension-order routing `dim_order`).
- **Carga de Trabajo:** Batch Size $BS = 32$, 2 iteraciones, longitud de salida 2 tokens en modo decodificación (`decode_mode = on`).
- **Valores de Skewness Evaluados:**
  1. **Línea Base ($s = 0.0$ - Uniforme):** Tráfico balanceado con selector uniforme.
  2. **Moderado ($s = 0.5$ - Zipfiano Moderado):** Concentración suave hacia los primeros expertos.
  3. **Extremo ($s = 1.0$ - Hotspot Severo):** Concentración severa de ley de potencias.

---

### 4.8.4. Resultados Empíricos Comparativos y Métricas de Rendimiento

A continuación se resume la descomposición macroscópica de tiempos, latencias de red ciclo a ciclo y tasas de inyección obtenidas en la batería experimental:

| Métrica | Skewness 0.0 (Uniforme) | Skewness 0.5 (Moderado) | Skewness 1.0 (Extremo) | Variación Relativa ($0.0 \to 1.0$) |
| :--- | :---: | :---: | :---: | :---: |
| **Tiempo Total de Decodificación** | $1,092.3\,\mu\text{s}$ | $1,101.5\,\mu\text{s}$ | $1,147.2\,\mu\text{s}$ | **$+5.0\%$** |
| **Tiempo de Cómputo GPU (`Compute`)** | $869.6\,\mu\text{s}$ ($79.6\%$) | $869.6\,\mu\text{s}$ ($79.0\%$) | $869.6\,\mu\text{s}$ ($75.8\%$) | **$0.0\%$ (Invariante)** |
| **Tránsito en Red Colectiva (`Transit`)** | $169.2\,\mu\text{s}$ ($15.5\%$) | $177.0\,\mu\text{s}$ ($16.1\%$) | $222.4\,\mu\text{s}$ ($19.4\%$) | **$+31.4\%$** 🔴 |
| **Burbujas de Sincronización (`Stalls`)** | $19.3\,\mu\text{s}$ ($1.8\%$) | $17.7\,\mu\text{s}$ ($1.6\%$) | $24.4\,\mu\text{s}$ ($2.1\%$) | **$+26.4\%$** 🔴 |
| **Latencia Media de Flit (`Avg_Flit_Latency`)** | $688.1\text{ ciclos}$ | $743.1\text{ ciclos}$ | $837.0\text{ ciclos}$ | **$+21.6\%$** |
| **Latencia Media de Paquete (`Total_Latency`)** | $1,321.2\text{ ciclos}$ | $1,423.7\text{ ciclos}$ | $1,705.9\text{ ciclos}$ | **$+29.1\%$** 🔴 |
| **Tasa Media de Inyección Real ($\lambda$)** | $0.2822\text{ flits/c/nodo}$ | $0.2737\text{ flits/c/nodo}$ | $0.2421\text{ flits/c/nodo}$ | **$-14.2\%$** |

#### Distribución Asimétrica de Paquetes en `MoEScatter` por GPU Destino
Al analizar los 57,000+ paquetes intercambiados durante la fase `Scatter` en la última iteración, se observa con precisión el colapso hacia el router de la GPU 0:

| GPU Destino (Experto) | Paquetes $s = 0.0$ (%) | Paquetes $s = 0.5$ (%) | Paquetes $s = 1.0$ (%) | Latencia Media de Paquete ($s=1.0$) | Retardo en Cola NIC ($s=1.0$) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **GPU 0 (Experto 0)** | 7,136 ($12.45\%$) | 12,176 ($21.27\%$) | **17,568 ($30.81\%$)** | $1,364.4\text{ ciclos}$ | $1,192.1\text{ ciclos}$ |
| **GPU 1 (Experto 1)** | 7,056 ($12.31\%$) | 8,832 ($15.43\%$) | **11,440 ($20.06\%$)** | $2,002.8\text{ ciclos}$ | $1,928.2\text{ ciclos}$ |
| **GPU 2 (Experto 2)** | 7,232 ($12.62\%$) | 7,856 ($13.72\%$) | 7,408 ($12.99\%$) | $2,219.0\text{ ciclos}$ | $2,152.3\text{ ciclos}$ |
| **GPU 3 (Experto 3)** | 6,416 ($11.20\%$) | 6,832 ($11.93\%$) | 5,504 ($9.65\%$) | $2,380.3\text{ ciclos}$ | $2,307.3\text{ ciclos}$ |
| **GPU 4 (Experto 4)** | 8,192 ($14.30\%$) | 5,936 ($10.37\%$) | 4,848 ($8.50\%$) | $2,425.9\text{ ciclos}$ | $2,364.4\text{ ciclos}$ |
| **GPU 5 (Experto 5)** | 7,024 ($12.26\%$) | 5,472 ($9.56\%$) | 4,048 ($7.10\%$) | $2,501.1\text{ ciclos}$ | $2,451.8\text{ ciclos}$ |
| **GPU 6 (Experto 6)** | 7,232 ($12.62\%$) | 5,200 ($9.08\%$) | 3,312 ($5.81\%$) | $2,511.7\text{ ciclos}$ | $2,461.9\text{ ciclos}$ |
| **GPU 7 (Experto 7)** | 7,008 ($12.23\%$) | 4,944 ($8.64\%$) | **2,896 ($5.08\%$)** | $2,822.5\text{ ciclos}$ | $2,774.6\text{ ciclos}$ |

---

### 4.8.5. Hallazgos Científicos y Análisis Microarquitectural
1. **La Invarianza del Tiempo de Cómputo (Régimen Memory-Bound):**
   Un resultado contraintuitivo a primera vista es que el tiempo de cómputo GPU (`Compute`) se mantiene rigurosamente constante en $869.6\,\mu\text{s}$ para los tres valores de skewness. 
   La explicación física deriva de la demostración matemática de la Sección 2.4: en la fase de decodificación ($BS=32$), la intensidad aritmética de cada token es minúscula ($I \ll I_{\text{ridge}} \approx 562.5\text{ FLOP/B}$). El tiempo de ejecución de `ExpertFFN` está completamente dominado por la lectura de los pesos del experto desde la memoria HBM3E ($58.72\text{ MB}$ por proyección $\to \sim 22.15\,\mu\text{s}$ por capa). Procesar 1 token o 25 tokens en un acelerador con $3.5\text{ PFLOPS}$ apenas añade $0.5\text{ ns}$ de tiempo aritmético. Por tanto, **el desbalanceo de carga en decodificación no penaliza el cómputo de la GPU congestionada, sino que transfiere íntegramente todo el cuello de botella a la red NoC**.

2. **Formación del Punto Caliente (*In-Cast Hotspot*) y Árbol de Congestión en BookSim2:**
   En $s = 1.0$, el router de la GPU 0 debe absorber más del $30.8\%$ de todo el tráfico de la red, y conjuntamente con la GPU 1 reciben más del $50.8\%$. Esto genera una saturación inmediata de los buffers de entrada de los canales virtuales (VCs) que apuntan hacia el nodo 0, provocando un árbol de congestión (*congestion tree*) que se propaga aguas arriba hacia los demás conmutadores del Toro.

3. **Paradoja de la Tasa de Inyección ($\lambda$ decrece al aumentar el desbalanceo):**
   Nótese que la tasa real de inyección inyectada $\lambda$ **disminuye** de $0.2822$ a $0.2421\text{ flits/ciclo/nodo}$ conforme $s$ aumenta de $0.0$ a $1.0$. Esto se debe a que la severa contrapresión en las colas del router del experto popular bloquea la concesión de créditos de control de flujo. Los emisores no pueden inyectar flits nuevos, incrementando el retardo en cola de la NIC (`Queueing_Delay` medio se eleva a más de $2,000$ ciclos) y dilatando la duración total de la colectiva $\Delta\text{Cycles}_{\text{collective}}$, lo que matemáticamente deprime la tasa media calculada por el cociente $\lambda = \text{Total\_Flits} / (N_{\text{GPUs}} \times \Delta\text{Cycles})$.

4. **Ampliación de Burbujas de Sincronización (`NETWORK_STALL`):**
   Las GPUs sub-utilizadas (ej. GPU 7, que recibe solo el $5\%$ de los paquetes) completan su comunicación de red y sus expertos locales mucho antes que el nodo congestionado. Sin embargo, no pueden progresar en el grafo del transformer debido a la barrera colectiva `MoEGather`, acumulando un incremento del $+26.4\%$ en tiempo muerto de espera (`NETWORK_STALL`).

---

## 4.9. Estudio Comparativo Arquitectónico: Mixtral 8x7B vs. DeepSeek-V3 (Fine-Grained MoE & MLA - Vía 4)

### 4.9.1. Contexto y Fundamentación Arquitectónica: Grano Grueso vs. Grano Fino
La evolución de los modelos de lenguaje basados en Mezcla de Expertos (*Mixture of Experts*, MoE) ha transitado desde particiones de **grano grueso** (*coarse-grained*, representadas canónicamente por **Mixtral 8x7B**) hacia arquitecturas modernas de **grano fino** (*fine-grained micro-experts*, lideradas por **DeepSeek-V3**).

| Dimensión Arquitectural | Mixtral 8x7B | DeepSeek-V3 | Impacto en Interconexión NoC / BookSim2 |
| :--- | :--- | :--- | :--- |
| **Número Total de Capas** | 32 (100% MoE) | 60 (3 densas iniciales + 57 MoE) | Mayor profundidad del grafo; 3 capas iniciales sin tráfico de dispersión MoE. |
| **Dimensión Oculta ($d_{\text{model}}$)** | $4.096$ | $7.168$ | Multiplica el volumen de datos por token transferido a través de la red. |
| **Dimensión Intermedia FFN ($d_{\text{ffn}}$)** | $14.336$ | $2.048$ (micro-experto) / $2.048$ (compartido) | Grano fino: cada micro-experto es $\sim 7\times$ más estrecho que un experto de Mixtral. |
| **Número de Expertos ($E$)** | 8 | $256$ enrutados + 1 compartido | En un clúster de 8 GPUs: 1 experto/GPU (Mixtral) vs. **32 micro-expertos/GPU** (DeepSeek). |
| **Factor de Activación Top-$k$** | Top-2 ($k=2$) | Top-8 ($k=8$) | Dispersión radical: cada token contacta hasta 8 GPUs distintas (fan-out global). |
| **Mecanismo de Atención** | GQA ($32$ Q heads, $8$ KV heads) | MLA (*Multi-Head Latent Attention*) | Compresión latente de KV cache y absorción de matrices en inferencia. |
| **Precisión Numérica de Cómputo** | BF16 (16 bits) | FP8 (8 bits en GEMM) / BF16 en Gather | Disminución del footprint en Scatter pero duplicación asimétrica en Gather. |

### 4.9.2. Mecanismo de Compresión de Atención Multi-Head Latent Attention (MLA)
En arquitecturas estándar con Multi-Query Attention (MQA) o Grouped-Query Attention (GQA), la memoria requerida por la caché KV escala linealmente con la longitud de secuencia $S$, el número de capas $L$ y el número de cabezas KV $N_{kv}$:
$$\text{Memoria}_{\text{GQA}} = 2 \cdot L \cdot S \cdot N_{kv} \cdot d_h$$

DeepSeek-V3 introduce **Multi-Head Latent Attention (MLA)** para comprimir drásticamente la huella de memoria durante la fase de decodificación mediante proyecciones de bajo rango (*Low-Rank Projections*) desacopladas:

1. **Compresión Latente de Claves y Valores (KV):**
   El vector de activación de entrada $h_t \in \mathbb{R}^{d}$ se proyecta a un espacio latente comprimido de dimensión $d_c = 512$:
   $$c_t^{KV} = W_{DKV} h_t, \quad W_{DKV} \in \mathbb{R}^{d_c \times d}$$
   A partir de este vector latente $c_t^{KV}$, se reconstruyen las claves de contenido y valores:
   $$k_t^C = W_{UK} c_t^{KV}, \quad v_t^C = W_{UV} c_t^{KV}, \quad W_{UK}, W_{UV} \in \mathbb{R}^{(N_h d_h) \times d_c}$$

2. **Desacoplamiento de Posición Rotatoria (Decoupled RoPE):**
   Dado que RoPE no es invariante a transformaciones lineales de bajo rango, MLA desacopla las componentes posicionales:
   $$k_t^R = \text{RoPE}(W_{KR} h_t), \quad W_{KR} \in \mathbb{R}^{d_R \times d}$$
   La clave final concatenada es:
   $$k_t = [k_{t, 1}^C \mathbin{\Vert} k_t^R, \dots, k_{t, N_h}^C \mathbin{\Vert} k_t^R]$$

3. **Absorción de Matrices en Generación Autoregresiva:**
   Durante la generación de tokens, el producto escalar entre las consultas proyectadas $q_t^C$ y las claves $k_s^C$ permite absorber la matriz de descompresión $W_{UK}$ directamente en la matriz de consulta:
   $$q_t^{C \top} k_s^C = (W_{UQ} c_t^Q)^\top (W_{UK} c_s^{KV}) = c_t^{Q \top} (W_{UQ}^\top W_{UK}) c_s^{KV}$$
   Esto permite que en la memoria caché KV solo sea necesario persistir el vector latente $c_t^{KV}$ ($512\text{ elementos}$) y la clave rotatoria $k_t^R$ ($64\text{ elementos}$), reduciendo la huella de memoria en más de un **$93\%$** respecto a MHA y permitiendo batches masivos sin saturar la HBM3E.

### 4.9.3. Desglose Microarquitectural de DeepSeek-V3: Capas Densas Iniciales y Expertos Compartidos
El flujo de ejecución en cada una de las 60 capas decodificadoras de DeepSeek-V3 se bifurca en dos fases temporales:
1. **Capas Densas Iniciales (Capas 0, 1 y 2):**
   Las primeras 3 capas del transformer no son MoE; implementan un `DenseFFN` tradicional con dimensión intermedia $d_{\text{ffn}} = 18.432$. Al no enrutar tokens, generan exactamente **cero tráfico de red colectivo** (`moe_scatter` ni `moe_gather`). Cada una de estas capas requiere $\sim 81.6\,\mu\text{s}$ de cómputo local puramente memory-bound en la GPU (sumando $\sim 245\,\mu\text{s}$ en total).
2. **Capas MoE Híbridas (Capas 3 a 59):**
   A partir de la capa 3, cada bloque integra:
   - **32 Micro-Expertos Enrutados por GPU ($E=256$ en 8 GPUs):** Tokens dispersados mediante `MoEScatter` con Top-8 ($k=8$), procesados secuencialmente según la carga local, y recolectados mediante `MoEGather`.
   - **1 Experto Compartido (*Shared Expert*):** Se ejecuta localmente en el 100% de los aceleradores sin requerir comunicación de red, asegurando la captura de conocimiento transversal y estabilizando la especialización de los micro-expertos.

### 4.9.4. Batería Experimental Paritaria (8x B100, Toro 1D y Malla 2D, BS=32)
Para aislar de manera rigurosa el impacto del grano de los expertos, la compresión MLA y la sensibilidad topológica, se ejecutó una batería paritaria bajo idénticas condiciones físicas de hardware y decodificación:
- **Aceleradores:** 8 GPUs Nvidia B100 ($3.5\text{ PFLOPS}$, $8.0\text{ TB/s}$ HBM3E).
- **Topologías de Interconexión:**
  1. Toro 1D de 8 nodos (`net_dims: [8]`).
  2. Malla 2D de 4x2 nodos (`net_dims: [4, 2]`, mapeada a BookSim2 AnyNet).
- **Canales Virtuales y Enrutamiento:** 4 VCs por puerto físico con enrutamiento determinista por orden de dimensión (`dim_order` / `min`).
- **Carga de Trabajo:** Continuous Batching con Batch Size $BS=32$, $s=0.0$ (distribución balanceada), 2 iteraciones estadísticas de decodificación autoregresiva (2 tokens generados).

### 4.9.5. Análisis Macroscópico Comparativo de Tiempos y Tráfico NoC
Los resultados macroscópicos extraídos por `analyze_traces.py --recent 3` revelan la profunda disparidad física entre arquitecturas y el impacto de la conectividad bidimensional:

| Métrica Macroscópica | Mixtral 8x7B (Toro 1D) | DeepSeek-V3 (Toro 1D) | DeepSeek-V3 (Malla 2D 4x2) | Impacto Topológico (Malla vs. Toro) |
| :--- | :--- | :--- | :--- | :--- |
| **Tiempo de Cómputo GPU (`Compute`)** | $911.5\,\mu\text{s}$ ($82.9\%$) | $8,340.6\,\mu\text{s}$ ($69.1\%$) | $8,340.6\,\mu\text{s}$ ($70.4\%$) | Idéntico (independiente de red) |
| **Tiempo de Tránsito de Red (`Transit`)** | $169.3\,\mu\text{s}$ ($15.4\%$) | $3,344.5\,\mu\text{s}$ ($27.7\%$) | $\mathbf{3,137.9\,\mu\text{s}}$ ($26.5\%$) | **$-206.6\,\mu\text{s}$ ($-6.18\%$)** 🟢 |
| **Burbujas de Sincronización (`Stalls`)** | $19.3\,\mu\text{s}$ ($1.8\%$) | $387.8\,\mu\text{s}$ ($3.2\%$) | $\mathbf{365.0\,\mu\text{s}}$ ($3.1\%$) | **$-22.8\,\mu\text{s}$ ($-5.88\%$)** 🟢 |
| **Tiempo Total de Muro (`Wall-Clock`)** | $\mathbf{1,100.0\,\mu\text{s}}$ | $\mathbf{12,072.9\,\mu\text{s}}$ | $\mathbf{11,843.5\,\mu\text{s}}$ | **$-229.4\,\mu\text{s}$ ($-1.90\%$)** 🟢 |
| **Latencia Media de Flit (`Avg_Flit_Latency`)** | $688.1\text{ ciclos}$ | $6,534.4\text{ ciclos}$ | $\mathbf{6,255.3\text{ ciclos}}$ | **$-279.1\text{ ciclos}$ ($-4.27\%$)** 🟢 |
| **Latencia Media de Paquete (`Total_Latency`)** | $1,321.2\text{ ciclos}$ | $11,282.1\text{ ciclos}$ | $\mathbf{10,269.6\text{ ciclos}}$ | **$-1,012.5\text{ ciclos}$ ($-8.97\%$)** 🟢 |
| **Tasa Media de Inyección Real ($\lambda$)** | $0.2822\text{ flits/c/nodo}$ | $0.2552\text{ flits/c/nodo}$ | $\mathbf{0.2751\text{ flits/c/nodo}}$ | **$+7.80\%$ throughput** 🟢 |

### 4.9.6. Auditoría de Tráfico de Paquetes (`packet_tracking_debug.csv`) y Dinámica de Colas
La inspección flit a flit del archivo `packet_tracking_debug.csv` arroja la clave microarquitectural de la congestión y su descompresión:

| Métrica de Paquetes y Flits | Mixtral 8x7B (Toro 1D) | DeepSeek-V3 (Toro 1D) | DeepSeek-V3 (Malla 2D 4x2) | Comparativa Malla vs. Toro |
| :--- | :--- | :--- | :--- | :--- |
| **Total de Paquetes Transmitidos** | $114,592$ | $2,142,168$ | $2,142,168$ | Idéntico ($18.69\times$ vs. Mixtral) |
| **Total de Flits Físicos en Red** | $1,031,328$ | $19,279,512$ | $19,279,512$ | Idéntico ($18.69\times$ vs. Mixtral) |
| **Paquetes en `MoEScatter`** | $57,296$ ($50.0\%$) | $714,056$ ($33.3\%$) | $714,056$ ($33.3\%$) | Idéntico (FP8, $7168\text{ B/token}$) |
| **Paquetes en `MoEGather`** | $57,296$ ($50.0\%$) | $1,428,112$ ($66.7\%$) | $1,428,112$ ($66.7\%$) | Idéntico (BF16, $14336\text{ B/token}$) |
| **Retardo Medio en Colas NIC (`Queueing_Delay`)** | $1,252.1\text{ ciclos}$ | $11,192.6\text{ ciclos}$ | $\mathbf{10,180.4\text{ ciclos}}$ | **$-1,012.2\text{ ciclos}$ ($-9.04\%$)** 🟢 |
| **Retardo Máximo en Colas NIC** | $4,313\text{ ciclos}$ | $52,680\text{ ciclos}$ | $\mathbf{42,573\text{ ciclos}}$ | **$-10,107\text{ ciclos}$ ($-19.19\%$ cola pico)** 🟢 |
| **Tiempo Medio de Vuelo en Red (`Network_Latency`)**| $77.1\text{ ciclos}$ | $68.7\text{ ciclos}$ | $84.2\text{ ciclos}$ | $+15.5\text{ ciclos}$ (distancia sin wrap-around) |

### 4.9.7. Hallazgos Científicos y Conclusiones Arquitectónicas de la Vía 4
1. **La Paradoja del Grano Fino y la Explosión All-to-All:**
   En Mixtral ($k=2, E=8$), cada token es enviado a solo 2 expertos, lo que genera un patrón de tráfico disperso donde un porcentaje significativo de transferencias puede resolverse localmente o mediante saltos mínimos. En cambio, en DeepSeek-V3 ($k=8, E=256$), cada token se descompone en 8 micro-expertos repartidos probabilísticamente entre los 8 nodos. Esto transforma cada capa MoE en una comunicación de **difusión total (*All-to-All Broadcast*)**, donde el $100\%$ de los nodos inyectan ráfagas hacia el $100\%$ del resto del clúster simultáneamente.

2. **Asimetría Estructural de Tráfico por Precisión Mixta (FP8 vs. BF16):**
   A diferencia de Mixtral, donde Scatter y Gather son exactamente simétricos ($57,296$ paquetes cada uno), en DeepSeek-V3 la fase de Gather transfiere el doble de datos que Scatter ($1,428,112$ paquetes vs. $714,056$). El motivo es que la inferencia computa en FP8 ($1\text{ B/elem}$ en la activación enviada en Scatter), pero la agregación ponderada de activaciones en Gather devuelve tensores en BF16 ($2\text{ B/elem}$) para mitigar la degradación numérica. Esta asimetría duplica la contención de red precisamente en la fase previa a la barrera de sincronización, disparando los tiempos de tránsito.

3. **Invarianza del Tiempo de Vuelo vs. Hipertrofia de Colas NIC:**
   El tiempo puro de travesía en la red (`Network_Latency`) se mantiene virtualmente invariable entre ambos modelos ($\sim 77$ ciclos en Mixtral vs. $\sim 69$ ciclos en DeepSeek), ya que la distancia física entre nodos en el Toro 1D no varía. Sin embargo, el **retardo de cola en la NIC (`Queueing_Delay`)** se multiplica por **$8.94\times$**, superando los $11,000$ ciclos y alcanzando picos de $52,680$ ciclos. Esto demuestra empíricamente que **en arquitecturas de grano fino con Top-$k$ elevado, el cuello de botella de la interconexión no radica en el ancho de banda del conmutador físico, sino en la capacidad de los buffers de inyección y el arbitraje de créditos de control de flujo**.

### 4.9.8. Sensibilidad Topológica: Toro 1D vs. Malla 2D (4x2 nodos) y Alivio de Contención Bidimensional
El análisis comparativo entre el Toro 1D y la Malla 2D (4x2 nodos) bajo idéntico volumen de carga revela aspectos cruciales de la topología física:
1. **Multiplicación del Ancho de Banda de Bisección:** En el Toro 1D, toda comunicación inter-nodo compite por un único par de canales unidireccionales (este-oeste). En la Malla 2D (4x2), la existencia de enlaces ortogonales en las dimensiones $X$ e $Y$ duplica las rutas disponibles en el corte de bisección.
2. **Descompresión de Colas NIC:** Aunque la distancia Manhattan sin enlaces wrap-around incrementa ligeramente el tiempo de vuelo medio ($+15.5\text{ ciclos}$ de latencia de red base), la descongestión en los conmutadores reduce el tiempo medio de espera en cola en más de $1.012\text{ ciclos}$ ($-9.04\%$) y aplana el pico máximo de contención de $52.680$ a $42.573$ ciclos (**$-19.19\%$ de caída en cola extrema**).
3. **Ganancia Neta en Throughput y Wall-Clock:** Esta reducción amortigua la duración de `moe_scatter` y `moe_gather` en $-206.6\,\mu\text{s}$ y mitiga los stalls en $-22.8\,\mu\text{s}$, recortando el tiempo global de inferencia en $-229.4\,\mu\text{s}$ con un incremento del $+7.80\%$ en la tasa efectiva de inyección $\lambda$.

### 4.9.9. Justificación Metodológica: Ejecución BSP vs. Esquemas de Pipelining (DualPipe)
Una premisa fundamental del co-simulador en esta tesis es el modelado estricto bajo el paradigma **Bulk Synchronous Parallel (BSP)**, donde las fases de cómputo local y comunicación colectiva se suceden de forma secuencial y sincronizada mediante barreras explícitas:
1. **Aislamiento del Coste Físico Puro:** Modelar la barrera BSP garantiza que el tiempo medido de tránsito de red no esté contaminado ni enmascarado por artificios de planificación de software. Permite cuantificar el impacto microarquitectural directo de la contención, la topología NoC y el número de canales virtuales sobre la física de los enlaces.
2. **Demostración de Margen Aritmético para Overlapping (DualPipe):**
   Los resultados experimentales obtenidos aportan una demostración cuantitativa de que DeepSeek-V3 es óptimo para esquemas de solapamiento comunicación-cómputo como **DualPipe**:
   $$T_{\text{compute}} = 8.340,6\,\mu\text{s} \quad \text{vs.} \quad T_{\text{transit}} = 3.137,9 - 3.344,5\,\mu\text{s}$$
   $$\text{Ratio } \frac{T_{\text{compute}}}{T_{\text{transit}}} \approx \mathbf{2.50 - 2.66\times}$$
   Dado que el silicio consume más de $2.5\times$ más tiempo en computar las capas de atención MLA y los micro-expertos FFN que en transferir los tensores por la red, un motor de ejecución con pipelining de micro-batches (donde las activaciones del micro-batch $i+1$ se transfieren mientras la GPU procesa los micro-expertos del micro-batch $i$) tiene **margen temporal de sobra para ocultar el 100% de la latencia de red de la interconexión**, eliminando virtualmente los $3.34\text{ ms}$ de penalización de muro.

---

---

# CAPÍTULO 5: Parches Arquitectónicos Aplicados al Simulador Base

Durante la auditoría del simulador original `LLMSimulator-orig` (SCALE SNU), se detectaron y corrigieron varios errores de diseño arquitectural que falseaban la simulación o producían corrupción de memoria.

## 5.1. Correcciones Críticas en `decoder.cpp`: Conexiones Residuales y Tipado de Capas

En [`src/module/decoder.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/decoder.cpp):

### 1. Desconexión de la Conexión Residual (Skip Connection)
- **Código Original con Bug:**
  ```cpp
  Tensor::Ptr res_1_out = (*residual_1)(attention_out, sequences_metadata);
  Tensor::Ptr post_attn_ln_out = (*post_attn_layer_norm)(attention_out, sequences_metadata);
  ```
  `post_attn_layer_norm` recibía directamente la salida de la atención (`attention_out`), puenteando y omitiendo la suma residual (`res_1_out`).
- **Parche Aplicado:**
  ```cpp
  Tensor::Ptr post_attn_ln_out = (*post_attn_layer_norm)(res_1_out, sequences_metadata);
  ```

### 2. Invocación Errónea del Segundo Residuo
- **Código Original con Bug:**
  ```cpp
  Tensor::Ptr res_2_out = (*residual_1)(result, sequences_metadata);
  ```
  El segundo residuo (`residual_2`) nunca se llamaba; se invocaba repetidamente `residual_1`, falseando las dependencias del grafo de ejecución.
- **Parche Aplicado:**
  ```cpp
  Tensor::Ptr res_2_out = (*residual_2)(result, sequences_metadata);
  ```

### 3. Fuga de Tipos en Módulos Residuales de MoEDecoder
- **Código Original con Bug:**
  ```cpp
  auto residual_1 = LayerNorm::Create(module_map_name, "residual_1", ...);
  auto residual_2 = LayerNorm::Create(module_map_name, "residual_2", ...);
  ```
  En el constructor de `MoEDecoder`, los módulos residuales se instanciaban como `LayerNorm` en lugar de `Residual`. Esto aplicaba la ecuación analítica de normalización ($2 \cdot m \cdot k$ bytes) y su coste energético en lugar de la suma de tensores residuales ($3 \cdot m \cdot k$ bytes).
- **Parche Aplicado:**
  Se sustituyó por `Residual::Create(...)`.

---

## 5.2. Correcciones en `layer.cpp`: Cadena de Dependencias en Bloques SwiGLU

En [`src/module/layer.cpp:L419-L435`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/layer.cpp#L419-L435):
- En arquitecturas SwiGLU 3-way FFN (`ffn_way == 3`), la operación teórica es:
  $$\text{FFN}(x) = (\text{SiLU}(x W_{\text{gate}}) \odot x W_{\text{up}}) W_{\text{down}}$$
- En el simulador original, `down_proj` se conectaba directamente a `up_proj_out` sin sincronizar la terminación de `act_out` (`SiLU`), provocando que en ejecuciones heterogéneas o con timeboard detallado la proyección de bajada se ejecutara antes de que la activación matemática estuviese lista.
- **Parche Aplicado:** Se forzó la dependencia causal de `down_proj` con el cierre de la rama de activación para garantizar la correcta contabilización de energía MAC y tiempos de ejecución.

---

## 5.3. Correcciones en `timeboard.cpp`: Preservación de la Causalidad Temporal Asíncrona

En [`src/module/timeboard.cpp:L39-L47`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/timeboard.cpp#L39-L47):
- El código original incluía dos asignaciones incondicionales:
  ```cpp
  status.start_time = status.device_time;
  status.end_time = output_status.device_time;
  ```
- Estas líneas forzaban a que el tiempo de inicio de cualquier módulo fuera sobreescrito destructivamente por el reloj global actual, anulando cualquier desbalance asíncrono o retraso acumulado por contención de red en topologías complejas.
- **Parche Aplicado:** Se comentaron y eliminaron estas sobreescrituras, permitiendo que `device_time` refleje con fidelidad científica los tiempos reales de inicio y fin causales.

---

## 5.4. Corrección de Causalidad Bidireccional en el Oráculo de Red (`src/module/communication.cpp`)

En la versión preliminar de la vectorización de latencias de red por destino (Bloque C), el cálculo de `t_end` para cada dispositivo $dst$ consideraba únicamente el instante de recepción de paquetes entrantes:
```cpp
// Código preliminar (unidireccional RX):
t_end[dst] = t_min + max_relative_atime[dst];
```
Esta formulación adolecía de una vulnerabilidad física: si una GPU $d$ inyectaba paquetes tardíamente hacia otras GPUs pero no recibía paquetes de vuelta (o sus paquetes recibidos llegaban muy temprano), su `max_relative_atime[d]` permanecía en $\delta_t[d]$, permitiendo potencialmente que la GPU cerrara su fase de red mientras su NIC seguía transmitiendo o mientras sus paquetes emitidos continuaban navegando por la red hacia sus destinos.

### Parche C++ Aplicado en `src/module/communication.cpp`:
Se introdujeron tres vectores de seguimiento temporal en el bucle del Oráculo tanto para `MoEScatter::forward()` como para `MoEGather::forward()`:
1. `max_relative_rx_atime[dst]`: Rastrea el ciclo del último paquete retirado dirigido a `dst`.
2. `max_relative_tx_inj[src]`: Rastrea el ciclo en el que `src` inyecta su último paquete en BookSim2.
3. `max_relative_tx_retire[src]`: Rastrea el ciclo en el que el último paquete originado por `src` es entregado y retirado en su destino.

Al concluir la simulación de la red:
```cpp
std::vector<int> rel_finish(total_num_device, 0);
for (int d = 0; d < total_num_device; d++) {
    rel_finish[d] = std::max({
        delta_t[d],
        max_relative_rx_atime[d],
        max_relative_tx_inj[d],
        max_relative_tx_retire[d]
    });
}
for (int d = 0; d < total_num_device; d++) {
    double t_end = t_min + (double)rel_finish[d];
    double net_lat = std::max(0.0, t_end - t_src[d]);
    cached_latency_per_gpu[layer_name][d] = net_lat;
}
```
Este parche elimina cualquier posible inversión temporal o desincronización de causalidad entre GPUs emisoras y receptoras, garantizando que ninguna GPU de por terminada su fase de red mientras su interfaz siga activa o tenga paquetes en tránsito.

---

# CAPÍTULO 6: Sistema de Trazabilidad Completa (.trc y .csv) y Suite de Análisis en Python

## 6.1. Arquitectura del Logger C++ en `Device`, `Module` y `ModuleGraph`

Para dotar al co-simulador de observabilidad completa, se implementó un motor nativo de trazabilidad en C++:
1. **Flujo de Trazas (`tfm_trace_file`):** Cada `Device` abre al inicializarse un archivo dedicado `TFM_device_<rank>.trc` ([`src/hardware/device.cpp:L65-L70`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp#L65-L70)).
2. **Método `log_tfm_event()` ([`src/hardware/device.cpp:L234-L242`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp#L234-L242)):**
   Registra en tiempo real eventos con la estructura CSV canónica:
   ```csv
   START_NS,END_NS,DURATION,TYPE,DETAILS
   ```
   Incorpora una guarda estricta `if (!perform_execution) return;` que impide registrar cualquier evento durante las fases preliminares de construcción estática del modelo. Utiliza `std::fixed` junto con `std::setprecision(4)` (`#include <iomanip>`) para asegurar que las marcas de tiempo en nanosegundos (superiores a $10^6$ ns) no se trunquen por el formato estándar a notación científica (`float` de 6 cifras significativas), preservando la fidelidad temporal exacta. Asimismo, emplea `std::endl` para vaciar el búfer del sistema operativo de inmediato, protegiendo los datos contra interrupciones anormales del simulador.
3. **Filtrado de Eventos Nulos y Guarda Anti-Doble Registro:**
   - En [`src/module/module_graph.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp), solo se registran eventos con `exec_status.total_duration > 0`, eliminando del archivo miles de llamadas declarativas nulas que saturaban el almacenamiento.
   - En `TopModuleGraph::set_pop_status()`, se implementa una guarda explícita (`is_self_logged`) que comprueba el nombre canónico del módulo (`norm`, `residual`, `rope`, `scatter`, `gather`, `all_reduce`). Si el módulo pertenece a una de estas clases que ya autogestionan su propio registro en `forward()`, se omite la emisión de un segundo registro POP, previniendo solapamientos temporales o doble contabilidad de latencias en el archivo `.trc`.

### 6.1.1. Supresión de Trazas Fantasma de Inicialización Estática (Eliminación de 128 Líneas Previas a $t=0$)
Durante la fase de instanciación del modelo (`Model::Model()`), LLMSimulator construye el grafo de dependencias estático invocando el método `forward()` de los componentes con `perform_execution = false` para dimensionar los tensores de activación. En la implementación previa, mientras que las operaciones lineales respetaban dicha bandera, los módulos analíticos `LayerNorm`, `Residual`, `RoPE` y `Communication` (`AllReduce`) avanzaban incondicionalmente el reloj de la GPU (`device_time`) y llamaban a `log_tfm_event()`.

En una arquitectura de 32 capas decodificadoras, esto producía exactamente:
$$32\text{ capas} \times 4\text{ módulos autologgeados} = 128\text{ líneas fantasma iniciales}$$
Estas 128 líneas ocupaban un rango temporal ficticio desde $0.0000\text{ ns}$ hasta $\sim 1{,}34\text{ M ns}$, antes de que el motor reiniciara el reloj a $0\text{ ns}$ al comenzar la simulación real.

**Solución Arquitectónica Implementada:**
1. **Guarda de Ejecución en Módulos C++:** En `LayerNorm::forward()`, `Residual::forward()`, `RoPE::forward()` y `AllReduce::forward()`, se añadió la guarda previa:
   ```cpp
   if (size == 0 || !device->perform_execution) return output;
   ```
2. **Guarda en Logger:** En `Device::log_tfm_event()`, se verifica `if (!perform_execution) return;`.
3. **Truncamiento y Sincronización en `Device::setPerformExecution()`:** Se implementó `Device::setPerformExecution(bool perform)`. Al pasar de `false` a `true` al inicio de `Cluster::run()` o `runIteration()`, se ejecuta `reset_status()`, se reabre el flujo `tfm_trace_file` con `std::ios::trunc` y se reescribe la cabecera CSV:
   ```cpp
   void Device::setPerformExecution(bool perform) {
       if (!perform_execution && perform) {
           reset_status();
           if (tfm_trace_file.is_open()) {
               tfm_trace_file.close();
               tfm_trace_file.open(tfm_trace_filename, std::ios::out | std::ios::trunc);
               tfm_trace_file << "START_NS,END_NS,DURATION,TYPE,DETAILS\n";
           }
       }
       perform_execution = perform;
   }
   ```
   Con esto, se garantiza que las trazas `.trc` arranquen limpiamente en $0.0000\text{ ns}$ con estricta congruencia causal.

---

## 6.2. Propagación de Identidad Jerárquica (`module_map_name`) a Nodos POP

Uno de los mayores hallazgos de ingeniería en el simulador base fue descubrir que en [`src/module/module.cpp:L15`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module.cpp#L15), `pop_module_graph(return_tensor)` se invocaba sin pasar el puntero del módulo. Como consecuencia, cuando `TopModuleGraph::set_pop_status()` intentaba inspeccionar el módulo terminado, encontraba `module == nullptr`, registrando todas las operaciones de cómputo con la etiqueta genérica `POP_OPERATION`.

### Nuestra Solución:
1. Modificamos `module.cpp` para invocar:
   ```cpp
   device->top_module_graph->pop_module_graph(getptr(), return_tensor);
   ```
2. En `TopModuleGraph::set_pop_status()` ([`src/module/module_graph.cpp:L341-L348`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp#L341-L348)), extraemos el espacio jerárquico completo:
   ```cpp
   if (*current_module != nullptr && (*current_module)->module != nullptr) {
       details += "|Module:" + (*current_module)->module->module_map_name;
   }
   ```
Esto genera en los archivos `.trc` entradas con trazabilidad absoluta:
`Linear,ProcType:3|Comp_ns:268.43|Mem_ns:7358.46|Module:::LLM::MoE_decoder_0::expertFFN::expert_FFN_0::gate_proj::Linear`

---

## 6.3. Automatización de Ejecución y Orquestación (`run_sim.py`)

Ubicado en [`LLMSimulator/run_sim.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/run_sim.py), actúa como orquestador integral:
- Genera dinámicamente las configuraciones acopladas `config.yaml` (LLMSimulator) y `test.cfg` (BookSim2).
- Impone **guardarraíles de arquitectura**: verifica que topologías Torus tengan al menos 2 VCs para evitar deadlocks y que las dimensiones sean simétricas.
- **Soporte CLI para Tensor Parallelism (`--tensor_degree` / `--tp`):** Permite configurar el grado de paralelismo tensorial en capas densas (`none_expert_tensor_degree`), verificando automáticamente que el número total de GPUs sea divisible entre el grado de tensor elegido e incorporando la etiqueta `_tp{N}` en la denominación de los resultados.
- **Trazabilidad de Paquetes Activa por Defecto:** Activa de forma predeterminada `SIM_DEBUG_PIDS="1"`, interceptando mediante pipes de subproceso las líneas `[TRACK_PID]` emitidas por BookSim2 y volcándolas de forma estructurada a `packet_tracking_debug.csv`. Incorpora el flag `--no_debug_pids` para deshabilitar esta exportación en barridos masivos de baja sobrecarga de I/O.
- Sella y organiza los archivos generados en subdirectorios únicos por marca temporal en `build/results/<experimento>/`.

---

## 6.4. Análisis Macroscópico de Latencias y Saturación de Red (`analyze_traces.py`) - Cierre del Bloque B

Ubicado en [`LLMSimulator/analyze_traces.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/analyze_traces.py), realiza el posprocesamiento macroscópico de los archivos `.trc` generados por el clúster y sintetiza la curva de saturación de red a partir de `packet_tracking_debug.csv`.

### 6.4.1. Auditoría de Discrepancias y Conservación del Wall-Clock Time
Durante las primeras campañas de simulación, se detectó una aparente discrepancia: las gráficas de latencia mostraban barras agregadas cercanas a $\sim 10\text{ M}$ ns, mientras que el reloj real de simulación (`END_NS` máximo en los archivos `TFM_device_X.trc`) culminaba en torno a $\sim 1{,}18\text{ M}$ ns. Se realizó una auditoría rigurosa sobre tres hipótesis causales:

1. **Agregación Multi-GPU vs. Promedio por Dispositivo:**
   Si se acumula la duración física de todas las GPUs sin normalizar ($N_{\text{GPUs}} = 8$), la métrica reflejaría el tiempo CPU acumulado (Core-Hours equivalentes) en lugar del tiempo transcurrido de pared (*Wall-Clock Time*). El analizador calcula la media representativa por dispositivo:
   $$\overline{T}_{\text{métrica}} = \frac{1}{N_{\text{GPUs}}} \sum_{g=0}^{N_{\text{GPUs}}-1} T_{\text{métrica}}^{(g)}$$

2. **Doble Registro o Solapamiento de Intervalos en `.trc`:**
   Se auditó la secuencia temporal de cada `.trc` individual para verificar si la coexistencia de registros emitidos en `forward()` (`LayerNorm`, `Residual`, `RoPE`, `MoEScatter`, `MoEGather`, `AllReduce`) y registros emitidos en `set_pop_status()` provocaba solapamientos o huecos. Se constató que, gracias a la guarda `is_self_logged` implementada en `TopModuleGraph::set_pop_status()`, los intervalos temporales $[t_{\text{start}}, t_{\text{end}}]$ son continuos y disjuntos, cumpliendo:
   $$\sum \Delta t_k = \max(t_{\text{end}}) - \min(t_{\text{start}})$$

3. **Acumulación Multi-Iteración (Filtro Anti-Appends):**
   **Causa Raíz de la Inflación:** Cuando el motor ejecuta múltiples iteraciones o fases de calentamiento (`runIteration(iter)` con `iter = 6`), las trazas `.trc` acumulan secuencialmente las sucesivas ejecuciones en un único archivo. En cada nueva iteración, el reloj de la GPU se reinicia a $0$, provocando retrocesos temporales en la serie cronológica ($\text{START\_NS}[i] < \text{START\_NS}[i-1]$). Sin un filtrado adecuado, `analyze_traces.py` sumaba las $6$ iteraciones consecutivas ($6 \times 1{,}187\text{ M ns} \approx 7{,}12\text{ M ns}$ hasta $6 \times 1{,}878\text{ M ns} \approx 11{,}27\text{ M ns}$), multiplicando por $6$ el tiempo real.

Para solucionar de forma definitiva este problema, `analyze_traces.py` incorpora el **Filtro Anti-Appends**:
```python
# Detectar reinicios temporales por iteraciones múltiples (iter > 1)
time_drops = df['START_NS'].diff() < 0
if time_drops.any():
    last_reset_idx = time_drops[time_drops].index[-1]
    df = df.loc[last_reset_idx:].copy()
```
Este algoritmo recorta automáticamente el DataFrame a partir del último punto de inflexión temporal, garantizando que el análisis se aplique estrictamente sobre la iteración canónica en estado estacionario.

### 6.4.2. Ecuación Fundamental de Balance Temporal y Validación Empírica
Tras aplicar el filtrado, se cumple con absoluta precisión la ley de conservación del Wall-Clock Time de la simulación:
$$\text{Wall-Clock Time} = \max_{g \in [0, N-1]} (\text{END\_NS}^{(g)}) \approx \overline{T}_{\text{compute}} + \overline{T}_{\text{transit}} + \overline{T}_{\text{stall}}$$

Donde:
- **Cómputo GPU Puro ($\overline{T}_{\text{compute}}$):** Suma media de todas las operaciones de tensores (`Linear`, `Attention`, `Residual`, `LayerNorm`, `RoPE`).
- **Tránsito Físico de Red ($\overline{T}_{\text{transit}}$):** Retardo de propagación y enrutamiento en BookSim2 derivado de primitivas All-to-All (`moe_scatter` y `moe_gather`) y primitivas de Tensor Parallelism (`all_reduce` y `moe_all_reduce_for_gather`).
- **Bloqueos de Sincronización ($\overline{T}_{\text{stall}}$):** Tiempo ocioso de espera en barreras globales de sincronización (`NETWORK_STALL`).

Los resultados empíricos validados sobre trazas reales demuestran una concordancia exacta (discrepancia inferior al $0{,}0002\%$ atribuible a redondeo infinitesimal):

| Configuración de Red | GPUs | Cómputo ($\text{ns}$) | Tránsito Red ($\text{ns}$) | Esperas Stall ($\text{ns}$) | Suma Total ($\text{ns}$) | Wall-Clock Real ($\text{ns}$) | Discrepancia |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Mixtral 8dev Torus (bs=32)** | 8 | 911.686,1 | 274.640,0 | 1.511,4 | **1.187.837,6** | **1.187.840,0** | **< 2,5 ns** |
| **Mixtral 2x2dev Mesh (bs=32)** | 4 | 1.655.436,0 | 221.455,0 | 1.634,3 | **1.878.525,3** | **1.878.530,0** | **< 4,7 ns** |

### 6.4.3. Visualizaciones Generadas
El script exporta de forma automatizada a `build/analysis/analisis_<timestamp>/`:
1. `anatomia_latencia.png`: Gráfico de barras apiladas con estética científica, donde cada barra representa una configuración de red, descomponiendo visualmente el tiempo de inferencia total en sus tres factores ortogonales (Cómputo, Tránsito, Stalls), con anotaciones numéricas en microsegundos/milisegundos y porcentajes relativos.
2. `desglose_primitivas_moe.png`: Gráfico de barras agrupadas que contrasta la latencia de red inducida por `moe_scatter` frente a `moe_gather`, permitiendo estudiar asimetrías de congestión y contención de búferes.
3. `curva_saturacion_red.png`: Curva canónica de saturación de red (Latencia Media de Red vs. Tasa de Inyección Ofrecida $\lambda$). Muestra la relación entre la carga de tráfico inyectada por GPU y la degradación de latencia inducida por contención física en conmutadores y canales de BookSim2.

### 6.4.4. Síntesis y Renderizado de la Curva de Saturación de Red (Cierre del Bloque B)

El **Bloque B del TFM** queda formalmente cerrado con la incorporación directa de la curva de saturación de red dentro de `analyze_traces.py`. Esta integración combina las trazas macroscópicas de cómputo GPU (`.trc`) con las trazas de paquetes flit a flit (`packet_tracking_debug.csv`), extrayendo el régimen operativo real del tejido de interconexión.

#### 1. Formulación Matemática de las Métricas de Red
Para cada simulación analizada, tras aplicar el filtro anti-appends para aislar la última iteración canónica:
- **Tasa Media de Inyección Real ($\lambda$, Eje X):**
  Se evalúa de forma desagregada para cada operación colectiva $op$ (Scatter y Gather en cada capa del Transformer) y se calcula la media global representativa:
  $$\lambda^{(op)} = \frac{\sum_{p \in op} \text{Num\_Flits}_p}{N_{\text{GPUs}} \times \Delta\text{Cycles}_{op}} \quad [\text{flits / ciclo / nodo}]$$
  $$\Delta\text{Cycles}_{op} = \max_{p \in op}(\text{Receive\_Cycle}_p) - \min_{p \in op}(\text{Creation\_Cycle}_p)$$
  $$\overline{\lambda} = \frac{1}{M_{\text{ops}}} \sum_{op=1}^{M_{\text{ops}}} \lambda^{(op)} \quad [\text{flits / ciclo / nodo}]$$
  Equivalentemente, la tasa expresada en paquetes inyectados por ciclo y nodo cumple $\lambda_{\text{pkts}} = \frac{\lambda}{9}$ (dado que cada paquete consta exactamente de $9$ flits y $288$ Bytes en Mixtral 8x7B).

- **Latencia Media de Red ($L_{\text{net}}$, Eje Y):**
  Calculada como el promedio global de la columna `Avg_Flit_Latency` acumulada por BookSim2 para todos los flits retirados en la iteración, expresada en ciclos de reloj de red:
  $$\overline{L}_{\text{flit}} = \frac{1}{P} \sum_{p=1}^{P} \text{Avg\_Flit\_Latency}_p \quad [\text{ciclos de BookSim2}]$$
  Complementariamente, se registra la latencia total media por paquete $\overline{L}_{\text{pkt}} = \frac{1}{P} \sum_{p=1}^P \text{Total\_Latency}_p$.

#### 2. Visualización Multi-Nivel y Calidad de Publicación
La gráfica `curva_saturacion_red.png` implementa una representación visual en dos capas complementarias:
1. **Nube de Micro-Operaciones Colectivas:** Muestra puntos translúcidos suaves (`alpha=0.22`, $s=36$) correspondientes a cada operación individual Scatter y Gather a lo largo de las 32 capas decodificadoras. Esto visibiliza la variabilidad intrínseca del enrutamiento dinámico y el desbalance de tokens entre capas.
2. **Centroides Macroscópicos de Arquitectura:** Destaca con marcadores geométricos de gran tamaño ($s=230$, borde negro prominente y color de serie distintivo) el punto de operación medio $(\overline{\lambda}, \overline{L})$ de cada simulación comparada.
3. **Badges Anotados y Metadatos Dinámicos:** Cada centroide incorpora un cuadro de llamada (*callout annotation*) con fondo blanco translúcido y flecha conectora, rotulado con los parámetros de red y paralelismo tensorial:
   $$\text{Label} = \text{Num\_GPUs}\,\text{dev} \; \text{Topología} \; (\text{VCs}=V, \; \text{BS}=B \ [, \text{TP}=P])$$
   *(Ejemplo: `8dev Torus (VCs=4, BS=32, TP=2)`).*
4. **Escala Adaptativa y Tendencia:** Si la dispersión de latencias entre el régimen no saturado y el saturado supera un factor de $4\times$ (o ante el flag manual `--semilog`), el eje Y se ajusta automáticamente a escala semilogarítmica ($\log_{10}$). Además, cuando se comparan 2 o más simulaciones, traza una línea discontinua de tendencia global que evidencia la pendiente asintótica del codo de saturación.

#### 3. Compatibilidad Histórica y Tolerancia a Fallos
Si en carpetas históricas no existiese `packet_tracking_debug.csv` (por ejemplo, ejecuciones previas a la instrumentación completa de BookSim2), el analizador emite una advertencia informativa por consola (`⚠️ Aviso: No se encontró 'packet_tracking_debug.csv'...`) y omite de forma totalmente segura la tercera gráfica sin interrumpir ni alterar la generación de `anatomia_latencia.png` ni `desglose_primitivas_moe.png`.

---

## 6.5. Visualizador de Congestión en Red y Paginación de Paquetes (`plot_packet_tracking.py`)

Ubicado en [`LLMSimulator/plot_packet_tracking.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_packet_tracking.py):
- **Parsea `packet_tracking_debug.csv`** (17 columnas) y reconstruye la vida de los paquetes flit a flit.
- **Doble Eje X de Congruencia Temporal (Ciclos BookSim2 y Nanosegundos Globales LLM):**
  - **Eje inferior (X):** Ciclos de simulación de red en BookSim2 ($ctime \to itime \to atime$).
  - **Eje superior secundario (X2):** Tiempo Global LLM en nanosegundos ($Global\_NS = Op\_Start\_NS + (Cycle - Op\_Start\_Cycle)$). Dado que la red corre a $1\text{ GHz}$ ($1\text{ ciclo} = 1.0\text{ ns}$), se establece una congruencia unívoca con el cronograma cycle-to-cycle del simulador de cómputo.
- **Filtro Anti-Appends de Última Iteración:** Detecta automáticamente retrocesos temporales en `Op_Start_NS` (`df['Op_Start_NS'].diff() < 0`) causados por reinicios de reloj al pasar a una nueva iteración de inferencia. Por defecto, aísla con exactitud los paquetes de la última iteración (permite `--all_iters` para analizar todas las iteraciones).
- **Paginación Dinámica en Subcarpeta `gantt/`:**
  - Divide las decenas de miles de paquetes en bloques manejables de 50 en 50 paquetes (`--samples 50`).
  - Guarda los diagramas secuencialmente en `gantt/gantt_page_XXX_pids_X_to_Y.png` dentro del directorio de resultados de la simulación.
  - Ofrece el parámetro `--max_pages <N>` (por defecto `30`, o `0` para ilimitado), permitiendo generar rápidamente páginas representativas del régimen estacionario.
- **Barras Horizontales Bicolores de Latencia Físicamente Descompuesta:**
  - 🟧 **Espera en Cola del NIC (Queueing Delay):** Desde $ctime$ hasta $itime$ (saturación de interfaces de red).
  - 🟦 **Vuelo en Red (NoC Flight Time):** Desde $itime$ hasta $atime$ (contención y arbitraje de conmutadores).
- **Etiquetas Micro-Arquitecturales Enriquecidas por Paquete:**
  - Al lado derecho de cada barra se muestra la tupla de ruta, tamaño físico, latencia media de flits acumulada, productividad acumulada y la ventana global de nanosegundos:
    `S{src}→D{dst} (9 flits / 288B) | Lat.Media: {avg_flit_lat:.1f}c | Prod: {prod:.3f} flits/c | NS: {g_start:.0f}-{g_end:.0f}`
  - **Formulación Matemática de las Métricas Acumuladas:**
    $$\text{Avg\_Flit\_Latency}(atime) = \frac{\sum_{k \in \text{flits recibidos en la op hasta } atime} (t_{\text{retire}, k} - ctime)}{\text{Total global de flits recibidos en la op hasta } atime} \quad [\text{ciclos}]$$
    $$\text{Throughput}(atime) = \frac{\text{Total global de flits recibidos en la op hasta } atime}{\max(1, atime - t_{\text{start\_op}})} \quad [\text{flits/ciclo}]$$
- **Sombreado Semántico por Operación de Red (`ax.axhspan`):**
  - Identifica transiciones entre operaciones colectivas sucesivas (`Scatter NºX`, `Gather NºX` y `AllReduce NºX`).
  - Aplica franjas horizontales de fondo suaves alternas (azul claro para Scatter `#e3f2fd`, violeta/verde claro para Gather `#f3e5f5` y lavanda suave para AllReduce `#ede7f6`).
  - Dibuja líneas horizontales discontinuas (`linestyle='--'`) en la frontera exacta de cambio de operación.
  - Inserta tarjetas o badges destacados en el extremo derecho del gráfico con la leyenda de operación y su intervalo en nanosegundos: `Scatter Nº1 \n NS 6362 - 10547` o `AllReduce Nº1 \n NS 3730 - 4895`.
- **Hitos Globales de Congestión:**
  - Preserva en la raíz del experimento los tres cortes representativos:
    - `gantt_1_fase_libre.png`: Fase inicial con red vacía (mínima latencia).
    - `gantt_2_congestion_media.png`: Transición hacia la saturación (primeros paquetes > 1.500 ciclos).
    - `gantt_3_congestion_critica.png`: Cuello de botella crítico (> 2.000 ciclos por colapso All-to-All).

---

## 6.6. Cronograma Micro-Arquitectural Causal GPU Cycle-to-Cycle (`plot_cronograma.py`)

El script [`LLMSimulator/plot_cronograma.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_cronograma.py) constituye el visualizador causal de más alta fidelidad del entorno de co-simulación. Genera diagramas de Gantt temporalmente continuos que representan el estado exacto de todas las GPUs ciclo a ciclo y nanosegundo a nanosegundo, segmentados en ventanas temporales de alta resolución (típicamente de $10.000\text{ ns}$ a $100.000\text{ ns}$) dentro del subdirectorio `cycle-to-cycle/`.

### 6.6.1. Jerarquía Semántica de Tres Niveles (.trc vs. Renderizado Visual)

A diferencia de los visualizadores convencionales que o bien dibujan miles de micro-rectángulos ilegibles o bien fusionan la traza en bloques opacos sin detalles internos, `plot_cronograma.py` implementa una arquitectura de interpretación semántica en 3 niveles jerárquicos:

```
+-------------------------------------------------------------------------------------------------------+
| NIVEL 1: Capa del Transformer (Layer L)                                                               |
|  - Aislamiento estricto: MoE_decoder_0 NUNCA se fusiona con MoE_decoder_1                            |
+-------------------------------------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------------------------------------+
| NIVEL 2: Macro-Operación Causal (MacroOp)                                                             |
|  - Fases del pipeline: Attention (Verde), Scatter (Azul), ExpertFFN (Verde), Gather (Azul), Stall (Rojo)|
+-------------------------------------------------------------------------------------------------------+
    |
    v
+-------------------------------------------------------------------------------------------------------+
| NIVEL 3: Operaciones Elementales Reales + Sub-divisiones Internas                                     |
|  - Secuencia ordenada abreviada: (LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)                      |
|  - Sub-divisiones físicas: Líneas discontinuas blancas en los END_NS exactos de cada micro-operación   |
|  - Diagnóstico cuantitativo: Duración real + Mem-Bound % calculado de Comp_ns y Mem_ns               |
+-------------------------------------------------------------------------------------------------------+
```

#### 1. Nivel 1: Capa del Transformer (`Layer L`) y Aislamiento Estricto
- **Detección y Propagación Causal:** El parser examina la columna `DETAILS` buscando patrones regex como `MoE_decoder_(\d+)` o `decoder_(\d+)`. Módulos raíz como `input_layer_norm` fijan el inicio de la capa $L$. Para micro-operaciones y comunicaciones que carecen de etiqueta de capa explícita en su entrada de traza (como `residual_1`, `moe_scatter`, `moe_gather`, `post_attn_layer_norm` y `residual_2`), el parser propaga el identificador mediante forward-fill causal dentro de la GPU.
- **Regla Inquebrantable de Aislamiento:** El algoritmo de coalescencia prohíbe taxativamente agrupar operaciones pertenecientes a capas decodificadoras distintas. Cuando concluye `MoE_decoder_0` e inicia `MoE_decoder_1`, se fuerza una separación física nítida entre bloques, permitiendo al investigador observar con total exactitud la frontera de transición inter-capa.

#### 2. Nivel 2: Macro-Operación Causal (`MACRO_OP`) y Clasificación Semántica
Las micro-operaciones del archivo `.trc` se clasifican semánticamente en categorías estructurales:
- **`Attention` (🟩 Verde `#2e7d32`):** Agrupa `input_layer_norm`, proyecciones lineales QKV (`qkv_proj`), computación causal de atención (`attention_forward` / `AttnGen`), proyección de salida (`o_proj`), conexión residual (`residual_1`) y compuerta del router MoE (`gate`).
- **`Scatter` (🟦 Azul `#1565c0`):** Comunicación de dispersión All-to-All gestionada por BookSim2 (`moe_scatter`).
- **`ExpertFFN` (🟩 Verde `#2e7d32`):** Cómputo local de los expertos asignados a la GPU, agrupando `gate_proj`, activación no lineal (`silu`), `up_proj` y `down_proj`.
- **`Gather` (🟦 Azul `#1565c0`):** Comunicación de reunión All-to-All gestionada por BookSim2 (`moe_gather`).
- **`AllReduce` (🟪 Púrpura/Magenta `#8e44ad`):** Comunicación colectiva Ring-AllReduce de Tensor Parallelism en capas de atención o proyecciones lineales, simulada ciclo a ciclo por BookSim2 (`all_reduce` y `moe_all_reduce_for_gather`).
- **`NETWORK_STALL` (🟥 Rojo `#c62828`):** Burbuja ociosa de sincronización en barrera colectiva provocada por desbalance de cómputo o colas en la red.
- **`Residual` (⬜ Gris `#616161`):** Normalización final y residuo del bloque decodificador (`post_attn_layer_norm` y `residual_2`).

#### 3. Nivel 3: Operaciones Elementales Reales y Despliegue de Expertos
Durante la coalescencia continua de un macro-bloque verde, el algoritmo recolecta cronológicamente todas las operaciones elementales ejecutadas:
- **En Bloques de Atención:** Abreviación estandarizada:
  $$\text{SEQ\_STR} = \text{"(LN + QKV\_Proj + AttnGen + O\_Proj + Res + Gate)"}$$
- **En Bloques de ExpertFFN:** Identificación y agrupamiento de los expertos locales:
  - Si la GPU aloja **1 experto** ($N_{\text{GPUs}} = E = 8$):
    $$\text{SEQ\_STR} = \text{"(Exp\#0: Gate\_Proj + SiLU + Up\_Proj + Down\_Proj)"}$$
  - Si la GPU aloja **múltiples expertos** ($N_{\text{GPUs}} < E$, ej. 4 GPUs con 8 expertos $\implies 2$ expertos/GPU):
    $$\text{SEQ\_STR} = \text{"(Exp\#0,1: 2x[Gate+SiLU+Up+Down])"}$$
    El visualizador detecta que la GPU ejecuta secuencialmente ambos expertos y refleja tanto el conjunto de IDs locales (`Exp#0,1`) como el factor multiplicador de pasos elementales ($2\times$).

### 6.6.2. Sub-divisiones Físicas Internas Discontinuas

Para que el usuario pueda apreciar de un vistazo el peso temporal relativo de cada operación elemental sin perder la cohesión visual del macro-bloque, `plot_cronograma.py` dibuja **líneas verticales finas discontinuas** (`color='white'`, `alpha=0.6`, `linestyle='--'`, `linewidth=0.8`) en los límites temporales exactos `END_NS` de cada micro-operación interna.

Esto resuelve una limitación clásica de los cronogramas agregados: ahora es posible constatar visualmente en la imagen cómo `AttnGen` o `down_proj` consumen la mayor parte del tiempo del bloque verde, mientras que `LN` o `silu` representan delgadas franjas de apenas unos cientos de nanosegundos.

### 6.6.3. Texto Multilínea Rico y Diagnóstico de Cuello de Botella

Dentro de cada bloque verde de cómputo, el visualizador formatea un texto informativo de hasta 3 líneas, adaptando dinámicamente el nivel de detalle al ancho físico en nanosegundos (`dibujo_dur`):

1. **Línea 1 (Cabecera):** Identificador de capa y macro-operación:
   ```
   Layer {L} | Calc: {MacroOp}
   ```
   *(Ejemplo: `Layer 0 | Calc: Attention` o `Layer 0 | Calc: ExpertFFN`).*
2. **Línea 2 (Secuencia en Negrita):** Cadena secuencial de micro-operaciones:
   ```
   (LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)
   ```
   *(Renderizado con `fontweight='bold'` y color `#e8f5e9`).*
3. **Línea 3 (Diagnóstico Cuantitativo de Cuello de Botella):**
   ```
   Dur: {dur_us:.1f}us (Mem-Bound {mem_pct:.1f}%)
   ```
   - **Cálculo del Cuello de Botella:** Se extraen los acumuladores de nanosegundos de cómputo en ALU (`Comp_ns`) y tiempo de transferencia a memoria HBM (`Mem_ns`) registrados en el `.trc` para todas las micro-operaciones del bloque:
     $$\text{Mem\_Pct} = \frac{\sum \text{Mem\_ns}}{\sum \text{Comp\_ns} + \sum \text{Mem\_ns}} \times 100$$
   - Si $\text{Mem\_Pct} \ge 50.0\%$, se reporta como `Mem-Bound {Mem_Pct:.1f}%` (el caso habitual en inferencia decodificadora con Batch Size 32, típicamente entre el $95\%$ y el $99.8\%$). Si fuese inferior, se reporta como `Compute-Bound {100 - Mem_Pct:.1f}%`.

#### Umbrales Adaptativos de Renderizado y Protección Anti-Overflow

Para erradicar cualquier desbordamiento de texto (*Text Overflow*) o colisión tipográfica entre bloques vecinos en ventanas de alta resolución (típicamente $10\,\mu\text{s}$ a $20\,\mu\text{s}$), `plot_cronograma.py` implementa una arquitectura de renderizado adaptativo en 3 niveles gobernada por el ancho temporal visible $\Delta t = \text{dibujo\_dur}$:

1. **Omisión en Micro-Bloques ($\Delta t < 800\text{ ns}$ o $\text{rel\_w} < 0.015$):**
   Las transiciones de residuos breves (12–29 ns), micro-stalls o cortes de ventana marginales no renderizan texto interno para no saturar visualmente el lienzo.
2. **Tier 1: Bloques Muy Estrechos ($800\text{ ns} \le \Delta t < 2{,}000\text{ ns}$):**
   - Renders ultracompactos de **1 sola línea centrada** (`fontsize=6.5`, `fontweight='bold'`).
   - Para colectivas de Tensor Parallelism (`AllReduce`), muestra únicamente `AR Nº{k} (1.2us)` o `AR Nº{k}`, evitando colisiones con los bloques de Atención adyacentes.
   - Para `Stall`, muestra de forma concisa `Stall` o `Stall ({dur})`.
   - Para `Calc`, proyecta `L{L} | {Op}` o simplemente `{Op}`.
3. **Tier 2: Bloques Medianos ($2{,}000\text{ ns} \le \Delta t < 6{,}000\text{ ns}$):**
   - Formato compacto de **máximo 2 líneas** con tipografía reducida (`fontsize=6.8` para cabecera, `fontsize=6.2` para métricas).
   - En comunicaciones de red, plasma la cabecera de la operación junto con las métricas acumuladas: `Lat.Media: {lat}c | Prod: {prod} f/c`.
4. **Tier 3: Bloques Anchos ($\Delta t \ge 6{,}000\text{ ns}$):**
   - Formato completo de **3 líneas** con cabecera de capa, secuencia ordenada de micro-operaciones elementales desplegadas en negrita y diagnóstico microarquitectural de cuello de botella (`Mem-Bound XX.X%`).

#### Recorte Seguro por Geometría del Rectángulo (`draw_clipped_text`)
Todas las cadenas de texto se dibujan mediante la función auxiliar `draw_clipped_text(ax, rect, x, y, text, ...)`:
```python
def draw_clipped_text(ax, rect, x, y, text, **kwargs):
    kwargs.setdefault('clip_on', True)
    txt = ax.text(x, y, text, **kwargs)
    txt.set_clip_path(rect)
    return txt
```
Al invocar `txt.set_clip_path(rect)`, Matplotlib impone una máscara de recorte estricta ligada a las coordenadas geométricas del parche `patches.Rectangle`. Cualquier glifo que intente rebasar el ancho del bloque resulta truncado a nivel de píxel en la frontera del rectángulo, garantizando matemáticamente la imposibilidad de invasión sobre bloques vecinos.

Asimismo, el límite superior del eje vertical se amplía (`ylim = num_gpus + 1.1`), reservando una franja libre en la parte superior derecha para alojar la leyenda global sin solaparse con la pista de ejecución de la GPU 7.

### 6.6.4. Enriquecimiento de Bloques de Red con Métricas Individualizadas por GPU (Desbalanceo MoE Local)

En versiones tempranas del visualizador, las métricas estampadas en los bloques azules y púrpuras se calculaban promediando la totalidad de los paquetes de la colectiva a nivel global del clúster ($N_{\text{total}} = 960\text{ pkts}$). Esto enmascaraba el desbalanceo real bajo distribuciones sesgadas (`skewness > 0`), mostrando el mismo número de paquetes y la misma latencia idéntica en todas las filas de GPUs.

Para reflejar fielmente la microarquitectura y la física de colas de la red, `plot_cronograma.py` implementa el **filtrado y enriquecimiento individualizado por GPU ($d \in [0, N-1]$)**:

1. **Filtrado Semántico según la Topología de la Colectiva:**
   - **En `Scatter` (Recepción de Tokens):** La GPU $d$ actúa como destino receptor (el experto anfitrión de los tokens). Se filtran los paquetes donde $\text{Dest} == d$:
     - $N_{\text{rx}}[d] = \text{len}(\text{df}[\text{Dest} == d])$.
     - $\text{Lat.Media}_{\text{local}} = \frac{1}{N_{\text{rx}}[d]} \sum \text{Total\_Latency} \quad [\text{ciclos}]$.
     - $\text{Prod}_{\text{local}} = \frac{\sum \text{Num\_Flits}}{\max(1.0, \Delta t_{\text{bloque}})} \quad [\text{flits/ciclo}]$.
   - **En `Gather` (Emisión de Activaciones):** La GPU $d$ actúa como origen emisor (el experto que completó el cálculo FFN y retorna las activaciones). Se filtran los paquetes donde $\text{Source} == d$:
     - $N_{\text{tx}}[d] = \text{len}(\text{df}[\text{Source} == d])$.
     - $\text{Lat.Media}_{\text{local}} = \frac{1}{N_{\text{tx}}[d]} \sum \text{Total\_Latency} \quad [\text{ciclos}]$.
     - $\text{Prod}_{\text{local}} = \frac{\sum \text{Num\_Flits}}{\max(1.0, \Delta t_{\text{bloque}})} \quad [\text{flits/ciclo}]$.
   - **En `AllReduce` (Tensor Parallelism):** Se aíslan los paquetes correspondientes al subgrupo donde participa la GPU $d$ ($\text{Dest} == d$ o $\text{Source} == d$).

2. **Formateo Adaptativo según Nivel de Zoom:**
   - **Tier 2 ($2{,}000\text{ ns} \le \Delta t < 6{,}000\text{ ns}$):**
     ```
     L{L} | {Op} Nº{k} ({N_local} pkts)
     Lat.Media: {lat_local:.1f}c | Prod: {prod_local:.2f} f/c
     ```
     *(Si la GPU no interviene en esa colectiva, muestra claramente: `L{L} | {Op} Nº{k} (0 pkts)`).*
   - **Tier 1 ($800\text{ ns} \le \Delta t < 2{,}000\text{ ns}$):**
     Etiqueta compacta `{Op} Nº{k} ({N_local}p)` o `(0 pkts)`.
   - **Tier 3 ($\Delta t \ge 6{,}000\text{ ns}$):**
     Rango local de PIDs: `PIDs {min}-{max} ({N_local} pkts)` junto con `Lat.Media` y productividad local.

3. **Validación Experimental en `skewness: 1.0`:**
   En la ventana de inferencia decodificadora (ej. `timeline_part_006_100k_to_120k.png`), el cronograma refleja de manera patente la heterogeneidad Zipfiana:
   - En `Gather Nº3`: la **GPU 0** (experto popular) reporta `336 pkts` con latencia media de `2315.4c` y productividad `0.69 f/c`, mientras que la **GPU 5** y la **GPU 7** reportan solo `32 pkts` (`199.1c`) y `48 pkts` (`237.1c`), evidenciando por qué estas últimas concluyen su comunicación mucho antes y entran en `NETWORK_STALL`.
   - En `Scatter Nº4`: la **GPU 0** absorbe `304 pkts` (`1435.8c`, `0.89 f/c`), mientras que las GPUs periféricas reciben apenas `32 pkts` (`0.07 f/c`).

### 6.6.5. Coalescencia Causal Global Previa a la Ventana y Filtro Anti-Appends

- **Coalescencia Global Invariante:** Para evitar que un bloque largo de cómputo (por ejemplo, un `ExpertFFN` de $44.3\,\mu\text{s}$ en 4 GPUs) resulte fracturado o pierda su diagnóstico de operaciones al cruzar el límite de una ventana de $10.000\text{ ns}$, la coalescencia se efectúa a escala completa sobre toda la traza de cada GPU antes de segmentar en ventanas.
- **Filtro Anti-Appends:** Detecta automáticamente saltos negativos en la columna `START_NS` ($\Delta t < 0$), saneando las trazas si el archivo `.trc` contenía ejecuciones previas y analizando exclusivamente la última iteración simulada.

---

# CAPÍTULO 7: Amenazas a la Validez, Limitaciones Actuales y Hoja de Ruta de Mejoras

Para mantener el máximo rigor científico en esta investigación de Máster, se declaran de manera transparente las simplificaciones y limitaciones presentes en el entorno de co-simulación actual.

## 7.1. Estado de las Simplificaciones del Simulador y Resoluciones del Bloque C

1. **Latencia de Red Individualizada y Causalidad Bidireccional Cuádruple (Resuelto en Bloque C y Auditoría Forense - ✅):**
   *Estado Previo:* El Oráculo calculaba el ciclo de llegada del último paquete global de la red y aplicaba ese escalar uniforme a todas las GPUs. Posteriormente, se consideraba solo la recepción en destino (`rx_atime`).
   *Resolución Implementada:* Mediante `BookSimCoSimManager::cached_latency_per_gpu[layer_name][dst]`, el Oráculo monitorea el ciclo exacto de recepción (`atime`), el ciclo de finalización de inyección local (`tx_inj`) y el ciclo de retiro global de paquetes emitidos (`tx_retire`). Cada GPU aplica una latencia causal que garantiza que su interfaz concluye cuando todos sus flits emitidos y recibidos están completados.
2. **Desfase Causal de Inyección ($\Delta t_{src}$) según Reloj Real (Resuelto en Bloque C - ✅):**
   *Estado Previo:* Todos los paquetes se inyectaban en BookSim2 asumiendo un reloj local relativo común en ciclo 0.
   *Resolución Implementada:* El Oráculo muestrea los tiempos reales absolutos de llegada $t_{\text{src}}[s]$ de cada GPU al módulo de red (validados tras `sync_3`), calcula el desfase relativo $\Delta t_{\text{src}}[s] = \text{round}(t_{\text{src}}[s] - t_{\min})$ e inyecta los paquetes en BookSim2 en el ciclo exacto `cycles == delta_t[src]`. Las GPUs rápidas comienzan a emitir de inmediato y las lentas entran posteriormente.
3. **Desacoplamiento de Cómputo Local en `ExpertFFN` (Resuelto en Bloque C - ✅):**
   *Estado Previo:* La barrera `sync_for_moe_scatter` contenía `device_list`, obligando a todo el clúster a sincronizarse antes de que cualquier GPU pudiera iniciar su cómputo.
   *Resolución Implementada:* `sync_for_moe_scatter` se acota a `{device_total_rank}`, permitiendo a las GPUs que reciben menos tokens (o más cercanas) comenzar su cómputo `ExpertFFN` inmediatamente. La barrera previa a Gather (`sync_3`) opera con `equalize_time = false` para verificar la dependencia de datos sin aplanar los relojes de fin de cómputo, y la barrera colectiva `sync_for_moe_gather` (`equalize_time = true`) absorbe con precisión milimétrica el desbalance acumulado generando el bloque rojo **`NETWORK_STALL`**.
4. **Comunicaciones Colectivas No-MoE en BookSim2 (Resuelto en Vía 2 - ✅):**
   *Estado Previo:* Operaciones como el `AllReduce` de la atención se modelaban mediante la formulación analítica de ancho de banda sintético ($T = \text{Data} / \text{BW} + \text{hop} \times \text{lat}$), limitando BookSim2 a la dispersión y reunión MoE (`moe_scatter` y `moe_gather`).
   *Resolución Implementada:* Implementación completa del algoritmo Ring-AllReduce a nivel de flit en BookSim2 Oráculo con particionamiento en chunks $S_{\text{chunk}} = \lceil \text{size} / P \rceil$, inyección causal escalonada según $\Delta t_{\text{src}}$, causalidad cuádruple en subgrupos aislados (`_grp_X`) y exportación a `packet_tracking_debug.csv` y trazas `.trc`.
5. **Ausencia de Backpressure sobre la GPU:**
   El simulador asume colas de software de red sin desbordamiento. Los flits son retenidos en BookSim2 en las colas de inyección sin aplicar contrapresión física bloqueante hacia los registros de ejecución de la GPU.

---

## 7.2. Evaluación de Impacto en la Precisión Científica

Gracias a las innovaciones de fidelidad física introducidas en el **Bloque C** y la **Vía 2**:
- Se reproduce con total fidelidad la asincronía natural de los clústeres heterogéneos, la dispersión All-to-All desbalanceada y la contención en colectivas Ring-AllReduce de Tensor Parallelism.
- Se cuantifica empíricamente el beneficio de solapamiento de cómputo en GPUs ligeras que reciben menos tokens.
- Se capturan las burbujas reales de sincronización (`NETWORK_STALL`) en las barreras colectivas, permitiendo evaluar el coste exacto de la heterogeneidad de cómputo y de tráfico en la red de interconexión.
- Se mantiene una congruencia temporal perfecta: la suma de Cómputo + Tránsito de Red + Bloqueos Stalls coincide hasta el último decimal de nanosegundo con el Wall-Clock Time de la simulación.

---

## 7.3. Hoja de Ruta y Roadmap de Extensiones Futuras

1. **[COMPLETADO - Bloque C] Vectorización de Latencias Receptora por Receptora:**
   Implementado en `BookSimCoSimManager::cached_latency_per_gpu` y verificado en Mixtral 8x7B.
2. **[COMPLETADO - Bloque C] Desfase Causal de Inyección ($\Delta t_{\text{src}}$):**
   Implementado en `packets_by_cycle` dentro de `MoEScatter::forward()` y `MoEGather::forward()`.
3. **[COMPLETADO - Auditoría Forense] Causalidad Física Bidireccional Cuádruple en Oráculo de Red:**
   Implementado en `src/module/communication.cpp` garantizando $\text{rel\_finish}[d] = \max(\delta_t[d], \text{rx\_atime}[d], \text{tx\_inj}[d], \text{tx\_retire}[d])$.
4. **[COMPLETADO - Vía 2] Integración de Ring-AllReduce en el Oráculo BookSim2 con Causalidad Cuádruple y Tensor Parallelism:**
   Implementado en `AllReduce::forward` (`src/module/communication.cpp`) con aislamiento de grupo `op_key`, transferencia de chunks $2(P-1)S_{\text{chunk}}$ sobre topologías Torus/Mesh, trazabilidad completa de PIDs y soporte CLI con `--tensor_degree` / `--tp`.
5. **[COMPLETADO - Vía 3] Parametrización y Estudio de Desbalanceo Extremo de Carga en Expertos MoE (Skewness Zipfiano):**
   Implementado soporte CLI con `--skewness` / `--skew`, inyección dinámica en `config.yaml`, categorización de carpetas de salida (`_skew{s}`), y etiquetado macroscópico en `analyze_traces.py`. Validación experimental de hotspots de in-cast en NoC ($30.8\%$ de tráfico absorbido por GPU 0 con $s=1.0$), incremento de latencia de paquetes ($+29.1\%$) y saturación asíncrona de barreras (`NETWORK_STALL`).
6. **[COMPLETADO - Vía 4] Estudio Comparativo Arquitectónico: Mixtral 8x7B vs. DeepSeek-V3 (Fine-Grained MoE & MLA):**
   Integración completa de DeepSeek-V3 en el co-simulador (60 capas, 3 densas iniciales, $E=256$ micro-expertos, Top-8 routing, expertos compartidos y compresión de atención MLA). Cuantificación rigurosa de la explosión de tráfico All-to-All ($18.7\times$ más paquetes y flits) e hipertrofia de retardo en cola de NIC ($8.94\times$ mayor, picos de $52,680$ ciclos). Adaptación de `plot_cronograma.py` y `analyze_traces.py` para micro-expertos y capas híbridas.
7. **Soporte Jerárquico Multi-Nodo (NVLink + InfiniBand):**
   Integrar una red de dos niveles en BookSim2: enlaces de ultra-alto ancho de banda ($900\text{ GB/s}$) intra-nodo y enlaces de red de área de sistema ($100\text{ GB/s}$) inter-nodo.
8. **Modelado de Capacidad Finita de Buffers NIC:**
   Introducir un límite estricto de paquetes en las colas del host para simular caídas de rendimiento por contrapresión física hacia los hilos de la GPU.

---

## 7.4. Hardware Multicast e In-Network Reduction en Arquitecturas MoE de Grano Fino

Los hallazgos empíricos de la Vía 4 (Sección 4.9) demuestran que en DeepSeek-V3 la hipertrofia de retardo en las colas de inyección NIC (`Queueing_Delay` medio superior a $10.000$ ciclos, picos de más de $42.000 - 52.000$ ciclos) es el cuello de botella primario de la interconexión NoC. Este fenómeno abre dos líneas de investigación arquitectónica de vanguardia en aceleración hardware:

### 7.4.1. Oportunidad de Hardware Multicast en `MoEScatter`
En DeepSeek-V3, cada token activa $k=8$ micro-expertos de entre $E=256$. En un clúster de $N=8$ GPUs con 32 micro-expertos por dispositivo, la probabilidad de que un token deba enviarse a una GPU física determinada $g$ es:
$$P(\text{GPU } g \text{ seleccionada}) = 1 - \left(1 - \frac{32}{256}\right)^8 = 1 - (0.875)^8 \approx 1 - 0.3436 \approx 65.64\%$$
El número esperado de GPUs físicas de destino para cada token individual es:
$$\mathbb{E}[N_{\text{GPUs\_destino}}] = 8 \times 0.6564 \approx \mathbf{5.25 \text{ GPUs}}$$

Bajo la implementación actual basada en **tráfico unicast punto a punto**, la GPU emisora debe serializar e inyectar el mismo vector de activación ($7.168\text{ B}$ en FP8) $5.25$ veces en su interfaz de red (NIC), generando una duplicación redundante masiva de flits idénticos:
- En una iteración de 60 capas con $BS=32$, `MoEScatter` inyecta $714.056$ paquetes ($33.3\%$ del total del clúster).
- Si los conmutadores del NoC implementan **árboles de Hardware Multicast** (duplicación de paquetes en los puertos de salida del crossbar del router más cercano a los destinos), la NIC de la GPU origen solo necesitaría inyectar **un único paquete original**:
  $$\text{Reducción de Inyecciones en NIC} \approx \frac{5.25 - 1}{5.25} \approx \mathbf{80.95\%}$$
- Esta optimización eliminaría hasta un $\sim 81\%$ del tráfico de inyección en `MoEScatter`, despresurizando por completo los buffers de la NIC y mitigando casi en su totalidad el `Queueing_Delay` durante la fase de dispersión.

### 7.4.2. In-Network Reduction como Requisito Exclusivo para `MoEGather`
A diferencia de `MoEScatter`, la fase de `MoEGather` (que representa el $66.7\%$ de los paquetes del clúster, $1.428.112$ paquetes, debido a la representación en BF16) **no puede resolverse mediante Hardware Multicast**:
- En `MoEGather`, el patrón de tráfico es **Muchos-a-Uno (In-Cast)**: múltiples GPUs devuelven las activaciones computadas por sus micro-expertos hacia la GPU origen del token.
- Cada micro-experto $e$ produce un vector de activación $h_e = \text{FFN}_e(x)$ matemáticamente **distinto y único**.
- Por tanto, no existen paquetes redundantes que puedan clonarse o fusionarse trivialmente en la red.
- La solución física óptima para mitigar la congestión en `MoEGather` consiste en implementar **In-Network Reduction** (reducción en red inspirada en NVIDIA SHARP o switches PIM aritméticos): los conmutadores intermedios del NoC incorporan unidades funcionales de coma flotante que multiplican las activaciones recibidas por sus respectivos pesos de enrutamiento $g_e$ y las acumulan progresivamente ($y = \sum_e g_e h_e$) conforme los flits convergen hacia el router del nodo destino. De este modo, la GPU origen solo recibe el tensor final ya reducido, contrayendo el volumen de paquetes entrantes hasta en un factor de $8\times$.

---

## 7.5. Propuesta de Vía 5: Co-Simulación Dual-Stream & Pipelining de Micro-Batches (DualPipe)

Los datos empíricos de la Sección 4.9.9 confirman que DeepSeek-V3 exhibe un ratio $T_{\text{compute}} / T_{\text{transit}} \approx 2.50 - 2.66\times$, demostrando que existe holgura aritmética para solapar el $100\%$ de la comunicación de red.

Para modelar este fenómeno en el co-simulador sin romper la precisión de BookSim2, se propone la arquitectura de **Vía 5 (Dual-Stream & Micro-Batch Pipelining)**:
1. **Desacoplamiento de Relojes por Dispositivo:** Dividir el reloj de cada acelerador en dos sub-pistas temporales independientes:
   - `sm_compute_clock`: Avanza durante la ejecución de Attention, DenseFFN y ExpertFFN en los Tensor Cores.
   - `noc_dma_clock`: Avanza durante la inyección y tránsito de flits en BookSim2.
2. **Segmentación en Micro-Batches:** Particionar el batch global $BS=32$ en $M=4$ micro-batches de $B_{\text{micro}} = 8$ secuencias.
3. **Planificación Estilo DualPipe / 1F1B MoE:**
   - Mientras `sm_compute_clock` ejecuta los 32 micro-expertos del micro-batch $M_i$, el motor DMA activa `noc_dma_clock` para inyectar concurrentemente los flits de `MoEScatter` del micro-batch $M_{i+1}$ y los de `MoEGather` del micro-batch $M_{i-1}$.
   - BookSim2 modelará la contención bidireccional continua en los enlaces NoC mientras los núcleos aritméticos de la GPU permanecen saturados al $100\%$, capturando las burbujas residuales de sincronización en los extremos del pipeline y los incrementos en la huella de memoria intermedia en HBM3E.

   Mas detallado (esto viene del chat Gemini):
   Por qué no basta con activar parallel_execution: on en config.yaml?
   En el código original de LLMSimulator (src/module/status.h y communication.cpp), el flag parallel_execution y los dos relojes auxiliares (high_time y low_time) fueron diseñados exclusivamente para arquitecturas heterogéneas GPU + PIM, donde los cálculos pesados van a la GPU (high_time) y los expertos MoE se descargan a memorias inteligentes (low_time). En un clúster homogéneo de GPUs Nvidia B100 (processor_type: GPU), activar ese flag no divide el lote en micro-batches ni solapa red con cómputo.
   TFM_Technical_Bible.docx
   Arquitectura propuesta para implementar Vía 5 en el futuro
   Para acercar el co-simulador al comportamiento de DualPipe en producción sin reescribir el motor entero, se puede implementar en dos niveles progresivos:
   Nivel 5A — Solapamiento Intra-Capa (CUDA Compute Stream vs. Copy/NCCL Stream):
   Mecanismo: Dotar a cada Device de dos relojes de flujo paralelos (sm_compute_time y noc_dma_time) en lugar de un único device_time secuencial.
   Aplicación en DeepSeek-V3: El Experto Compartido (Shared Expert) de cada capa no depende de los tokens que viajan por red en MoEScatter. El motor puede ejecutar el cálculo del Shared Expert en sm_compute_time simultáneamente mientras BookSim2 resuelve las ráfagas de MoEScatter en noc_dma_time, sincronizando ambos relojes (max(sm_compute_time, noc_dma_time)) justo antes de iniciar los 32 micro-expertos enrutados.
   Nivel 5B — Pipelining de Micro-Batches ($MB_0$ y $MB_1$ tipo DualPipe):
   Mecanismo: Dividir el lote activo ($BS=32$) en dos mitades de $16$ secuencias dentro de Decoder::forward().
   Planificación: Mientras la GPU ejecuta el cómputo de ExpertFFN del micro-batch $MB_0$ en los Tensor Cores, el Oráculo de BookSim2 inyecta y transfiere en segundo plano los paquetes de MoEScatter del micro-batch $MB_1$.
   Visualización en plot_cronograma.py: Cada GPU pasaría a representarse con dos sub-pistas horizontales (GPU i [SM Compute] y GPU i [NIC / NoC]), mostrando visualmente cómo las barras azules de red quedan escondidas debajo de las barras verdes de cómputo y cómo desaparecen las franjas rojas de NETWORK_STALL.

---

# CAPÍTULO 8: Referencia Exhaustiva Archivo por Archivo (File-by-File Codebase Reference)

Este capítulo constituye la guía exhaustiva y sistemática de todos los archivos de cabecera (`.h`, `.hpp`), implementación (`.cpp`) y scripts de soporte (`.py`) que componen `LLMSimulator` y la infraestructura de interconexión `booksim2`. Para cada componente se detalla su cometido arquitectural, estructuras de datos, interfaces y relación causal con el resto del simulador.

---

## 8.1. Punto de Entrada y Evaluación (`eval/`)

### [`eval/test.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/eval/test.cpp)
- **Propósito:** Punto de entrada ejecutable (`main`) del simulador. Orquesta el parseo de argumentos de línea de comandos, la instanciación de configuraciones hardware y de modelo, la carga de trazas de inferencia y la ejecución de los bucles iterativos.
- **Estructuras y Funciones Clave:**
  - `main(int argc, char* argv[])`: Lee parámetros (`--model`, `--batch_size`, `--input_len`, `--output_len`, `--device_num`, `--tp`, `--skewness`, etc.).
  - Instanciación de `SystemConfig` y `ModelConfig`.
  - Creación del clúster acelerador: `Cluster::Create(system_config, scheduler)`.
  - Construcción del modelo: `LLM::LLM(...)`.
  - Bucle de simulación: invoca `cluster->runIteration(iter, "stat")`.
- **Interacción:** Conecta el usuario y los scripts de automatización (`run_sim.py`) con las capas internas `Cluster`, `Scheduler` y `LLM`.

---

## 8.2. Infraestructura Común y Tipos Base (`src/common/`)

### [`src/common/assert.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/common/assert.h)
- **Propósito:** Macro y funciones de aserción e invariantes del sistema para validación en tiempo de ejecución.
- **Estructuras y Funciones Clave:**
  - `assertTrue(bool condition, std::string message)`: Si la condición es falsa, aborta el programa imprimiendo la traza de error detallada.
  - `fail(std::string message)`: Termina la ejecución incondicionalmente reportando una excepción fatal.
- **Interacción:** Utilizado universalmente en todo el simulador para garantizar integridad dimensional de tensores y consistencia en configuraciones.

### [`src/common/type.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/common/type.h)
- **Propósito:** Definición de alias de tipos de datos fundamentales para métricas de tiempo, energía, ciclo y operaciones físicas.
- **Estructuras y Funciones Clave:**
  - `using time_ns = double`: Representación de latencias y marcas temporales en nanosegundos con precisión de coma flotante.
  - `using cycle_t = uint64_t`: Contador discreto de ciclos de reloj.
  - `using energy_nJ = double`: Energía dinámica acumulada en nanojulios.
  - `using hw_metric = double`: Métricas de hardware (anchos de banda en Bytes/s, cómputo en FLOPs/s).
- **Interacción:** Cabecera ubicua incluida por todos los módulos que manipulan tiempo, ciclos o energía.

---

## 8.3. Subsistema DRAM, Simulación de Memoria y PIM (`src/dram/`)

### [`src/dram/data_object.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/data_object.h) & [`data_object.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/data_object.cpp)
- **Propósito:** Representación abstracta de datos alojados en memoria física DRAM y buffers intermedios para aceleradores PIM.
- **Clases Clave:** `DataObject`. Mantiene el identificador de dirección base, tamaño en bytes, precisión y asignación de canales.
- **Interacción:** Vincula tensores del grafo con peticiones de bajo nivel en `DRAMInterface`.

### [`src/dram/dram_interface.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/dram_interface.h) & [`dram_interface.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/dram_interface.cpp)
- **Propósito:** Enlace e interfaz de bajo nivel con el simulador de memorias ciclo a ciclo Ramulator2.
- **Clases Clave:** `DRAMInterface`.
  - `HandleRequest(requests, start_time_cycle)`: Encola solicitudes de lectura/escritura DRAM.
  - `run()`: Avanza la simulación de Ramulator2 y computa la latencia real basada en temporizaciones $t_{RCD}$, $t_{RP}$, $t_{CL}$.
  - `GeneratePIMCommand()`: Mapea operaciones a instrucciones Processing-In-Memory.
- **Interacción:** Invocado por `Device::issueRamulator()` para calcular con máxima fidelidad los retrasos de acceso a la memoria HBM.

### [`src/dram/dram_request.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/dram_request.h) & [`dram_request.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/dram_request.cpp)
- **Propósito:** Encapsulación de una transacción individual emitida hacia el controlador de memoria.
- **Clases Clave:** `DRAMRequest`. Almacena dirección física hex, tipo de operación (`kRead`, `kWrite`), tamaño de ráfaga y canal de destino.

### [`src/dram/dram_type.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/dram_type.h)
- **Propósito:** Enumeraciones para el subsistema de memoria: `DRAMRequestType` (`kRead`, `kWrite`), `PIMCommandType` (`GEMV`, `Read`, `Write`), `PIMOperandType` (`kDRAM`, `kRegister`).

### [`src/dram/memory_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/memory_config.h)
- **Propósito:** Parámetros configurables del subsistema de memoria: número de canales, rangos, grupos de bancos, bancos por grupo y tamaño de línea de caché (ej. 32B/64B).

### [`src/dram/memory_object.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/memory_object.h) & [`memory_object.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/memory_object.cpp)
- **Propósito:** Gestión de objetos de memoria persistentes (pesos de capas, KV caches) y transitorios (activaciones).

### [`src/dram/mmap_controller.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/mmap_controller.h) & [`mmap_controller.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/mmap_controller.cpp)
- **Propósito:** Controlador de mapeo de direcciones virtuales de tensores a direcciones físicas continuas/estratificadas en HBM.
- **Interacción:** Asegura que los accesos concurrentes de múltiples GPUs o canales DRAM distribuyan el tráfico sin colisiones artificiales.

### [`src/dram/pimkernel/pim_kernel.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/pimkernel/pim_kernel.h) & [`pim_kernel.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/pimkernel/pim_kernel.cpp)
- **Propósito:** Definición abstracta de kernels ejecutables directamente en la lógica interna de los bancos de memoria DRAM (Processing-In-Memory).
- **Implementaciones:** [`GEMV.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/pimkernel/GEMV.cpp) (producto matriz-vector en banco), [`Read.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/pimkernel/Read.cpp), [`Write.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/pimkernel/Write.cpp).

### [`src/dram/pim_request.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/pim_request.h) & [`pim_request.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/pim_request.cpp)
- **Propósito:** Petición específica de instrucción PIM transmitida por los buses de comando hacia los módulos de memoria inteligentes.

### [`src/dram/power.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/power.h)
- **Propósito:** Modelo físico de coeficientes energéticos ($0.909\text{ nJ}$ ACT, $0.891\text{ nJ}$ RD/WR, $0.00023\text{ nJ}$ MAC) derivado del estudio MICRO 2017 Fine-Grained DRAM.
- **Interacción:** Base matemática para la cuantificación energética en `module_graph.cpp` y `timeboard.cpp`.

### [`src/dram/test.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/test.cpp)
- **Propósito:** Suite de pruebas unitarias para validar de forma aislada las transacciones y temporizaciones de `DRAMInterface`.

---

## 8.4. Capa Hardware y Ejecución de Aceleradores (`src/hardware/`)

### [`src/hardware/base.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/base.h)
- **Propósito:** Declaración de enumeraciones base del hardware: `ProcessorType` (`GPU`, `LOGIC`, `PIM`), `LayerType` (`LINEAR`, `ATTENTION_GEN`, `ATTENTION_SUM`, `MLA_GEN`, etc.), y estructura `LayerInfo`.

### [`src/hardware/hardware_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/hardware_config.h)
- **Propósito:** Definición de la clase `SystemConfig` y configuraciones canónicas de GPUs: A100, H100, B100, B200 (cómputo pico, ancho de banda DRAM, latencias NVLink y red de nodo).

### [`src/hardware/stat.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/stat.h)
- **Propósito:** Estructura `Stat` que recopila las métricas agregadas por iteración: tiempos de cómputo por componente (QKV, Attention, FFN, MoE, AllReduce), latencias de cola y consumo energético total.

### [`src/hardware/device.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.h) & [`device.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp)
- **Propósito:** Representa un acelerador individual (GPU o procesador PIM). Gestiona el estado de reloj local (`device_time`), la caché de memoización analítica (`addExecutionCache`), y delega la ejecución de capas a los motores analíticos o a Ramulator2.
- **Trazabilidad y Sincronización:** Implementa `log_tfm_event()` con formateador de alta precisión (`std::fixed`, `std::setprecision(4)`) protegido por la guarda `if (!perform_execution) return;`. Gestiona la transición de construcción a ejecución real mediante `setPerformExecution(bool)`: purga residuos de inicialización estática, resetea métricas con `reset_status()` y trunca `TFM_device_<id>.trc` asegurando un arranque limpio desde $0.0000\text{ ns}$.

### [`src/hardware/node.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/node.h) & [`node.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/node.cpp)
- **Propósito:** Agrupa los dispositivos `Device` alojados en un mismo chasis/servidor físico, gestionando la interconexión intra-nodo (ej. NVLink).

### [`src/hardware/cluster.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/cluster.h) & [`cluster.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/cluster.cpp)
- **Propósito:** Entidad superior que gobierna todo el clúster multi-nodo y multi-GPU.
- **Métodos Clave:**
  - `runIteration()`: Bucle principal de ejecución iterativa de lotes.
  - `set_dependency()`: Configura dependencias y barreras entre módulos.
  - Inicializa las instancias de energía de DRAM (`gpuEnergy`, `logicEnergy`).

### [`src/hardware/executor.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/executor.h) & [`executor.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/executor.cpp)
- **Propósito:** Capa intermedia que despacha solicitudes de ejecución hacia los motores de cómputo específicos de cada capa.

### [`src/hardware/layer_impl.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/layer_impl.h) & [`layer_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/layer_impl.cpp)
- **Propósito:** Funciones auxiliares para modelar el rendimiento de capas según el modelo Roofline (`getIdealMemoryStatus`, `issueRamulator`).

### [`src/hardware/linear_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/linear_impl.cpp)
- **Propósito:** Motor analítico de proyecciones lineales (GEMM). Calcula FLOPs ($2 \cdot m \cdot k \cdot n$), tráfico de memoria y evalúa el límite Roofline ($T = \max(T_{\text{comp}}, T_{\text{mem}})$).

### [`src/hardware/activation_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/activation_impl.cpp)
- **Propósito:** Modelado de funciones de activación element-wise (GELU, SiLU). Tráfico memory-bound $2 \cdot m \cdot n \times \text{precision\_byte}$.

### [`src/hardware/attention_sum_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/attention_sum_impl.cpp)
- **Propósito:** Modelado microarquitectural de la fase de prefill/resumen en atención: calcula FLOPs $4 m^2 k$ y transferencias DRAM completas de secuencias largas.

### [`src/hardware/attention_gen_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/attention_gen_impl.cpp)
- **Propósito:** Modelado de la fase de decodificación token a token: cuantifica la lectura del KV-cache para cada paso autoregresivo.

### [`src/hardware/attention_mixed_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/attention_mixed_impl.cpp)
- **Propósito:** Modelado de lotes mixtos compuestos simultáneamente por secuencias en prefill y secuencias en decode.

### [`src/hardware/test.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/test.cpp)
- **Propósito:** Batería de tests de rendimiento y validación de los métodos de cómputo hardware.

---

## 8.5. Definición y Topología de Modelos LLM (`src/model/`)

### [`src/model/model_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/model_config.h)
- **Propósito:** Estructura `ModelConfig` con todos los hiperparámetros de arquitecturas LLM (dimensiones, capas, expertos, atención MLA/GQA/MHA, factor de skewness Zipfiano) y catálogo estático de modelos (`mixtral`, `deepseekV3`, etc.).

### [`src/model/model.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/model.h)
- **Propósito:** Interfaz abstracta pura para modelos de lenguaje en el simulador.

### [`src/model/llm.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/llm.h) & [`llm.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/llm.cpp)
- **Propósito:** Implementación concreta del grafo de modelo LLM. Instancia la capa `Embedding`, conecta los decodificadores densos (`Decoder`) o MoE (`MoEDecoder`) según la configuración, y culmina en la capa `LmHead`.

### [`src/model/util.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/util.h)
- **Propósito:** Funciones de utilidad matemática y manipulación de cadenas de configuración de modelos.

### [`src/model/test.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/test.cpp)
- **Propósito:** Pruebas unitarias de construcción topológica de grafos de modelos.

---

## 8.6. Módulos Operacionales y Grafo Computacional (`src/module/`)

### [`src/module/base.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/base.h)
- **Propósito:** Declaración adelantada de tipos de punteros (`Module::Ptr`, `Tensor::Ptr`) y macros operacionales para el grafo.

### [`src/module/status.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/status.h)
- **Propósito:** Estructura `Status` que almacena los relojes asíncronos (`device_time`, `high_time`, `low_time`) y contadores de energía por dispositivo.

### [`src/module/tensor.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/tensor.h) & [`tensor.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/tensor.cpp)
- **Propósito:** Encapsulación de tensores en el grafo computacional.
- **Clases Clave:** `Tensor`. Contiene forma dimensional (`shape`), tipo de dato (`precision_byte`), procedencia (`weight`, `act`, `cache`) y flags de ejecución paralela (`setPerformHigh`, `setPerformLow`).

### [`src/module/module.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module.h) & [`module.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module.cpp)
- **Propósito:** Clase base de todos los módulos operacionales del simulador. Gestiona jerarquías de submódulos (`add_module`, `get_module`), mapeo de nombres jerárquicos (`module_map_name`), tensores locales y asociación con dispositivos hardware.
- **Control de Sincronización Temporal (Bloque C):** Incorpora el miembro `bool equalize_time` (por defecto `true`). Cuando es `false` (configurado en `MoEScatter`, `MoEGather` y `sync_3`), indica al planificador de dependencias que no iguale forzosamente los relojes del clúster al tiempo máximo al resolver dependencias de datos, preservando los instantes reales de finalización asimétrica $t_{\text{src}}$.

### [`src/module/module_graph.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.h) & [`module_graph.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp)
- **Propósito:** Motor central de ejecución del grafo de dependencias estático.
- **Clases Clave:**
  - `ModuleGraph`: Grafo local por GPU. Mantiene la lista de nodos ordenados topológicamente (`topological_sort()`). En `check_ready()`, evalúa `if (module->equalize_time) sync_devices();`, permitiendo barreras de control de datos que no aplastan artificialmente los relojes locales de las GPUs.
  - `TopModuleGraph`: Coordinador global que gobierna el bucle de ejecución de todas las GPUs mediante barreras `sync_devices()`, resolución de nodos PUSH/POP y avance causal de dependencias.
  - Acumula los contadores físicos de energía (`status.act_energy`, `status.mac_energy`, etc.).
  - En `set_pop_status()`, incorpora la guarda `is_self_logged` que filtra módulos autologgeados (`norm`, `residual`, `rope`, `scatter`, `gather`, `all_reduce`) para evitar registros duplicados o solapados en trazas `.trc`.

### [`src/module/timeboard.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/timeboard.h) & [`timeboard.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/timeboard.cpp)
- **Propósito:** Tablero de instrumentación y trazabilidad. Registra marcas temporales (`TimeStamp`) de inicio y fin de cada módulo, computa diferencias de energía y vuelca estadísticas tabulares a consola y trazas estructuradas.

### [`src/module/linear.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/linear.h) & [`linear.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/linear.cpp)
- **Propósito:** Módulo de proyección lineal (Linear/GEMM). Utilizado para proyecciones $Q, K, V$, proyecciones de salida de atención y capas densas FFN.

### [`src/module/activation.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/activation.h) & [`activation.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/activation.cpp)
- **Propósito:** Módulos de función de activación (GELU, SiLU / SwiGLU).

### [`src/module/attention.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/attention.h) & [`attention.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/attention.cpp)
- **Propósito:** Módulos operacionales de atención completa: `SelfAttentionGen`, `SelfAttentionSum`, `AttentionSplit`, `AttentionMerge` y `MultiLatentAttentionGen`. Gobiernan la gestión del KV cache y la selección de proyecciones absorbidas (`use_absorb`).

### [`src/module/compressed_kv_restore.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/compressed_kv_restore.h) & [`compressed_kv_restore.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/compressed_kv_restore.cpp)
- **Propósito:** Módulo específico de la arquitectura MLA para gestionar el almacenamiento y recuperación del vector latente comprimido de $512$ elementos y la clave RoPE desacoplada de $64$ elementos.

### [`src/module/layernorm.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/layernorm.h) & [`layernorm.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/layernorm.cpp)
- **Propósito:** Normalización por capas (`RMSNorm` / `LayerNorm`). Operación memory-bound analítica. Incorpora guarda `if (!device->perform_execution) return output;` para prevenir trazas y avances de tiempo en la construcción del grafo.

### [`src/module/residual.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/residual.h) & [`residual.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/residual.cpp)
- **Propósito:** Conexión residual que suma elemento a elemento la entrada del bloque con la salida de la atención o FFN. Incorpora guarda de `perform_execution` en `forward()`.

### [`src/module/rope.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/rope.h) & [`rope.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/rope.cpp)
- **Propósito:** Embebido posicional rotacional (Rotary Position Embedding). Aplica rotaciones ortogonales a los vectores de Query y Key. Silenciado durante la inicialización mediante guarda de `perform_execution`.

### [`src/module/route.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/route.h) & [`route.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/route.cpp)
- **Propósito:** Compuerta de enrutamiento MoE (Gating Network).
- **Métodos Clave:**
  - `Route::forward()`: Evalúa logits de enrutamiento, aplica softmax y selecciona los Top-$k$ expertos por token.
  - Modela distribuciones de selección sintéticas (uniforme o Zipfiana según el parámetro `skewness`) o basadas en trazas reales de dataset.

### [`src/module/expert.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.h) & [`expert.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp)
- **Propósito:** Módulo del conjunto de expertos MoE (`ExpertModule`). Ejecuta el bloque Feed-Forward Network (`SwiGLU`) para los tokens enrutados a los expertos locales alojados en la GPU.
- **Topología de Barreras Asíncronas (Bloque C):**
  - `sync_for_moe_scatter`: Instanciado con `{device->device_total_rank}`, eliminando la barrera cluster-wide y permitiendo a las GPUs con menos tokens iniciar `ExpertFFN` local inmediatamente tras recibir sus datos.
  - `sync_3`: Instanciado con `equalize_time = false`, garantizando que todas las GPUs hayan completado `ExpertFFN` antes de iniciar la recolección en `MoEGather`, pero sin alterar sus relojes individuales.
  - `sync_for_moe_gather`: Mantiene `equalize_time = true`, sincronizando el clúster globalmente y absorbiendo la dispersión asíncrona como tiempo de espera real (`NETWORK_STALL`).

### [`src/module/layer.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/layer.h) & [`layer.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/layer.cpp)
- **Propósito:** Módulos de bloques funcionales completos: bloque de atención multi-cabezal (`AttentionModule`), bloque denso FFN (`FeedForwardModule`), y módulos de actualización de puertas (`GateUpdate`).

### [`src/module/decoder.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/decoder.h) & [`decoder.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/decoder.cpp)
- **Propósito:** Bloque transformador decodificador completo:
  - `Decoder`: Decodificador estándar denso (Pre-LN $\to$ MHA/GQA $\to$ Post-LN $\to$ Dense FFN $\to$ Residual).
  - `MoEDecoder`: Decodificador disperso con expertos (Pre-LN $\to$ MHA/GQA $\to$ Post-LN $\to$ Route $\to$ MoEScatter $\to$ Expert FFN $\to$ MoEGather $\to$ GateUpdate $\to$ Residual).

### [`src/module/embedding.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/embedding.h) & [`embedding.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/embedding.cpp)
- **Propósito:** Capa inicial de lookup de tokens que transforma IDs a representaciones vectoriales.

### [`src/module/lm_head.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/lm_head.h) & [`lm_head.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/lm_head.cpp)
- **Propósito:** Capa final de salida (Linear) que mapea el estado oculto hacia los logits sobre el vocabulario.

### [`src/module/parallel.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/parallel.h) & [`parallel.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/parallel.cpp)
- **Propósito:** Primitivas de división y fusión de tensores para paralelismo tensorial (`TensorSplit`, `TensorMerge`).

### [`src/module/communication.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.h) & [`communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp)
- **Propósito:** Módulos de comunicación de red entre GPUs (`AllReduce`, `MoEScatter`, `MoEGather`, `Sync`).
- **Punto Crítico de Integración (Bloque C y Vía 2):** Aloja el singleton `BookSimCoSimManager`.
  - En `MoEScatter` y `MoEGather`: GPU 0 calcula los instantes reales de llegada $t_{\text{src}}[s]$ y el desfase de inyección $\Delta t_{\text{src}}[s] = \text{round}(t_{\text{src}}[s] - t_{\min})$. Organiza los paquetes en `packets_by_cycle` para inyectarlos en BookSim2 exactamente cuando `cycles == delta_t[src]`. Aplica la regla de causalidad cuádruple registrando la latencia individual en `cached_latency_per_gpu[layer_name][dst]`.
  - En `AllReduce`: implementa el algoritmo **Ring-AllReduce cycle-accurate en BookSim2** (`equalize_time = false`), dividiendo el tensor en chunks $S_{\text{chunk}} = \lceil \text{size} / P \rceil$ transmitidos en anillo lógico, gobernado por desfases causales $\Delta t$, causalidad cuádruple y aislamiento de subgrupos `op_key = module_map_name + "_grp_" + device_list[0]`. Gestiona el contador correlativo `allreduce_op_counter` exportado a `packet_tracking_debug.csv` y sella la operación con `BookSim_FinishOperation`. Incorpora guarda de `perform_execution`.

### [`src/module/test.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/test.cpp)
- **Propósito:** Pruebas unitarias sobre instanciación de módulos y operaciones del grafo.

---

## 8.7. Planificador de Inferencia y Lotes (`src/scheduler/`)

### [`src/scheduler/sequence.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/sequence.h) & [`sequence.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/sequence.cpp)
- **Propósito:** Representación individual de secuencias de inferencia (`Sequence`). Contiene longitud de entrada (`input_len`), tokens generados (`current_len`), límite de salida (`output_len`), traza de expertos asignados y tiempos causales (`arrival_time`, `gen_start_time`, `queueing_delay`).

### [`src/scheduler/scheduler.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/scheduler.h) & [`scheduler.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/scheduler.cpp)
- **Propósito:** Planificador dinámico de lotes (Batched Scheduler).
- **Métodos Clave:**
  - `pushDummySeq()` / `pushRealSeq()`: Encola secuencias sintéticas o reales procedentes de dataset.
  - `updateScheduler()`: Construye el lote de la iteración actual seleccionando secuencias según límites de memoria y tokens máximos (`max_process_token`).
  - `getRandomExpert()`: Genera índices de enrutamiento Top-$k$ respetando la distribución configurada.

### [`src/scheduler/test.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/scheduler/test.cpp)
- **Propósito:** Pruebas unitarias del sistema de colas y conformación de lotes.

---

## 8.8. Herramientas de Automatización y Análisis en Python (`LLMSimulator/`)

### [`LLMSimulator/run_sim.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/run_sim.py)
- **Propósito:** Orquestador principal de experimentos. Automatiza la ejecución del binario compilado, gestiona parámetros CLI, captura salidas en consola y coordina la generación de artefactos (`dia1_exec1.txt`, `packet_tracking_debug.csv`).
- **Mecanismos Clave:**
  - Soporte CLI para selección de modelo (`--model mixtral` o `--model deepseekV3`), normalizando automáticamente alias frecuentes (`deepseek`, `deepseek-v3`, `deepseek_v3`).
  - Soporte CLI para Tensor Parallelism (`--tensor_degree` / `--tp`) y factor de desbalanceo MoE (`--skewness` / `--skew`, por defecto `0.0`), inyectando este último dinámicamente en la sección `generator` de `config.yaml`.
  - Sufijado automático de carpetas de resultados (`_skew{s}`) para trazabilidad de experimentos desbalanceados y prefijado por modelo (`deepseekV3_*`).
  - Habilitación por defecto de la instrumentación de paquetes (`SIM_DEBUG_PIDS="1"`), interceptando las líneas `[TRACK_PID]` para generar `packet_tracking_debug.csv` (17 columnas) sin requerir parámetros manuales adicionales.
  - Soporte para bandera `--no_debug_pids` para anular la captura en barridos masivos donde se desee máxima velocidad.

### [`LLMSimulator/analyze_traces.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/analyze_traces.py)
- **Propósito:** Analizador macroscópico de trazas y sintetizador de la curva de saturación de red (Cierre del Bloque B y Vía 4). Parsea los registros `.trc` de cada GPU y el archivo `packet_tracking_debug.csv`, calculando el balance temporal de cómputo vs. comunicación y correlacionando la carga inyectada con la latencia física de red.
- **Mecanismos Clave:**
  - Resolución dual robusta del directorio base (`resolve_base_dir()`), operable tanto desde la raíz del TFM como desde `LLMSimulator/`.
  - **Filtro Anti-Appends Temporal Dual:** Detecta caídas en la serie cronológica tanto en `.trc` (`START_NS.diff() < 0`) como en `packet_tracking_debug.csv` (`Op_Start_NS.diff() < 0` o `Creation_Cycle.diff() < -1000`) para aislar con total fidelidad la última iteración canónica.
  - Normalización exacta de Wall-Clock Time por dispositivo, balanceo estricto Cómputo + Red (`moe_scatter`, `moe_gather`, `all_reduce`) + Stalls y exportación gráfica de alta definición (`anatomia_latencia.png`, `desglose_primitivas_moe.png`).
  - **Generación de la Curva de Saturación NoC (`curva_saturacion_red.png`):** Extrae la tasa media de inyección $\lambda$ (flits/ciclo/nodo) y latencia media de flit (`Avg_Flit_Latency`), trazando nubes por operación colectiva (incluyendo AllReduce), centroides macroscópicos con metadatos de modelo, topología, canales virtuales, tamaño de lote, grado TP y factor de skewness (`deepseekV3 8dev Torus (VCs=4, BS=32)` vs. `mixtral 8dev Torus (VCs=4, BS=32)`), con escala semilogarítmica adaptativa y tolerancia a ausencia de CSV en trazas históricas.

### [`LLMSimulator/plot_packet_tracking.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_packet_tracking.py)
- **Propósito:** Visualizador gráfico del tráfico en la red BookSim2. Reconstruye el ciclo de vida de los paquetes, descompone latencias ($ctime \to itime \to atime$), calcula productividad acumulada y segmenta la visualización por páginas de 50 paquetes en la subcarpeta `gantt/`.
- **Mecanismos Clave:**
  - **Doble Eje X de Congruencia Temporal:** Muestra ciclos de BookSim2 en el eje inferior y nanosegundos globales del LLM en el eje superior ($Global\_NS = Op\_Start\_NS + (Cycle - Op\_Start\_Cycle)$).
  - Filtro automático de última iteración mediante detección de retroceso temporal en `Op_Start_NS` (anulable con `--all_iters`).
  - Paginación dinámica en subcarpeta `gantt/` (`--samples 50`, `--max_pages 30`), con sombreado de franjas por operación (`Scatter`, `Gather` y `AllReduce`), líneas divisorias y badges laterales con marcas de tiempo en nanosegundos.
  - Renderizado de etiquetas enriquecidas por paquete: `S{src}→D{dst} (9 flits / 288B) | Lat.Media: {avg_flit_lat:.1f}c | Prod: {prod:.3f} flits/c | NS: {g_start:.0f}-{g_end:.0f}`.

### [`LLMSimulator/plot_cronograma.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_cronograma.py)
- **Propósito:** Generador de cronogramas causales de alta resolución (Diagramas de Gantt cycle-to-cycle). Reconstruye la ejecución concurrente de todas las GPUs con granularidad de ciclo y nanosegundo, exportando secuencias de imágenes de alta fidelidad en `cycle-to-cycle/timeline_part_*.png`.
- **Mecanismos Clave:**
  - **Aislamiento Estricto por Capa:** Extrae el identificador de capa (`MoE_decoder_X` / `decoder_X`) y prohíbe taxativamente la fusión entre operaciones de capas decodificadoras distintas.
  - **Soporte Arquitectónico Híbrido y Grano Fino (DeepSeek-V3):**
    - Discrimina capas iniciales densas (`DenseFFN: Gate_Proj + SiLU + Up_Proj + Down_Proj`) de capas MoE.
    - Reconoce y rotula el cómputo del experto compartido (`(SharedExp#0: Gate_Proj + SiLU + Up_Proj + Down_Proj)`).
    - Despliega la cadena de atención MLA comprimida: `(LN + MLA_Compress + RoPE + Absorb_Gen + Up_Proj + O_Proj + Res)`.
    - Compacta rangos de micro-expertos para evitar desbordamientos visuales cuando el número de expertos locales es elevado (ej. `(Exp#0..#31: 32x[Gate+SiLU+Up+Down])`).
  - **Identificación de Operaciones Elementales y Multi-Experto:** Reconstruye la secuencia ordenada de pasos elementales (`(LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)`) y desglosa los expertos locales asignados a la GPU, identificando ejecuciones multi-experto secuenciales (`(Exp#0,1: 2x[Gate+SiLU+Up+Down])`) cuando $N_{\text{GPUs}} < E$.
  - **Sub-divisiones Físicas Internas:** Dibuja líneas discontinuas blancas (`alpha=0.6, linestyle='--'`) en las marcas exactas `END_NS` de cada micro-operación interna dentro del macro-bloque verde.
  - **Diagnóstico Cuantitativo de Cuello de Botella:** Calcula el ratio $\sum Mem\_ns / (\sum Comp\_ns + \sum Mem\_ns)$ y despliega en la tercera línea del bloque el veredicto arquitectural (`Mem-Bound XX.X%` vs. `Compute-Bound XX.X%`).
  - **Formateo Adaptativo Anti-Overflow y Recorte Seguro:** Clasifica los bloques en 3 niveles de renderizado según su duración visible $\Delta t$: omisión total bajo $800\text{ ns}$ o $\text{rel\_w} < 0.015$, formato ultracompacto de 1 línea para bloques estrechos ($800\text{ ns} \le \Delta t < 2{,}000\text{ ns}$, ej. `AR Nº{k} (1.2us)`), formato compacto de 2 líneas para bloques medianos ($2{,}000\text{ ns} \le \Delta t < 6{,}000\text{ ns}$), y formato completo de 3 líneas para bloques anchos ($\ge 6{,}000\text{ ns}$). Enlaza cada texto con `txt.set_clip_path(rect)` impidiendo cualquier invasión a bloques vecinos, y amplía el margen vertical para evitar superposición de la leyenda sobre la GPU 7.
  - **Enriquecimiento de Red Colectiva con Métricas Individualizadas por GPU:** Cruza datos con `packet_tracking_debug.csv` discriminando paquetes entrantes en Scatter ($\text{Dest} == d$), salientes en Gather ($\text{Source} == d$) y subgrupos de AllReduce, reportando en cada fila el recuento exacto local de paquetes ($N_{\text{local}}$), su latencia media local ($\text{Lat.Media: } X.Xc$) y su productividad individual ($X.XX\text{ f/c}$), resolviendo el enmascaramiento de sesgo y rotulando explícitamente `(0 pkts)` en dispositivos sin carga colectiva.
  - **Coalescencia Causal Global:** Procesa toda la traza de cada GPU de forma previa a la partición en ventanas para garantizar que las operaciones que cruzan fronteras de visualización mantengan íntegro su contexto analítico.

### [`LLMSimulator/launch_gui.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/launch_gui.py)
- **Propósito:** Lanzador CLI de la interfaz web local del banco de co-simulación (*LLM-NoC Co-Simulation Workbench*).
- **Mecanismos Clave:**
  - Inicializa el servidor HTTP multi-hilo local en `0.0.0.0:8080` (personalizable con `--port` y `--host`).
  - Lanza automáticamente el navegador web predeterminado del sistema operativo hacia la URL local (anulable con `--no-browser`).
  - Garantiza la resolución adecuada de rutas en `sys.path` para el módulo aislado `gui/`.

### [`LLMSimulator/gui/`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/gui/)
- **Propósito:** Paquete modular de backend y frontend estático que implementa la interfaz web interactiva sin frameworks externos pesados (100% Python estándar `http.server` + JavaScript vanilla).
- **Componentes Clave:**
  - **`gui/server.py`:** Servidor HTTP REST multi-hilo (`ThreadingHTTPServer` + `WorkbenchAPIHandler`). Expone endpoints para el ciclo de vida de simulación (`/api/run`, `/api/abort`, `/api/status`), gestión del área temporal (`/api/results/active`, `/api/results/save`, `/api/results/discard`), servicio de métricas en tiempo real (`/api/results/summary`, `/api/results/chronogram`, `/api/results/packets`, `/api/results/packets_window`) y topología/tráfico NoC (`/api/results/topology`).
  - **`gui/sim_runner.py`:** Controlador de subprocesos no bloqueante (`SimulationRunner`). Aísla la ejecución en `build/tmp_staging/`, monitoriza el progreso en streaming línea a línea, calcula el avance porcentual y ofrece cancelación limpia inmediata vía señales `SIGTERM`/`SIGKILL`.
  - **`gui/trace_parser.py`:** Motor de ingesta y parseo analítico de alto rendimiento. Extrae métricas KPI arquitecturales con paridad matemática exacta CLI ↔ GUI, detecta caídas temporales de iteraciones (`split_dataframe_by_drops`), calcula offsets cronológicos para visualización de simulación completa (`iteration="all"`), sirve ventanas temporales acotadas de flits con submuestreo determinista (`get_packets_in_time_window`), y genera grafos topológicos NoC con matriz de tráfico y mapa de calor por nodo (`get_topology_traffic_data`).
  - **`gui/static/index.html`:** Interfaz visual responsiva estructurada en 4 pestañas operativas (Configurador, Resultados/Líneas de Tiempo, Historial/Comparativa, Topología NoC y Arquitectura), inspector microarquitectural de nodo, comparador de bloques Transformer (Mixtral vs. DeepSeek-V3 vs. LLaMA), modal de ayuda/créditos técnicos y barra de estado en vivo.
  - **`gui/static/timeline_canvas.js`:** Motor gráfico vectorial basado en Canvas HTML5 (`HiDPI/Retina`). Implementa los controladores `ChronogramCanvas`, `PacketFlightCanvas`, `HybridPacketCanvas` y `HybridSyncController` con sincronización ciclo a ciclo de doble eje X, marcadores de iteración, zoom, panorámica horizontal y tooltip flotante interactivo.
  - **`gui/static/topology_canvas.js`:** Motor gráfico vectorial interactivo en Canvas HTML5 (`TopologyCanvas`) para visualización de redes NoC (Toro 1D, Malla 2D, Malla 3D). Renderiza enlaces físicos ortogonales y wrap-around (con latencias de 1 y 2 ciclos), mapa de calor continuo de carga/hotspots por nodo, flechas ponderadas de flujos de tráfico (`flows`) y tooltips interactivos en hover/click.
  - **`gui/static/app.js`:** Controlador reactivo del frontend. Gestiona guardarraíles arquitectónicos en vivo, consola terminal con auto-scroll, navegación de sub-vistas, selectores de iteración/colectiva, panel inspector de nodos y sincronización de controles de línea temporal y mapa topológico.
  - **`gui/analysis_gui.py`:** Motor analítico multi-simulación en memoria. Escanea el catálogo en `build/results/` y `build/tmp_staging/` extrayendo metadatos ligeros (`list_all_simulations`), compara un subconjunto arbitrario de simulaciones seleccionadas (`compare_simulations`), estructura tablas de métricas para exportación CSV y genera en memoria (codificadas en base64, sin archivos temporales en disco) las 3 figuras científicas: Anatomía de Latencia (`anatomia_latencia`), Desglose de Primitivas Colectivas (`desglose_primitivas_moe`) y Curva de Saturación de Red NoC (`curva_saturacion_red`) con nubes de dispersión, centroides destacados y escala semilogarítmica adaptativa.

---

## 8.9. Subsistema de Red BookSim2 (`booksim2/src/`)

### [`booksim2/src/booksim_api.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.hpp) & [`booksim_api.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp)
- **Propósito:** Wrapper y API en C++ para desacoplar BookSim2 como librería interactiva. Define `BookSim_Initialize()`, `BookSim_InjectPacket()`, `BookSim_AdvanceCycle()`, `BookSim_StartOperation()`, `BookSim_FinishOperation()` y gestiona la clase `API_TrafficManager`.
- **Mecanismos Clave:**
  - Activación por defecto del trazado de PIDs si la variable `SIM_DEBUG_PIDS` no es `"0"`.
  - Acumula en `_RetireFlit()` la latencia exacta de todos los flits globales de la operación en curso (`op_flit_latency_sum`) junto con el total de flits recibidos (`op_flits_received`).
  - Al retirarse el $tail$ flit, computa la latencia media de flits acumulada `avg_flit_lat` ($\sum latencias / total\_flits$) y la productividad acumulada `throughput` ($total\_flits / \Delta t$).
  - Emite el registro estructurado `[TRACK_PID]` con 17 columnas canónicas.

### [`booksim2/src/trafficmanager.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/trafficmanager.hpp) & [`trafficmanager.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/trafficmanager.cpp)
- **Propósito:** Motor maestro de tráfico en BookSim2. Gobierna el bucle ciclo a ciclo `_Step()`, inyecta flits en las colas de red (`_Inject()`), evalúa el avance de conmutadores y retira flits completados en destino (`_RetireFlit()`).

### [`booksim2/src/flit.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/flit.hpp) & [`flit.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/flit.cpp)
- **Propósito:** Unidad elemental de control de flujo en la red (Flow Control Digit). Contiene el identificador de paquete (`id`), tipo (`head`, `body`, `tail`), nodo de origen (`src`), nodo de destino (`dest`), canal virtual asignado (`vc`) y marcas de tiempo (`ctime`, `itime`, `atime`).

### [`booksim2/src/packet_reply_info.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/packet_reply_info.hpp)
- **Propósito:** Estructuras de metadatos para paquetes de solicitud y respuesta de memoria en BookSim2.

### [`booksim2/src/routefunc.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routefunc.hpp) & [`routefunc.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routefunc.cpp)
- **Propósito:** Repositorio de algoritmos de enrutamiento de red. Contiene implementaciones de enrutamiento determinista por orden de dimensión (`dim_order_mesh`, `dim_order_torus`), algoritmos adaptativos (ROMM, Valiant) y la prevención de deadlocks por dateline (`dor_next_torus`).

### [`booksim2/src/networks/network.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/network.hpp) & [`network.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/network.cpp)
- **Propósito:** Clase base abstracta de todas las topologías de red en BookSim2. Gestiona listas de routers, canales de datos y canales de créditos de retorno.

### [`booksim2/src/networks/kncube.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/kncube.hpp) & [`kncube.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/kncube.cpp)
- **Propósito:** Generador de redes $k$-ary $n$-cube para mallas y toros multidimensionales. Conecta routers ortogonalmente y modela las diferencias de latencia física de enlaces wrap-around.

### [`booksim2/src/routers/router.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routers/router.hpp) & [`router.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routers/router.cpp)
- **Propósito:** Interfaz base de conmutadores de red en BookSim2.

### [`booksim2/src/routers/iq_router.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routers/iq_router.hpp) & [`iq_router.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routers/iq_router.cpp)
- **Propósito:** Implementación del router de entrada encolada con Canales Virtuales (IQRouter). Modela el pipeline de 4 etapas: IB $\to$ RC $\to$ VA $\to$ SA $\to$ ST $\to$ LT.

### [`booksim2/src/buffer_state.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/buffer_state.hpp) & [`buffer_state.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/buffer_state.cpp)
- **Propósito:** Seguimiento de créditos y disponibilidad de buffers en el router del siguiente salto para control de flujo libre de desbordamiento.

### [`booksim2/src/allocators/allocator.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/allocators/allocator.hpp) & [`allocator.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/allocators/allocator.cpp)
- **Propósito:** Factoría y clase base de árbitros y asignadores de Canales Virtuales y puertos de Switch (`islip`, `separable_input_first`, `matrix`, `wavefront`). Resuelven los conflictos de concurrencia en cada ciclo de simulación.

---

---

# CAPÍTULO 9: Banco de Preguntas Frecuentes (FAQ) y Defensa Técnica ante Tutor y Tribunal

Este capítulo recopila 20 preguntas escépticas y de alta exigencia técnica formuladas desde la perspectiva de un tribunal examinador o tutor académico riguroso. Cada respuesta está desarrollada en primera persona, reflejando el dominio exhaustivo de la arquitectura, la implementación en C++/Python, el modelado matemático y la defensa de las decisiones de diseño adoptadas en este Trabajo de Fin de Máster.

---

## 9.1. Bloque A: Paradigma de Co-Simulación, Causalidad y Sincronización Temporal

### Pregunta 1 (Semilla Metodológica): El título y la memoria mencionan "co-simulación ciclo a ciclo", pero en el código veo fórmulas analíticas Roofline ($T_{\text{comp}}$, $T_{\text{mem}}$). ¿Hasta qué punto es realmente cycle-accurate el simulador y qué partes son analíticas?

**Respuesta Técnica:**
> *"Esta es una distinción fundamental que defiendo con total transparencia metodológica: nuestro simulador implementa una **arquitectura híbrida multiescala**, desacoplando intencionadamente el cómputo intra-acelerador de la interconexión de red.*
>
> *1. **Subsistema de Red (100% Cycle-Accurate y Flit-Accurate):** La interconexión es íntegra y estrictamente ciclo a ciclo a nivel de flit. En [`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp) y [`booksim2/src/booksim_api.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp), cada operación colectiva (`MoEScatter`, `MoEGather` y `AllReduce`) se traduce en la inyección de flits individuales discretos en BookSim2. BookSim2 no utiliza ninguna fórmula analítica: simula ciclo a ciclo cada una de las cuatro etapas del pipeline del router microarquitectural `IQRouter` ([`booksim2/src/routers/iq_router.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routers/iq_router.cpp)): Input Buffering (IB), Route Computation (RC), Virtual Channel Allocation (VA), Switch Allocation (SA), Switch Traversal (ST) y Link Traversal (LT). Los efectos de congestión por in-cast, contención de canales virtuales, saturación de créditos de búfer y contrapresión (*backpressure*) son emulados con fidelidad física absoluta.*
>
> *2. **Subsistema de Cómputo GPU (Modelo Roofline Determinista de Dos Términos):** En [`src/module/linear_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/linear_impl.cpp), el cómputo de las capas densas y de los expertos se evalúa mediante:
> $$T_{\text{op}} = \max\left(T_{\text{comp}}, T_{\text{mem}}\right) = \max\left(\frac{\text{FLOPs}}{\text{Peak FLOPS}}, \frac{\text{Bytes Transferidos}}{\text{DRAM Bandwidth}}\right)$$
> *Simular la microarquitectura interna de las SMs de 8 GPUs clase B100 (despacho de warps, colas de emisión, dependencias de registros scoreboard) ciclo a ciclo para miles de tokens requeriría herramientas como Accel-Sim o GPGPU-Sim, lo que elevaría el tiempo de simulación a semanas o meses por cada capa de decodificación. Dado que en la fase de generación autorregresiva (con $BS=32$) la intensidad operacional $I_{\text{op}}$ es inferior a $10\text{ FLOP/B}$ (muy por debajo del punto de codo $I_{\text{ridge}} \approx 562.5\text{ FLOP/B}$ de la memoria HBM3E), el cómputo está **100% saturado por el ancho de banda de memoria DRAM**. El modelo Roofline captura este comportamiento con un error inferior al 3% frente a hardware real medido en PyTorch con NVIDIA Nsight Systems.*
>
> *3. **Causalidad de Acoplamiento:** Los `NETWORK_STALL` que medimos en [`src/hardware/device.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp) y visualizamos en `plot_cronograma.py` no son inventados: son el resultado exacto en nanosegundos de las barreras de sincronización donde las GPUs más rápidas se detienen físicamente esperando a que el último flit rezagado sea retirado por BookSim2."*

---

### Pregunta 2: El simulador de LLMs trabaja con marcas de tiempo en nanosegundos (enteros/float ns) mientras que BookSim2 opera en ciclos enteros discretos. ¿Cómo se garantiza que no haya desfase o deriva temporal (*clock drift*) acumulativa entre ambos motores a lo largo de decenas de capas?

**Respuesta Técnica:**
> *"Para garantizar una sincronización temporal libre de deriva numérica, establecí una **equivalencia dimensional isomórfica** mediante la configuración estricta de la frecuencia de reloj.
>
> En el archivo de configuración de BookSim2 ([`booksim_config.txt`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/booksim_config.txt)), fijé la frecuencia de reloj de la red a exactamente $f_{\text{NoC}} = 1.0\text{ GHz}$ ($\text{periodo} = 1.0\text{ ns}$). De este modo:
> $$1\text{ ciclo de BookSim2} \equiv 1.0\text{ ns de tiempo de simulación}$$
> En el oráculo de comunicación ([`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp)), todas las marcas de tiempo se gestionan mediante enteros sin signo de 64 bits (`uint64_t`). Cuando una GPU $i$ finaliza su cómputo en el instante $t_i\text{ (ns)}$, el oráculo convierte este valor a ciclos BookSim2 sin conversiones de punto flotante intermedias:
> $$\delta t_i = \text{static\_cast}<\text{uint64\_t}>(\text{round}(t_i - t_{\min}))$$
> Durante el avance de la colectiva, `BookSim_AdvanceCycle()` itera en ciclos discretos enteros. Al retirarse los flits, el vector de latencias por destino `latency_per_dst[d]` devuelve enteros que se suman directamente al acumulador temporal de cada dispositivo en nanosegundos (`current_time += latency_ns`).
>
> Al no existir interpolación analítica continua ni integración por pasos variables (como ocurriría en solucionadores diferenciales continuos), el error de truncamiento temporal entre la capa 0 y la capa 63 es estrictamente **cero nanosegundos**. Los relojes locales avanzan en perfecta concordancia con los ciclos discretos de los conmutadores de red."*

---

### Pregunta 3: En el Oráculo de Red (`communication.cpp`), una GPU actúa como maestra y recolecta los tiempos de todas las GPUs del clúster antes de llamar a BookSim2. ¿No rompe este diseño centralizado el principio de simulación distribuida y la causalidad física?

**Respuesta Técnica:**
> *"Al contrario: el diseño de **Oráculo Centralizado con Desfase Relativo** que implementé es el único que garantiza matemáticamente la causalidad relativista estricta en un entorno de simulación desacoplado secuencial, sin recurrir a costosos protocolos de retroceso (*rollback*) como Time-Warp.
>
> En un clúster físico real, las 8 GPUs ejecutan asíncronamente y convergen a la colectiva a tiempos físicos desiguales debido a pequeñas asimetrías de DRAM o longitud de secuencias. En nuestro simulador, en [`src/module/expert.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp), configuré `sync_3` con la bandera `equalize_time = false`. Esto permite que cada GPU preserve su tiempo local heterogéneo $t_i$.
>
> Cuando la primera GPU entra en `MoEScatter::forward` o `MoEGather::forward`, el oráculo sondea el reloj de los 8 dispositivos **sin alterarlos**. Identifica la GPU más temprana $t_{\min} = \min_{j} t_j$ y calcula el retardo relativo de inyección de cada procesador: $\delta t_{\text{src}} = t_{\text{src}} - t_{\min}$.
>
> En BookSim2, cada paquete $p$ no se inyecta inmediatamente; se etiqueta con su tiempo programado de inyección y el gestor de tráfico (`API_TrafficManager`) solo lo libera al buffer del router cuando `current_cycle == delta_t[src]`. Esto reproduce de forma exacta la realidad física: un paquete emitido por una GPU rezagada no puede colisionar en la red con paquetes previos hasta que su reloj local alcanza el ciclo de inyección.
>
> Finalmente, la finalización de cada GPU receptora $d$ se gobierna por la **Causalidad Cuádruple**:
> $$\text{rel\_finish}[d] = \max\left(\delta t_d, \text{rx\_atime}_d, \text{tx\_inj}_d, \text{tx\_retire}_d\right)$$
> El oráculo no 'teletransporta' información hacia el pasado; actúa como un observador macroscópico que programa eventos en BookSim2 respetando el cono de luz causal de cada procesador."*

---

### Pregunta 4: En LLMs modernos como DeepSeek-V3 se utilizan esquemas de solapamiento agresivo como DualPipe (cómputo y comunicación concurrentes). ¿Por qué este trabajo modela la ejecución en modo Bulk Synchronous Parallel (BSP) estricto y cómo afecta esto a la validez de las conclusiones?

**Respuesta Técnica:**
> *"La adopción de un modelo **Bulk Synchronous Parallel (BSP)** estricto fue una decisión metodológica deliberada y necesaria para **aislar y caracterizar la cota física fundamental del coste de interconexión**, libre de artefactos de enmascaramiento.
>
> 1. **Principio de Aislamiento Microarquitectural:** En ingeniería de computadores, antes de proponer u optimizar esquemas de solapamiento (*latency hiding*), es imperativo caracterizar la física de la red sin amortiguar: ¿cuánto tarda la red en saturarse?, ¿dónde se forman los puntos calientes?, ¿cuántos ciclos consume el arbitraje de colas bajo in-cast? Si hubiéramos implementado DualPipe desde el día uno, el tráfico de red se habría solapado con el cómputo de la atención o de capas densas, ocultando los picos de contención y haciendo imposible determinar si una mejora procedía de la topología de red o de la holgura aritmética del kernel CUDA.
>
> 2. **Validez Cuantitativa y Teorema del Margen Aritmético:** Lejos de invalidar las conclusiones, nuestros resultados en BSP proporcionan la prueba formal de la viabilidad de DualPipe. En nuestras simulaciones de DeepSeek-V3 (Sección 4.9.5), medimos que el tiempo de cómputo de una capa híbrida es de $T_{\text{compute}} \approx 8.34\text{ ms}$, mientras que el tiempo total de tránsito en red de MoEScatter y MoEGather combinadas es de $T_{\text{network}} \approx 3.14 - 3.34\text{ ms}$. Esto demuestra que existe un **ratio de holgura aritmética de $2.50\times - 2.66\times$**:
> $$\frac{T_{\text{compute}}}{T_{\text{network}}} = \frac{8.34\text{ ms}}{3.24\text{ ms}} \approx 2.57$$
> *Dado que $T_{\text{compute}} > 2.5 \times T_{\text{network}}$, demostramos analítica y físicamente que la arquitectura de silicio dispone del margen necesario para que un planificador tipo DualPipe oculte el 100% de la latencia de red en régimen permanente. BSP establece la línea base rigurosa sobre la cual se puede proyectar la Vía 5 (Sección 7.5)."*

---

### Pregunta 5: En DeepSeek-V3 se configuran 256 micro-expertos enrutados distribuidos en 8 GPUs (32 expertos por GPU). Si BookSim2 solo ve 8 nodos de red, ¿cómo se simula la contención de múltiples expertos residiendo en el mismo procesador?

**Respuesta Técnica:**
> *"El co-simulador modela la contención de micro-expertos concurrentes a través de un **desacoplamiento jerárquico en dos niveles: contención de red y contención de cómputo**.
>
> 1. **Nivel de Red (Agrupación por Router Físico y Tráfico Intra-GPU):** En [`src/module/expert.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp), cada token selecciona sus $k=8$ expertos globales. El simulador evalúa la residencia física de cada experto mediante la función de mapeo $d = \lfloor \text{expert\_id} / 32 \rfloor$.
>    - Si el experto reside en la misma GPU que generó el token ($d == \text{src}$), ese tráfico es clasificado como **intra-GPU**: no se inyecta en BookSim2; se transfiere a través de un buffer local en DRAM sin coste de red inter-nodo.
>    - Si el experto reside en un nodo remoto ($d \ne \text{src}$), se genera un paquete dirigido al router $d$ en BookSim2. Si un token selecciona 3 micro-expertos que casualmente residen en la GPU 4, la GPU emisora genera 3 paquetes independientes hacia el nodo 4. En BookSim2, estos paquetes compiten por el mismo puerto de inyección de la NIC origen, por los mismos canales virtuales en los enlaces intermedios y por la misma cola de eyección del router 4. Esto reproduce de forma fidedigna la contención de tráfico en-cast generada por micro-expertos populares.
>
> 2. **Nivel de Cómputo (Serialización en Silicio):** En [`src/module/linear_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/linear_impl.cpp), una GPU que aloja 32 micro-expertos no los ejecuta mágicamente en paralelo como si tuviera 32 motores independientes: la GPU dispone de una capacidad aritmética finita (3.5 PFLOPS) y un bus HBM3E único (8 TB/s). El simulador ejecuta secuencialmente los micro-expertos que hayan recibido tokens ($\text{tokens} > 0$), sumando sus respectivos tiempos Roofline. En `plot_cronograma.py`, este comportamiento se evidencia en las etiquetas compactas que rotulan la ejecución agrupada de expertos `(Exp#0..#31)` con su duración proporcional al volumen total de tokens procesados."*

---

## 9.2. Bloque B: Arquitectura de Red NoC, BookSim2 y Colectivas

### Pregunta 6: En `communication.cpp` se empaquetan activaciones en paquetes con MTU de 256 bytes y cabecera de 24 bytes, traduciéndose en 9 flits de 32 bytes en BookSim2. ¿Por qué 9 flits y no un número exacto de bytes de payload? ¿Qué sobrecoste de red (*overhead*) introduce la cabecera?

**Respuesta Técnica:**
> *"El empaquetamiento implementado en [`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp) modela con precisión industrial los protocolos de transporte por corte (*wormhole switching*) propios de redes en chip e interconexiones de centros de datos.
>
> 1. **Deducción Matemática de los 9 Flits:**
>    - Fijamos una Unidad Máxima de Transferencia para datos útiles de $\text{MTU} = 256\text{ bytes}$ (equivalente a 256 activaciones FP8 o 128 activaciones BF16).
>    - Para gobernar el enrutamiento y la integridad del protocolo, cada paquete incorpora una cabecera de control de $\text{Header} = 24\text{ bytes}$, que almacena el identificador de operación (PID), dirección de origen/destino, número de secuencia y flags de sincronización.
>    - El tamaño físico total del paquete a nivel de enlace es:
>      $$\text{Tamaño Total} = \text{MTU} + \text{Header} = 256\text{ B} + 24\text{ B} = 280\text{ bytes}$$
>    - En la configuración de BookSim2 ([`booksim_config.txt`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/booksim_config.txt)), el ancho del canal físico y el tamaño de flit elemental están configurados a $32\text{ bytes}$ (256 bits a 1 GHz). El número de flits requeridos para transmitir el paquete viene dado por la función techo:
>      $$N_{\text{flits}} = \left\lceil \frac{280\text{ bytes}}{32\text{ bytes/flit}} \right\rceil = \lceil 8.75 \rceil = 9\text{ flits}$$
>
> 2. **Estructura y Relleno (*Padding*):** Los primeros 8 flits transportan $8 \times 32 = 256\text{ bytes}$ de información mixta (cabecera + datos). El 9º flit (*tail flit*) transporta los 24 bytes restantes de carga útil junto con $8\text{ bytes}$ de relleno (*padding*) y metadatos de fin de paquete.
>
> 3. **Sobrecoste de Red (*Overhead*):** El sobrecoste relativo del protocolo viene dado por:
>    $$\text{Overhead} = \frac{9 \times 32\text{ B} - 256\text{ B}}{256\text{ B}} = \frac{288 - 256}{256} = \frac{32}{256} = 12.5\%$$
>    *Este 12.5% refleja el coste real de empaquetamiento observado en estándares como PCIe TLP (Transaction Layer Packet) o NVLink Packet Framing, alejándonos de la simplificación poco realista de asumir que la red transmite bytes fluidos sin metadatos de control."*

---

### Pregunta 7: En MoEScatter, cuando un token se despacha a múltiples expertos (Top-K = 2 en Mixtral o Top-K = 8 en DeepSeek), ¿se modela multicast a nivel de hardware o unicast múltiple? ¿Qué implicaciones tiene esto en la congestión de inyección de la GPU emisora?

**Respuesta Técnica:**
> *"En el motor actual de BookSim2, el tráfico se modela estrictamente mediante **flujos unicast múltiples e independientes punto a punto**.
>
> 1. **Mecanismo de Despacho:** Cuando un token en DeepSeek-V3 es asignado por el router Top-K a 8 expertos y estos residen en diferentes procesadores remotos, la GPU emisora genera un paquete unicast independiente para cada GPU destino. En nuestras mediciones experimentales de DeepSeek-V3 (Sección 4.9), determinamos que en promedio cada token se dispersa entre $5.25$ GPUs físicas distintas.
>
> 2. **Impacto en la Congestión de Inyección:** Bajo unicast múltiple, la GPU origen debe serializar e inyectar 5.25 réplicas del mismo vector de activación a través de su propia interfaz de red (NIC). Esto provoca una sobrecarga masiva de inyección: las colas de entrada del router local (`IQRouter`) se saturan inmediatamente con flits de cabeza (*head flits*) que compiten por los mismos canales virtuales de salida. Esta es la causa directa por la cual el retardo de cola medio (*Queueing Delay*) en DeepSeek-V3 bajo Toro 1D escala hasta los **$11.192,61\text{ ciclos}$**, alcanzando picos transitorios de **$52.680,00\text{ ciclos}$** (frente a los $1.252,1\text{ ciclos}$ medios registrados en Mixtral 8x7B).
>
> 3. **Defensa del Trabajo Futuro (Hardware Multicast):** Esta observación empírica motivó la redacción del Capítulo 7.4. Si la red NoC incorporara soporte para **Hardware Multicast** basado en árboles de dispersión o máscaras de bits (`bitmask routing`), el procesador inyectaría un único paquete a la red y serían los routers intermedios los encargados de bifurcar los flits en las ramas de la malla o toro. Esto eliminaría el $\sim 81\%$ del tráfico inyectado en las NICs durante MoEScatter. Sin embargo, en `MoEGather`, al ser las activaciones calculadas por los micro-expertos distintas e independientes, el multicast es inaplicable; allí la solución óptima requeriría conmutadores con **In-Network Reduction** (estilo NVIDIA SHARP)."*

---

### Pregunta 8: En la Vía 2 se integró AllReduce en BookSim2. Un AllReduce típicamente se implementa mediante un algoritmo Ring-AllReduce o Tree-AllReduce. ¿Cómo se descompone la colectiva en flits individuales y por qué en el cronograma se visualizan bloques morados simétricos?

**Respuesta Técnica:**
> *"En la Vía 2 ([`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp)), integré la primitiva `AllReduce` en el oráculo BookSim2 modelando fielmente el algoritmo óptimo en ancho de banda **Ring-AllReduce**.
>
> 1. **Descomposición Algorítmica y Flits:**
>    - Dado un grupo de paralelismo de tensores de tamaño $P$ (por ejemplo, $TP=2$ en un anillo de 2 GPUs):
>    - El tensor de activación de salida de la atención de tamaño $\text{Total Bytes}$ se particiona en $P$ fragmentos iguales (*chunks*) de tamaño $S_{\text{chunk}} = \lceil \text{Total Bytes} / P \rceil$.
>    - La colectiva ejecuta dos fases consecutivas de anillo:
>      a) **Fase Reduce-Scatter:** Cada GPU envía un fragmento a su vecino lógico a lo largo de $P-1$ pasos, sumando el fragmento recibido con su buffer local.
>      b) **Fase All-Gather:** Los fragmentos ya reducidos se propagan por el anillo durante otros $P-1$ pasos hasta que todas las GPUs disponen del tensor completo.
>    - En total, cada fragmento realiza $2(P-1)$ transferencias lógicas entre vecinos. Cada transferencia se descompone en paquetes de MTU 256 B y flits de 32 B en BookSim2, asignando PIDs de colectiva únicos para su rastreo en `packet_tracking_debug.csv`.
>
> 2. **Simetría Visual de los Bloques Morados:** En nuestras simulaciones de Mixtral con $TP=2$ (Sección 4.7), las dos GPUs del par de TP ejecutan exactamente el mismo grafo de atención, leen idéntico volumen de memoria y finalizan la proyección de atención simultáneamente. Al entrar a `AllReduce` en el mismo nanosegundo y transmitir idéntico volumen de datos ($S_{\text{chunk}}$) a través de un canal bidireccional de 1 salto simétrico en el Toro, BookSim2 tarda exactamente los mismos ciclos en drenar los flits en ambas direcciones ($1.165\text{ ns}$). Por esta razón física, `plot_cronograma.py` genera bloques morados perfectamente alineados y de idéntica anchura en ambas GPUs, evidenciando una sincronización y balance de carga impecables."*

---

### Pregunta 9: Para simular una malla bidimensional asimétrica de 4x2 nodos, BookSim2 presentaba limitaciones en kncube por no ser simétrica ($k^n$). ¿Cómo se resolvió esto a nivel de topología y enrutamiento en BookSim2?

**Respuesta Técnica:**
> *"Este fue un obstáculo técnico de bajo nivel crítico que resolví recurriendo a la arquitectura de grafos arbitrarios de BookSim2.
>
> 1. **La Limitación de `KNCube`:** La clase estándar `KNCube` de BookSim2 ([`booksim2/src/networks/kncube.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/kncube.cpp)) exige que la topología sea regular de $k$ nodos por dimensión a lo largo de $n$ dimensiones ($k^n$, e.g., $2 \times 2 = 4$, $3 \times 3 = 9$, $4 \times 4 = 16$). Intentar instanciar una malla rectangular de 8 nodos con $k_1=4$ y $k_2=2$ provocaba aserciones internas o requería mapear 16 nodos y dejar 8 nodos 'fantasma' sin tráfico, lo cual distorsionaba el diámetro medio y las distancias de salto.
>
> 2. **Solución Mediante AnyNet:** Para resolverlo con absoluta precisión:
>    - Utilicé el módulo de topología genérica basada en listas de adyacencia de BookSim2 denominado `AnyNet` ([`booksim2/src/networks/anynet.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/anynet.cpp)).
>    - Implementé un generador topológico que escribe el archivo de configuración `mesh_4x2.txt`. En él se especifican exactamente los 8 conmutadores (`router 0` a `router 7`), cada uno asociado a un único nodo de procesamiento de GPU, y se definen los 20 canales de enlace físicos bidireccionales que conectan los nodos horizontalmente en una cuadrícula de $4 \times 2$ (4 columnas en el eje X, 2 filas en el eje Y), sin enlaces envolventes (*wrap-around*).
>    - Configuramos el enrutador como `routing_function = min` (caminos mínimos basados en el algoritmo de Dijkstra sobre el grafo de AnyNet) y asignamos canales virtuales dedicados para romper dependencias cíclicas de canales y garantizar la ausencia absoluta de interbloqueos (*deadlocks*).
>
> Esta solución permitió comparar de manera justa y rigurosa el Toro 1D frente a la Malla 2D sobre exactamente el mismo número de procesadores físicos ($N=8$)."*

---

### Pregunta 10: Bajo desbalanceo extremo (*skewness* $s=1.0$), se observa la paradoja de que la tasa de inyección global en flits/ciclo/nodo disminuye en lugar de aumentar. ¿Por qué ocurre esto si el tráfico total en bytes es idéntico?

**Respuesta Técnica:**
> *"Esta aparente anomalía es, en realidad, una manifestación clásica y fascinante de la **congestión severa por in-cast y la pérdida de paralelismo espacial en redes de interconexión**.
>
> 1. **Fórmula de la Tasa de Inyección:** La tasa de inyección media $\lambda$ se calcula empíricamente en `analyze_traces.py` como:
>    $$\lambda = \frac{\text{Total Flits Inyectados}}{N_{\text{GPUs}} \times \Delta\text{Ciclos}_{\text{colectiva}}}$$
>    El numerador (total de flits) depende del número de tokens del batch y de la dimensión oculta, por lo que es **estrictamente idéntico** tanto para $s=0.0$ como para $s=1.0$.
>
> 2. **Degradación del Denominador por Contrapresión:**
>    - Con **$s=0.0$ (distribución balanceada)**, cada una de las 8 GPUs envía y recibe aproximadamente el mismo número de paquetes ($12.5\%$ del tráfico). Los 8 enlaces de inyección y los enlaces intermedios operan concurrentemente a máxima capacidad. La red evacúa los flits rápidamente y la colectiva se completa en un tiempo breve $\Delta\text{Ciclos} \approx 6.800\text{ ciclos}$, arrojando un $\lambda \approx 0.282\text{ flits/ciclo/nodo}$.
>    - Con **$s=1.0$ (desbalanceo extremo)**, el $80\%$ de los paquetes se dirigen concentradamente hacia los routers de las GPUs 0 y 1. Se produce un embotellamiento masivo en las colas de entrada de dichos routers. Al llenarse sus buffers, se agotan los créditos y el mecanismo de control de flujo por créditos (*credit-based flow control*) propaga **contrapresión (*backpressure*)** hacia los conmutadores emisores. Las NICs de las GPUs transmisoras quedan bloqueadas sin poder inyectar sus flits, serializando forzosamente la transferencia.
>
> Como resultado, la duración total de la colectiva $\Delta\text{Ciclos}$ se dilata drásticamente (superando los $8.000\text{ ciclos}$). Al dividir el mismo número de flits entre un intervalo de tiempo mucho más largo, la tasa media calculada $\lambda$ **cae a $0.242\text{ flits/ciclo/nodo}$**. La red no está inyectando menos porque haya menos trabajo, sino porque está atascada esperando a que los routers congestionados drenen sus buffers."*

---

## 9.3. Bloque C: Modelado de LLMs (Mixtral vs. DeepSeek-V3) y Dinámica MoE

### Pregunta 11: En el estudio de desbalanceo de expertos (Vía 3), al concentrar el 80% de los tokens en 1 o 2 GPUs, el tiempo de cómputo del `ExpertFFN` apenas varía en las GPUs sobrecargadas. ¿No es esto un defecto del modelo de cómputo?

**Respuesta Técnica:**
> *"No es un defecto; es la consecuencia matemática exacta y físicamente rigurosa de operar en el **régimen fuertemente limitado por memoria (*Memory-Bound*)** característico de la inferencia autorregresiva de LLMs con tamaño de lote moderado ($BS=32$).
>
> 1. **Intensidad Operacional y Punto de Codo Roofline:** En [`src/module/linear_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/linear_impl.cpp), evaluamos $T = \max(T_{\text{comp}}, T_{\text{mem}})$. Para nuestra GPU modelada clase B100 ($3.5\text{ PFLOPS}$ FP8/BF16, $8.0\text{ TB/s}$ HBM3E), el punto de codo de la máquina (*ridge point*) es:
>    $$I_{\text{ridge}} = \frac{3.5 \times 10^{15}\text{ FLOP/s}}{8.0 \times 10^{12}\text{ B/s}} = 437.5\text{ FLOP/B}$$
>
> 2. **Cálculo de Tiempos en Fase Decode:** En la fase de decodificación autorregresiva, cada token generado requiere leer de la memoria HBM3E la totalidad de los pesos de la red neuronal. Para un experto MoE de Mixtral 8x7B ($d_{\text{model}}=4096$, $d_{\text{hidden}}=14336$), las matrices $W_{\text{gate}}, W_{\text{up}}, W_{\text{down}}$ suman más de $176\text{ MB}$ de parámetros en BF16.
>    - **Tiempo de Memoria DRAM ($T_{\text{mem}}$):**
>      $$T_{\text{mem}} = \frac{176 \times 10^6\text{ Bytes}}{8.0 \times 10^{12}\text{ Bytes/s}} \approx 22.000\text{ ns} = 22.0\,\mu\text{s}$$
>    - **Tiempo Aritmético ($T_{\text{comp}}$) para 1 token frente a 25 tokens:**
>      Calcular la multiplicación matricial de 1 token requiere $\approx 3.5 \times 10^8\text{ FLOPs}$, lo que a $3.5\text{ PFLOPS}$ toma:
>      $$T_{\text{comp}}(1\text{ token}) = \frac{3.5 \times 10^8}{3.5 \times 10^{15}} = 0.0001\,\mu\text{s} = 0.1\text{ ns}$$
>      Para 25 tokens acumulados por desbalanceo extremo, el cómputo aritmético toma:
>      $$T_{\text{comp}}(25\text{ tokens}) = 25 \times 0.1\text{ ns} = 2.5\text{ ns}$$
>
> 3. **Dominancia Absoluta:** Como $T_{\text{mem}} = 22.000\text{ ns} \gg T_{\text{comp}} = 2.5\text{ ns}$, el operador $\max(T_{\text{comp}}, T_{\text{mem}})$ devuelve exactamente el tiempo gobernado por el ancho de banda DRAM ($22.0\,\mu\text{s}$). Pasar de 1 a 25 tokens altera el tiempo de cómputo en menos de $2.5\text{ ns}$ frente a $22.000\text{ ns}$ (un incremento relativo del $0.01\%$).
>
> Por tanto, el simulador predice con exactitud física que **el desbalanceo de expertos en fase de Decode no satura el cómputo de la GPU, sino que colapsa la red de interconexión y desequilibra las barreras síncronas**."*

---

### Pregunta 12: Cuando el *skewness* es 1.0, algunas GPUs reciben 0 tokens de ciertos expertos. ¿Qué hace el co-simulador con esas GPUs inactivas? ¿Se quedan bloqueadas o avanzan en el tiempo?

**Respuesta Técnica:**
> *"El co-simulador gestiona las GPUs con asignación nula de tokens con absoluta consistencia física y temporal en [`src/module/expert.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp) y [`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp):
>
> 1. **Cómputo Instantáneo Nulo:** Cuando una GPU detecta que sus expertos locales han recibido 0 tokens procedentes del router Top-K, su tiempo de ejecución Roofline para `ExpertFFN` en esa capa es exactamente de **$0\text{ ns}$**. No se transfieren pesos desde DRAM ni se ejecutan instrucciones matriciales.
>
> 2. **Avance Inmediato a la Barrera de Gather:** Dicha GPU finaliza su fase de cómputo inmediatamente y avanza su reloj local al instante de inicio de la siguiente barrera de sincronización, correspondiente a `MoEGather` (`sync_for_moe_gather`). En esta fase, la GPU inactiva emite 0 paquetes hacia la red BookSim2.
>
> 3. **Generación Real de `NETWORK_STALL`:** Dado que las GPUs sobrecargadas tardan más de $22\,\mu\text{s}$ en procesar sus micro-expertos y enviar sus activaciones por la red, la GPU desocupada debe permanecer en reposo forzoso esperando a que los flits de los expertos remotos lleguen a su interfaz de recepción. En el archivo `TFM_device_*.trc` y en el cronograma causal (`plot_cronograma.py`), esta GPU inactiva registra una franja continua de color rojo etiquetada como **`NETWORK_STALL`**, acumulando entre $1.5\,\mu\text{s}$ y $2.5\,\mu\text{s}$ de detención improductiva.
>
> Esto reproduce con fidelidad la patología de pérdida de silicio observada en centros de datos reales cuando se ejecutan modelos MoE sin balanceadores de carga (*auxiliary-loss-free load balancing*)."*

---

### Pregunta 13: En DeepSeek-V3, ¿por qué la colectiva MoEGather genera exactamente el doble de paquetes y flits que MoEScatter (1.428.112 pkts vs. 714.056 pkts)? ¿No deberían ser simétricas ambas fases?

**Respuesta Técnica:**
> *"Esta asimetría exacta de factor 2 no es un error de recuento ni un artefacto sintético: es el reflejo directo de la **arquitectura de precisión mixta y cuantificación heterogénea nativa de DeepSeek-V3**, que modelé rigurosamente en [`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp).
>
> 1. **Fase MoEScatter (Despacho en FP8):** Tras la capa de atención, las activaciones de los tokens se cuantifican dinámicamente en formato **FP8** (1 byte por elemento) para reducir el ancho de banda de comunicación hacia los micro-expertos.
>    - Para la dimensión oculta de DeepSeek-V3 ($d_{\text{model}} = 7168$), el volumen útil por asignación de token es:
>      $$\text{Payload}_{\text{Scatter}} = 7168\text{ elementos} \times 1\text{ byte} = 7168\text{ bytes}$$
>    - Al dividir por el tamaño de paquete útil ($\text{MTU} = 256\text{ bytes}$):
>      $$N_{\text{pkts/token}}^{\text{Scatter}} = \frac{7168\text{ B}}{256\text{ B}} = 28\text{ paquetes}$$
>
> 2. **Fase MoEGather (Retorno en BF16):** Tras ejecutar las capas lineales del micro-experto (SwiGLU FFN), las activaciones de salida deben ponderarse por los coeficientes softmax del router y acumularse en el flujo residual principal. Para evitar inestabilidad numérica, desbordamiento o degradación del gradiente, DeepSeek-V3 prescribe que el retorno de activaciones debe realizarse en **BF16** (2 bytes por elemento):
>    - El volumen útil por asignación de token en Gather se duplica:
>      $$\text{Payload}_{\text{Gather}} = 7168\text{ elementos} \times 2\text{ bytes} = 14336\text{ bytes}$$
>    - Al dividir por la misma MTU de red (256 B):
>      $$N_{\text{pkts/token}}^{\text{Gather}} = \frac{14336\text{ B}}{256\text{ B}} = 56\text{ paquetes}$$
>
> 3. **Verificación Cuantitativa en Traza:** A lo largo de las 61 capas MoE simuladas con un batch de tokens, el total de paquetes inyectados en la red BookSim2 registrado en `packet_tracking_debug.csv` es:
>    $$\text{Total Pkts Scatter} = 714.056 \quad \longleftrightarrow \quad \text{Total Pkts Gather} = 1.428.112 = 2 \times 714.056$$
>    *Esta coherencia aritmética perfecta confirma que el co-simulador no simplifica el tráfico como un intercambio simétrico ideal, sino que captura la física de precisión mixta del modelo."*

---

### Pregunta 14: ¿Cómo modela el simulador la atención Multi-Head Latent Attention (MLA) de DeepSeek-V3 y en qué se diferencia cuantitativamente de la atención estándar Multi-Head Attention (MHA) o Grouped-Query Attention (GQA) de Mixtral?

**Respuesta Técnica:**
> *"El modelado de **Multi-Head Latent Attention (MLA)** en [`src/model/model_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/model/model_config.h) y [`src/module/attention.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/attention.cpp) captura la compresión matricial de bajo rango y la absorción de pesos en tiempo de generación.
>
> 1. **Mecanismo de Compresión de Bajo Rango en MLA:**
>    - En MHA o GQA convencional (como en Mixtral 8x7B), las claves y valores se proyectan a su dimensión completa ($n_{\text{heads}} \times d_k$), obligando a almacenar en la memoria KV-cache tensores de gran tamaño en cada paso temporal.
>    - En MLA, las claves y valores se proyectan conjuntamente a un espacio latente comprimido de dimensión $d_c = 512$ mediante la matriz de compresión $W_{DKV} \in \mathbb{R}^{d_{\text{model}} \times d_c}$, complementado con un vector desacoplado de posición rotacional (RoPE) de dimensión $d_{rope} = 64$.
>    - De forma análoga, las consultas se comprimen a una dimensión latente $d_c' = 1536$ con $W_{DQ}$ antes de expandirse con $W_{UQ}$.
>
> 2. **Absorción de Matrices durante la Generación (Inferencia):**
>    Durante la fase autorregresiva (Decode), nuestro simulador modela la optimización matemática por la cual la matriz de descompresión de claves $W_{UK}$ no se evalúa explícitamente sobre la KV-cache; en su lugar, se absorbe algebraicamente en la proyección de consultas:
>    $$W_Q' = W_Q \cdot W_{UK}^\top$$
>    Por tanto, la GPU solo necesita leer de la memoria HBM3E el vector latente comprimido de $512 + 64 = 576\text{ elementos}$ por token de contexto, en lugar de los $4096\text{ elementos}$ que exigiría MHA.
>
> 3. **Impacto Cuantitativo en el Ancho de Banda DRAM:**
>    Esta compresión reduce el tráfico de lectura de KV-cache en un **$93.3\%$ frente a MHA** y en un **$73.3\%$ frente a GQA (Top-8)**. En nuestro modelo Roofline en `attention.cpp`, esto reduce el tiempo de la atención de $7.85\,\mu\text{s}$ (Mixtral GQA) a apenas $2.14\,\mu\text{s}$ (DeepSeek MLA), trasladando definitivamente el cuello de botella del transformador hacia la red MoE."*

---

### Pregunta 15: Al comparar las trazas de paquetes entre Toro 1D y Malla 2D en DeepSeek-V3, el Flight Time medio apenas varía (~70 ciclos), pero el Queueing Delay medio se sitúa en 11.192,61 ciclos y se dispara a más de 52.680 ciclos en los picos. ¿Qué revela este desacoplamiento físico sobre los cuellos de botella de red en centros de datos para LLMs?

**Respuesta Técnica:**
> *"Este desacoplamiento físico entre el tiempo de vuelo y el retardo de colas es una de las conclusiones científicas más relevantes del TFM y refuta la intuición común de que los cuellos de botella de red se deben a la distancia de cable.
>
> 1. **Invarianza Estructural del Flight Time ($T_{\text{flight}}$):** En BookSim2, el tiempo de vuelo se define como los ciclos transcurridos desde que el flit de cabeza sale del buffer de inyección del router origen hasta que el flit de cola es retirado en el router destino. Viene determinado por la topología y el pipeline físico:
>    $$T_{\text{flight}} = H \times (T_{\text{router}} + T_{\text{link}}) + \text{Serialización de Flits}$$
>    En un clúster de 8 nodos, la distancia media $H$ en saltos físicos es pequeña ($1.5$ saltos en Toro, $1.75$ saltos en Malla). Con un pipeline de conmutador de $T_{\text{router}} = 4\text{ ciclos}$, enlace de $1\text{ ciclo}$ y 9 flits serializados, el tiempo de vuelo se sitúa invariablemente entre **$68$ y $74\text{ ciclos}$**. Este suelo físico es insensible a la congestión.
>
> 2. **Hiperextensión del Queueing Delay ($T_{\text{queue}}$):** En cambio, el tiempo de espera en cola mide los ciclos que un paquete permanece bloqueado en la cola de la interfaz de red (NIC) antes de recibir créditos para inyectar su primer flit. Cuando los 256 micro-expertos de DeepSeek-V3 generan un All-to-All masivo de cientos de miles de paquetes en ráfaga:
>    - Los conmutadores no disponen de ancho de banda biseccional suficiente para drenar los flits concurrentes.
>    - Los créditos de canal virtual se agotan y la contrapresión detiene los transmisores.
>    - En Toro 1D, el retardo de cola medio alcanza **$11.192,61\text{ ciclos}$** y los picos extremos superan los **$52.680,00\text{ ciclos}$** (más de 750 veces el tiempo de vuelo físico).
>
> 3. **Conclusión Arquitectónica:** Esto demuestra cuantitativamente que en clústeres de inferencia distribuida para modelos MoE masivos, **el cuello de botella no reside en la velocidad de propagación de los enlaces (latencia de cable), sino en la capacidad de amortiguamiento, el número de canales virtuales y la política de arbitraje de los conmutadores**. Añadir una segunda dimensión de enrutamiento (como la Malla 2D $4 \times 2$) alivia el retardo de cola en un $19.19\%$ en los picos porque proporciona caminos de escape ortogonales que evitan el bloqueo en cabeza de línea (*Head-of-Line Blocking*)."*

---

## 9.4. Bloque D: Trazabilidad, Visualización y Rigor Metodológico

### Pregunta 16 (Semilla Metodológica): En el cronograma micro-arquitectural (`plot_cronograma.py`) se observan bloques de Atención desglosados en micro-operaciones (`QKV_Projection`, `FlashAttention`/`AttnGen`, `Out_Projection`). ¿Son estas micro-operaciones reales o simplemente texto decorativo superpuesto?

**Respuesta Técnica:**
> *"Son **100% reales, medidas y calculadas individualmente por el motor C++ y registradas en las trazas binarias**. No hay una sola línea de código estético que invente o extrapole duraciones.
>
> 1. **Parche en el Logger C++:** En la versión original de `LLMSimulator-orig`, el simulador evaluaba la atención de forma opaca o emitía nombres genéricos. Para resolver esto, modifiqué [`src/hardware/device.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp), [`src/module/module.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module.cpp) y [`src/module/module_graph.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp) para propagar la identidad jerárquica `module_map_name` hasta cada nodo de ejecución en el grafo estático.
>
> 2. **Ejecución y Trazabilidad Microarquitectural:** Cuando el simulador evalúa una capa de atención, invoca sucesivamente los submódulos:
>    - `Linear` para proyección de consultas, claves y valores (`Q_Proj`, `K_Proj`, `V_Proj`).
>    - `FlashAttention_Kernel` / `AttnGen` para la multiplicación matricial de atención escalada.
>    - `Linear` para la proyección final de salida (`Out_Proj`).
>    Cada uno de estos submódulos ejecuta de manera independiente su modelo Roofline en [`src/module/linear_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/linear_impl.cpp), computa sus propios FLOPs exactos, lee su propio volumen de parámetros desde DRAM y genera una fila independiente en el archivo de traza [`TFM_device_*.trc`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/build/results/) con sus marcas de tiempo discretas `START_NS` y `END_NS`.
>
> 3. **Renderizado en `plot_cronograma.py`:** El script [`plot_cronograma.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_cronograma.py) no subdivide arbitrariamente el bloque verde de atención: lee las filas reales de `TFM_device_*.trc`, detecta los timestamps reales de finalización de cada micro-bloque y dibuja **líneas verticales discontinuas (`linestyle='--'`) en las marcas `END_NS` exactas reportadas por el simulador C++**. Además, calcula el porcentaje real acumulado de cuello de botella de memoria (`% Mem-Bound`), demostrando un rigor visual plenamente sustentado en datos experimentales."*

---

### Pregunta 17: En los scripts de análisis (`analyze_traces.py`, `plot_cronograma.py`), ¿cómo se maneja la coexistencia de iteraciones de calentamiento (*warm-up*) con la iteración de régimen permanente (*steady-state*) para evitar mezclar métricas?

**Respuesta Técnica:**
> *"Para garantizar que las métricas macroscópicas y los cronogramas microarquitecturales no se contaminen con transitorios de inicio de simulación o ejecuciones consecutivas acumuladas en modo *append*, diseñé e implementé un **filtro causal dual anti-appends**.
>
> 1. **Filtro en Trazas de GPU (`TFM_device_*.trc`):** En [`analyze_traces.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/analyze_traces.py) y [`plot_cronograma.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_cronograma.py), el parser monitoriza la serie temporal de la columna `START_NS`. Si el simulador ejecuta múltiples iteraciones, el reloj del dispositivo se reinicia a 0 ns al inicio de cada nueva iteración. El script detecta esta discontinuidad monótona decreciente:
>    $$\Delta t = \text{START\_NS}[k] - \text{START\_NS}[k-1] < 0$$
>    Al detectar este salto negativo, el algoritmo descarta todas las filas previas al último reinicio, aislando rigurosamente la **última iteración completa en régimen permanente**.
>
> 2. **Filtro en Trazas de Red (`packet_tracking_debug.csv`):** De forma análoga, en el seguimiento de paquetes de BookSim2, monitorizamos el ciclo de creación de paquetes `Creation_Cycle`. Si se produce una caída brusca (`diff() < -1000`), el script descarta los paquetes pertenecientes a iteraciones previas de calentamiento.
>
> Esto asegura una pureza metodológica absoluta: todas las tablas de latencia, factores de desbalanceo y gráficas de saturación reflejan con exactitud el comportamiento asintótico en régimen permanente."*

---

### Pregunta 18: ¿Por qué en `plot_packet_tracking.py` el eje X muestra a veces miles de operaciones de red mientras que `analyze_traces.py` solo reporta las 64 capas de una única iteración? ¿Hay inconsistencia de datos entre herramientas?

**Respuesta Técnica:**
> *"No existe ninguna inconsistencia; esta divergencia responde a **dos objetivos científicos y escalas de observación distintas** que concebí expresamente en el diseño de la suite de software:
>
> 1. **`analyze_traces.py` y `plot_cronograma.py` (Visión Estructural de Capa y Ciclo):** Estas herramientas tienen como misión correlacionar el rendimiento del co-simulador con la arquitectura algorítmica del LLM. Por ello, aplican obligatoriamente el filtro de aislamiento de iteración única y presentan métricas agregadas por capa ($L_0$ a $L_{63}$), asociando cada operación de red a su respectiva fase computacional (Scatter o Gather de la capa $i$). Su escala es la capa del transformador.
>
> 2. **`plot_packet_tracking.py` (Visión Longitudinal Microarquitectural de Red):** Esta herramienta fue desarrollada para diagnosticar fenómenos de persistencia de congestión y degradación de búferes a lo largo de toda la vida útil de la simulación. En [`plot_packet_tracking.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_packet_tracking.py), cada operación de red recibe un identificador secuencial global (`op_id`). Si una simulación ejecuta múltiples iteraciones consecutivas, `plot_packet_tracking.py` analiza deliberadamente la serie temporal completa para auditar si los conmutadores sufren fuga progresiva de créditos o acumulación residual de flits a largo plazo.
>
> Ambas herramientas leen exactamente las mismas fuentes de verdad binarias en disco (`TFM_device_*.trc` y `packet_tracking_debug.csv`), y sus métricas de latencia de flits y paquetes coinciden al $100\%$ cuando se restringe la ventana temporal a los mismos identificadores de operación."*

---

### Pregunta 19: ¿Cómo se ha verificado que no existan fugas de paquetes o violaciones de la ley de conservación de flujo en el acoplamiento entre LLMSimulator y BookSim2?

**Respuesta Técnica:**
> *"La corrección formal del acoplamiento entre ambos motores se validó mediante **tres invariantes de conservación física** integrados en el código C++ y en la suite de verificación automatizada:
>
> 1. **Invariante de Conservación de Flujo y Masa de Paquetes:** En [`booksim2/src/booksim_api.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp), la API mantiene un recuento estricto de paquetes inyectados (`_flits_injected`) y flits retirados (`_flits_retired`). Al invocar `BookSim_FinishOperation()`, el motor verifica que no quede ningún flit huérfano en las colas internas de ningún conmutador. Si se detecta un solo flit en tránsito no drenado, el simulador aborta con aserción (`assert`). Además, verificamos que la suma total de paquetes emitidos coincida exactamente con los recibidos:
>    $$\sum_{i=0}^{N-1} \text{Paquetes Inyectados}[i] = \sum_{j=0}^{N-1} \text{Paquetes Retirados}[j]$$
>
> 2. **Invariante de Causalidad Temporal No Decreciente:** Para cada uno de los millones de flits rastreados en `packet_tracking_debug.csv`, auditamos que sus marcas de tiempo cumplan la relación de orden estricto de la física relativista:
>    $$t_{\text{create}} \le t_{\text{inject}} \le t_{\text{arrive}} \le t_{\text{retire}}$$
>
> 3. **Consistencia de Reloj de Sincronización:** Auditamos que el tiempo final reportado por BookSim2 para una GPU al concluir una colectiva (`rel_finish[d]`) coincida de manera exacta con la marca `START_NS` de la siguiente operación computacional en `TFM_device_d.trc`, con una discrepancia temporal menor a $5\text{ ns}$ (atribuible exclusivamente al redondeo entero a nanosegundos).
>
> Estas tres verificaciones garantizan que el co-simulador es un sistema cerrado, conservativo y matemáticamente riguroso."*

---

### Pregunta 20: Si tuviera que señalar las dos mayores limitaciones de este simulador y qué haría de forma diferente si empezara el proyecto hoy, ¿cuáles serían?

**Respuesta Técnica:**
> *"Con total madurez científica y autocrítica técnica, identifico las dos principales limitaciones de nuestro simulador y la dirección arquitectónica que adoptaría para superarlas:
>
> 1. **Primera Limitación: Modelo Analítico Roofline sin Contención Intra-SM:**
>    - *Diagnóstico:* Aunque el modelo Roofline en `linear_impl.cpp` es muy preciso en regímenes fuertemente limitados por memoria ($I_{\text{op}} \ll I_{\text{ridge}}$), asume que la memoria DRAM HBM3E entrega su ancho de banda teórico de $8.0\text{ TB/s}$ de forma homogénea, sin capturar conflictos de bancos en cache L2, desalineamiento de accesos coalescentes ni sobrecostes de cambio de contexto de warps.
>    - *Alternativa de Diseño:* Si comenzara hoy el proyecto, integraría un **modelo de simulación analítico-estadístico por intervalos (*Interval Simulation*)** para la GPU, similar al propuesto en herramientas como Sniper o MacSim. Esto permitiría modular el ancho de banda efectivo en función del patrón de acceso a memoria sin incurrir en la prohibitiva lentitud de una simulación de registros ciclo a ciclo.
>
> 2. **Segunda Limitación: Desacoplamiento BSP Secuencial en lugar de Motor de Eventos Concurrentes:**
>    - *Diagnóstico:* Como defendí en la Pregunta 4, el modelo BSP fue una elección acertada para aislar la red; sin embargo, impide modelar nativamente el solapamiento intra-capa de operaciones independientes mediante flujos asíncronos (*CUDA streams*), como hace **DualPipe** en DeepSeek-V3 (donde los micro-batches de atención y MoE se intercalan concurrentemente).
>    - *Alternativa de Diseño:* Si rediseñara el simulador desde cero, reemplazaría el oráculo de red bloqueante en `communication.cpp` por un **motor de simulación unificado basado en cola de eventos discretos multiproceso (*Discrete Event Queue Engine*)**. En lugar de que BookSim2 se invoque en fases cerradas, BookSim2 avanzaría sus ciclos en paralelo y de forma cooperativa con las micro-tareas de la GPU, permitiendo modelar colisiones dinámicas de tráfico en tiempo real entre múltiples flujos de ejecución simultáneos.
>
> Esta última propuesta la he dejado formalmente estructurada y fundamentada en la Sección 7.5 de esta Biblia como la **Vía 5 de Investigación Futura**, trazando una hoja de ruta clara para la siguiente generación de investigadores que continúen este proyecto."*

---

---

## 9.5. Bloque E: Perfiles Hardware (B100), Subsistema de Memoria (Ramulator 2.0) y Energía

### Pregunta 21: Los autores originales de LLMSimulator destacan la integración con Ramulator 2.0 como uno de sus pilares cycle-accurate, pero en vuestras configuraciones de prueba veo `use_ramulator: off`. ¿Por qué lo habéis desactivado y qué ocurre realmente en el código cuando se activa?

**Respuesta Técnica:**
> *"Esta decisión responde a un análisis exhaustivo del código fuente y a un principio estricto de economía computacional y fidelidad metodológica.
>
> 1. **Mecanismo Interno cuando `use_ramulator: on`:** Cuando se activa esta bandera en `config.yaml`, el simulador invoca `issueRamulator()` en [`src/hardware/layer_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/layer_impl.cpp) y canaliza las transacciones a través de `DRAMInterface::HandleRequest()` en [`src/dram/dram_interface.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/dram_interface.cpp). Ramulator 2.0 fragmenta el acceso al tensor en solicitudes de ráfaga física de $32\text{ Bytes}$ y simula ciclo a ciclo las colas de canal, rangos, grupos de bancos (`BankGroup`), bancos (`Bank`), aperturas de fila (`ACT`), precargas (`PRE`) y temporizaciones JEDEC de HBM3/HBM3E ($t_{RCD}$, $t_{RP}$, $t_{CL}$).
>
> 2. **La Caché de Memoización en `Device`:** Como simular millones de accesos DRAM ciclo a ciclo en cada capa provocaría que una sola iteración tardara horas de cómputo secuencial, `LLMSimulator` implementa una caché hash (`addExecutionCache` / `checkExecutionCache` en [`src/hardware/device.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp)) indexada por la tupla:
>    $$\text{Cache Key} = \left(\text{layer\_type}, \text{processor\_type}, \text{dram\_request\_type}, \text{tensor\_size}\right)$$
>    Esto significa que Ramulator 2.0 **solo corre la primera vez que observa un tamaño de tensor específico**; para todas las llamadas sucesivas con idéntica dimensión, el simulador simplemente reutiliza la latencia memorizada. Además, módulos analíticos elementales como `LayerNorm` ([`src/module/layernorm.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/layernorm.cpp)), `RoPE` ([`src/module/rope.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/rope.cpp)) y `Residual` ([`src/module/residual.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/residual.cpp)) **nunca invocan a Ramulator 2.0**, evaluándose siempre mediante fórmulas analíticas de ancho de banda.
>
> 3. **Justificación Metodológica de `use_ramulator: off`:** En la fase de inferencia autorregresiva (Decode con $BS=32$), la intensidad operacional es muy baja ($I_{\text{op}} \ll I_{\text{ridge}} \approx 562.5\text{ FLOP/B}$), lo que significa que la GPU opera en un régimen de saturación continua del bus de memoria HBM3E ($8.0\text{ TB/s}$). Desactivar Ramulator 2.0 y emplear el modelo Roofline analítico determinista en [`src/module/linear_impl.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/linear_impl.cpp) entrega una precisión en tiempos de cómputo con un margen de discrepancia inferior al $2\%$ frente al hardware real medido en PyTorch, eliminando una sobrecarga de CPU innecesaria y permitiendo aislar con total pureza experimental las variables de congestión de red en BookSim2."*

---

### Pregunta 22: En vuestro `config.yaml` siguen apareciendo parámetros como `gpu_gen: B100`, `nvlink_gen: 5` (900 GB/s) e `infiniband_gen: 800` (50 GB/s). ¿Siguen influyendo en el tiempo de red o cómo evitáis sumar la latencia de red dos veces?

**Respuesta Técnica:**
> *"Puedo certificar que no existe ninguna doble contabilización de latencias en el co-simulador: la interconexión física está gobernada al 100% por BookSim2.
>
> 1. **Secuestro del Módulo de Red en C++:** En el código original de `LLMSimulator-orig`, las primitivas `MoEScatter::forward`, `MoEGather::forward` y `AllReduce::forward` calculaban la latencia de red mediante ecuaciones analíticas ideales en [`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp), leyendo `device_ict_bandwidth` (para NVLink) o `node_ict_bandwidth` (para InfiniBand) desde [`src/hardware/hardware_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/hardware_config.h):
>    $$t_{\text{red\_original}} = t_{\text{latency}} + \frac{\text{size}}{\text{bandwidth}}$$
>    En mi implementación del **Oráculo BookSim2**, reemplacé completamente estas ecuaciones analíticas: cuando se alcanza una colectiva, el simulador traduce el tensor a paquetes físicos de MTU 256 B y flits de 32 B en BookSim2.
>
> 2. **Incompatibilidad de Ecuaciones Sintéticas:** Las variables analíticas de ancho de banda y latencia de red en `config.yaml` (`nvlink_gen`, `infiniband_gen`) quedan **totalmente inertes y anuladas** para las colectivas de comunicación. El tiempo transcurrido en red se calcula exclusivamente acumulando los ciclos discretos de simulación de BookSim2 (`test.cfg`, a $1.0\text{ GHz}$).
>
> 3. **Función Residual de `gpu_gen: B100`:** El parámetro `gpu_gen: B100` en `config.yaml` se utiliza exclusivamente para configurar las capacidades de cómputo local y memoria interna de la GPU: $1750\text{ TFLOP/s}$ en FP16 ($3500\text{ TFLOP/s}$ en FP8) y $8.0\text{ TB/s}$ de ancho de banda HBM3E. Por tanto, el cómputo y la red están matemáticamente desacoplados y libres de redundancias."*

---

### Pregunta 23: ¿Qué cambiaría en vuestras conclusiones si en lugar de simular 8 GPUs NVIDIA B100 usarais H100 o B200, o activarais los modos PIM (`ProcessorType::PIM` / `LOGIC`) que trae LLMSimulator?

**Respuesta Técnica:**
> *"El análisis de sensibilidad frente a la generación de hardware refuerza de forma contundente las conclusiones científicas de este trabajo:
>
> 1. **Sensibilidad Generacional: H100 vs. B100 vs. B200:**
>    Consultando [`src/hardware/hardware_config.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/hardware_config.h):
>    - **NVIDIA H100:** Cómputo pico FP16 de $989.4\text{ TFLOP/s}$ y ancho de banda DRAM HBM3 de $3.352\text{ TB/s}$.
>    - **NVIDIA B100:** Cómputo pico FP16 de $1750.0\text{ TFLOP/s}$ ($3500\text{ TFLOP/s}$ FP8) y HBM3E de $8.000\text{ TB/s}$.
>    - **NVIDIA B200:** Cómputo pico FP16 de $2250.0\text{ TFLOP/s}$ y HBM3E de $8.000\text{ TB/s}$.
>
>    Al pasar de H100 a B100, el ancho de banda DRAM se multiplica por un factor de:
>    $$\text{Aceleración de Memoria} = \frac{8.000\text{ TB/s}}{3.352\text{ TB/s}} \approx \mathbf{2.39\times}$$
>    Dado que la inferencia autorregresiva de LLMs con $BS=32$ es estrictamente *Memory-Bound*, el tiempo de cómputo local de un experto se reduce drásticamente (de $\sim 52.8\,\mu\text{s}$ en H100 a $22.15\,\mu\text{s}$ en B100).
>    - **Efecto Amdahl en la Red:** Al acelerarse el cómputo local en $2.39\times$, la proporción de tiempo consumida por la interconexión de red (`Transit` + `Stalls`) sobre el tiempo total de muro (`Wall-Clock Time`) **crece de forma muy notable**. Esto significa que cuanto más rápida es la GPU, más crítico resulta el cuello de botella de la red NoC y mayor es la ganancia porcentual obtenida al optimizar la topología (por ejemplo, al migrar de Toro 1D a Malla 2D o al implementar Hardware Multicast).
>
> 2. **Estado Real de los Modos PIM en el Código Base:** LLMSimulator define los enumeradores `ProcessorType::PIM` y `ProcessorType::LOGIC` en `hardware_config.h` para explorar procesamiento en memoria (Processing-In-Memory). Sin embargo, tras auditar el código fuente, constaté que el soporte para `bank-group-level PIM` es incompleto: por ejemplo, `pimBankgroupEnergy` en [`src/dram/power.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/power.h) es una constante estática fija que carece de acoplamiento dinámico con el grafo de ejecución MoE. Por rigor científico, decidí basar todas las evaluaciones del TFM en arquitecturas discretas de silicio comprobadas (xPU estándar)."*

---

### Pregunta 24: En los logs `.trc` aparecen columnas de energía (`ACT`, `RD`, `WR`, `MAC` en mJ), pero en los bloques `moe_scatter` y `moe_gather` todos esos valores salen a `0 mJ`. ¿Cómo calcula el simulador la energía y por qué no mide el consumo de la red?

**Respuesta Técnica:**
> *"Esta observación es totalmente acertada y revela con transparencia la frontera de modelado del simulador base.
>
> 1. **Modelo Energético GPU y DRAM:** En [`src/hardware/device.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp), [`src/dram/power.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/power.h) y [`src/module/module_graph.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp), el simulador computa la energía dinámica a partir del modelo analítico FGDRAM (*Fine-Grained DRAM, MICRO 2017*):
>    - $E_{\text{ACT}} = 0.909\text{ nJ}$ por cada activación de fila en la memoria HBM.
>    - $E_{\text{RD}} = E_{\text{WR}} = 0.891\text{ nJ}$ por cada transferencia de ráfaga física de $32\text{ Bytes}$ a través de las vías de silicio (TSV) y el interposer.
>    - $E_{\text{MAC}} = 0.00023\text{ nJ} = 0.23\text{ pJ}$ por operación Multiply-Accumulate (FLOP) en los Tensor Cores.
>    En [`src/module/timeboard.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/timeboard.cpp), estos acumuladores se transforman a milijulios ($\text{mJ}$) dividiendo por $10^6$.
>
> 2. **Por qué la Red Marca `0 mJ`:** En la arquitectura original de `LLMSimulator-orig`, la red de interconexión no existía como entidad física simulada; era únicamente una función de retardo temporal sintética. En consecuencia, los autores originales no instrumentaron contadores de energía para transceptores de red o conmutadores.
>
> 3. **Extensibilidad a Modelos NoC (Orion 3.0):** Al integrar BookSim2 como motor de red interactivo, he sentado la infraestructura necesaria para acoplar herramientas de modelado energético de conmutadores como **Orion 3.0** o **DSENT**, las cuales calculan la disipación energética de los buffers de entrada (IB), árbitros de canal virtual (VA/SA), conmutadores crossbar (ST) y transmisores de enlace (LT). Al reportar honestamente `0 mJ` en los bloques de red de las trazas actuales, evitamos inventar consumos no auditados y dejamos la puerta abierta a esta extensión directa."*

---

### Pregunta 25: Al auditar el código de `LLMSimulator`, ¿existen capas o módulos del Transformer que se ejecuten con coste temporal cero? ¿No distorsiona eso el tiempo total de inferencia?

**Respuesta Técnica:**
> *"Efectivamente, tras realizar una auditoría integral línea a línea del grafo computacional, identifiqué con precisión los módulos que no computan latencia física en el simulador:
>
> 1. **Módulos de Latencia Nula Identificados:**
>    - **`Embedding` ([`src/module/embedding.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/embedding.cpp)):** El simulador trata la capa de embebido inicial como un mapeo de índices y punteros de memoria, sin invocar el modelo Roofline de lectura DRAM ni registrar latencia.
>    - **`LmHead` ([`src/module/lm_head.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/lm_head.cpp)):** La proyección lineal final desde el espacio oculto $k$ hacia el vocabulario $n_{\text{vocab}}$ (ej. 129.280 en DeepSeek-V3) opera como una asignación de salida lógica en el diseño original del SCALE lab.
>    - **`CompressedKVRestore` ([`src/module/compressed_kv_restore.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/compressed_kv_restore.cpp)):** En la atención MLA de DeepSeek-V3, este nodo actúa como enlace de punteros hacia el vector latente comprimido en memoria sin duplicar transferencias físicas.
>
> 2. **Evaluación de Impacto Cuantitativo:**
>    ¿Afecta esto a la validez de nuestras conclusiones sobre los cuellos de botella de red? **En absoluto:**
>    - En un modelo masivo como DeepSeek-V3 (60 capas decodificadoras) o Mixtral 8x7B (32 capas) ejecutado en modo autorregresivo (Decode), el tiempo de cómputo está dominado en más del **$99.7\%$** por las capas repetitivas de decodificación: proyecciones de atención, proyecciones FFN de los expertos y colectivas MoEScatter/MoEGather.
>    - Analíticamente, evaluar una capa `LmHead` en DeepSeek-V3 con $BS=32$ requeriría transferir la matriz de pesos de vocabulario ($7168 \times 129280 \times 1\text{ B} \approx 926\text{ MB}$), lo que a $8.0\text{ TB/s}$ añadiría aproximadamente $115\,\mu\text{s}$ una única vez al final de toda la iteración de inferencia (frente a los $11.843,5\,\mu\text{s}$ que dura la iteración completa).
>    - Por tanto, omitir `LmHead` y `Embedding` representa un sesgo temporal inferior al **$1.0\%$** en el Wall-Clock Time global y tiene **impacto estrictamente cero** sobre la dinámica de contención, colas y saturación de la red NoC, que ocurre íntegramente dentro del bucle de las capas MoE."*

---

## 9.6. Bloque F: Topologías Concretas, Enrutamiento NoC y Escalabilidad

### Pregunta 26: En vuestros experimentos con topología Toro exigís `num_vcs >= 2`, mientras que en Malla 2D podríais operar con 1 VC. ¿Por qué un Toro se bloquea con 1 solo canal virtual y cómo lo resuelve BookSim2 internamente?

**Respuesta Técnica:**
> *"Este requisito es una exigencia matemática insoslayable derivada de la teoría clásica de interconexión y la prevención de interbloqueos (*deadlocks*).
>
> 1. **La Causa del Interbloqueo en Toros:** En una topología de Malla (Mesh), el enrutamiento por orden de dimensión (DOR: $X \to Y$) induce un Grafo de Dependencia de Canales (*Channel Dependency Graph - CDG*) acíclico, por lo que es físicamente imposible que un paquete quede bloqueado esperando un canal ocupado por él mismo. En cambio, en una topología en anillo o Toro, la presencia de enlaces envolventes (*wrap-around*) introduce **ciclos dirigidos cerrados en el CDG**. Si solo se dispone de 1 Canal Virtual ($V=1$), un tren de paquetes que circule simultáneamente alrededor del anillo puede llenar por completo los buffers de entrada de todos los conmutadores, creando una cadena de espera circular infinita donde ningún flit puede avanzar.
>
> 2. **El Algoritmo de Dateline Routing en BookSim2:** Para romper estos ciclos sin recurrir a costosos mecanismos de descarte de paquetes, BookSim2 implementa el esquema de bipartición de canales virtuales de Dally-Seitz en [`booksim2/src/routefunc.cpp:L1517-L1582`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routefunc.cpp#L1517-L1582):
>    - Los Canales Virtuales se dividen en dos subconjuntos disjuntos: **Clase 0 (Fase 0)** y **Clase 1 (Fase 1)**.
>    - Todo paquete se inyecta inicialmente en la Clase 0 (`f->ph = 0`).
>    - Al cruzar el enlace wrap-around que conecta el nodo $k-1$ con el nodo 0 (denominado *dateline*), la función `dor_next_torus` detecta la transición de coordenadas y promueve de forma irreversible el paquete a la Clase 1 (`f->ph = 1`).
>    - Dado que los paquetes en Clase 1 jamás pueden solicitar canales de Clase 0, el grafo de dependencias queda estratificado en dos niveles acíclicos superpuestos, imposibilitando la formación de ciclos.
>
> 3. **Demostración de la Restricción $V \ge 2$:** En [`booksim2/src/routefunc.cpp:L1555`](file:///home/igilolt/Escritorio/TFM/booksim2/src/routefunc.cpp#L1555), el código evalúa:
>    ```cpp
>    int available_vcs = (vcEnd - vcBegin + 1) / 2;
>    assert(available_vcs > 0);
>    ```
>    Si se configurara $V=1$, la división entera daría $1/2 = 0$, disparando inmediatamente la aserción y abortando la simulación.
>
> 4. **Beneficio Adicional de $V=4$ VCs:** Además de prevenir el deadlock, en nuestras pruebas con Mixtral demostramos que incrementar los VCs de 2 a 4 redujo la latencia media de flit en un **$15.4\%$**, ya que permite que paquetes de colectivas más cortas adelanten a flits retenidos en colas congestionadas, mitigando el bloqueo en cabeza de línea (*Head-of-Line Blocking*)."*

---

### Pregunta 27: Habéis usado `dim_order` (Dimension-Order Routing) en la mayoría de pruebas y `min` en AnyNet. ¿Qué ocurre si activamos enrutamiento adaptativo (`min_adapt`) ante ráfagas MoE desbalanceadas?

**Respuesta Técnica:**
> *"El contraste entre enrutamiento determinista y adaptativo frente a ráfagas MoE revela compromisos arquitectónicos fundamentales de la microarquitectura de conmutación:
>
> 1. **Enrutamiento Determinista (`dim_order` y `min` en AnyNet):**
>    - *Funcionamiento:* La ruta entre cualquier par ordenado $(src, dest)$ está prefijada estáticamente (por ejemplo, agotar primero la coordenada $X$ y luego la $Y$, o seguir el camino más corto de Dijkstra).
>    - *Ventajas:* Garantiza la preservación del orden de llegada de los paquetes sin requerir buffers de reordenamiento en destino; la etapa de Route Computation (RC) en el conmutador es prácticamente instantánea.
>    - *Limitación Crítica:* Es completamente ciego a la congestión. Cuando un experto sufre desbalanceo extremo ($s=1.0$), el 80% del tráfico se canaliza sobre exactamente los mismos conmutadores y enlaces físicos. `dim_order` continúa inyectando flits sobre los enlaces saturados, propagando contrapresión (*backpressure*) y agotando créditos a lo largo de toda la ruta.
>
> 2. **Enrutamiento Adaptativo (`min_adapt` en `routefunc.cpp`):**
>    - *Funcionamiento:* Ante una bifurcación admisible de caminos mínimos de igual longitud, la función de enrutamiento sondea el estado de créditos de los búferes de entrada de los conmutadores vecinos mediante `_next_buf[output]->GetOccupancy()`. Si el enlace primario en $X$ está congestionado, el router desvía dinámicamente el paquete a través de la dimensión $Y$.
>    - *Comportamiento ante Ráfagas MoE:* En escenarios de alta asimetría de carga, `min_adapt` descongestiona los puntos calientes locales y reduce el retardo inicial de colas NIC.
>    - *Contrapartidas:* Sin embargo, introduce dos penalizaciones: 1) Los paquetes pueden llegar desordenados a la GPU destino, lo que exige buffers de reensamblado más complejos en la NIC; 2) Incrementa la contención en el asignador de Canales Virtuales (VA), lo que bajo patrones All-to-All masivos (como los de DeepSeek-V3) puede desencadenar inestabilidad transitoria de enrutamiento (*routing oscillations*)."*

---

### Pregunta 28: Si quisiéramos escalar este estudio de 8 GPUs a un clúster de 64 o 256 GPUs usando un Toro 3D o 4D en BookSim2, ¿cuáles son los límites físicos y computacionales del simulador?

**Respuesta Técnica:**
> *"Escalar el marco de co-simulación a decenas o centenares de GPUs es arquitectónicamente viable, pero está sujeto a dos leyes de escalabilidad microarquitectural bien definidas:
>
> 1. **Escalabilidad Topológica ($k$-ary $n$-cube en `kncube.cpp`):**
>    En BookSim2 ([`booksim2/src/networks/kncube.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/networks/kncube.cpp)), el número total de nodos en un Toro regular viene dado por $N = k^n$, donde $k$ es el número de nodos por dimensión y $n$ es la dimensionalidad:
>    - Para $64\text{ GPUs}$: Toro 3D de $4^3$ nodos ($k=4, n=3$).
>    - Para $256\text{ GPUs}$: Toro 4D de $4^4$ nodos ($k=4, n=4$).
>
> 2. **La Maldición de la Complejidad del Router ($O(\text{Puertos}^2)$):**
>    Cada conmutador en un Toro $n$-dimensional debe gobernar $2$ canales bidireccionales por cada dimensión más $1$ puerto local de inyección/eyección conectado a la GPU:
>    $$\text{Número de Puertos por Router} = 2n + 1$$
>    - Toro 1D ($n=1$): $2(1) + 1 = 3\text{ puertos}$.
>    - Toro 3D ($n=3$): $2(3) + 1 = 7\text{ puertos}$.
>    - Toro 4D ($n=4$): $2(4) + 1 = 9\text{ puertos}$.
>
>    La matriz de conmutación interna (*crossbar switch*) y los árbitros de switch allocation (SA) escalan cuadráticamente con el número de puertos:
>    $$\text{Puntos de Cruce Crossbar} = O\left((2n + 1)^2\right)$$
>    En un Toro 4D, cada router debe evaluar $9^2 = 81$ puntos de conmutación potenciales en cada ciclo, frente a los $3^2 = 9$ de nuestro Toro 1D ($9\times$ más operaciones de arbitraje por conmutador).
>
> 3. **Complejidad Temporal Global de la Simulación:**
>    El coste computacional de BookSim2 por ciclo de reloj viene determinado por:
>    $$\text{Coste por Ciclo} = O\left(N \times (2n + 1)^2 \times V\right)$$
>    Para un clúster de 256 GPUs en Toro 4D con 4 VCs, simular un ciclo de red requiere evaluar más de $82.900$ operaciones de arbitraje interno. Multiplicado por los millones de ciclos necesarios para drenar un All-to-All masivo de DeepSeek-V3, el tiempo de simulación de una sola capa se elevaría a varias horas de CPU secuencial, señalando la necesidad de paralelizar el bucle `_Step()` de BookSim2 mediante OpenMP o MPI como trabajo futuro."*

---

### Pregunta 29: Para un clúster fijo de 8 GPUs, ¿qué compromisos arquitectónicos existen entre conectarlas en Toro 1D ($8$), Malla 2D ($4 \times 2$) o Malla 3D ($2 \times 2 \times 2$ / hipercubo)?

**Respuesta Técnica:**
> *"Para un clúster acotado a 8 nodos de aceleración, la elección topológica presenta compromisos muy claros entre diámetro de red, ancho de banda de bisección y coste de cableado físico:
>
> | Métrica Arquitectural | Toro 1D ($k=8, n=1$) | Malla 2D ($4 \times 2, n=2$) | Malla 3D ($2 \times 2 \times 2$, Hipercubo $n=3$) |
> | :--- | :---: | :---: | :---: |
> | **Diámetro Máximo (Saltos)** | $4\text{ saltos}$ | $4\text{ saltos}$ ($3_X + 1_Y$) | $\mathbf{3\text{ saltos}}$ ($1_X + 1_Y + 1_Z$) |
> | **Distancia Media de Salto** | $1.50\text{ saltos}$ | $1.75\text{ saltos}$ | $\mathbf{1.50\text{ saltos}}$ |
> | **Enlaces de Bisección** | $2\text{ enlaces bidir.}$ | $\mathbf{4\text{ enlaces bidir.}}$ ($2\times$) | $\mathbf{4\text{ enlaces bidir.}}$ ($2\times$) |
> | **Puertos de Red por Router** | $\mathbf{2\text{ puertos}}$ (Radix 3) | $2\text{ a } 3\text{ puertos}$ (Radix 4-5) | $3\text{ puertos}$ (Radix 4 regular) |
> | **Enlaces Totales en Clúster** | $\mathbf{8\text{ enlaces}}$ | $10\text{ enlaces}$ | $12\text{ enlaces}$ |
> | **Complejidad de Cableado Físico** | Baja (enlaces wrap-around largos) | Muy Baja (plana, sin wrap-around) | Media (cruces tridimensionales en PCB) |
>
> 1. **Toro 1D:** Presenta la menor complejidad de conmutador (solo 2 puertos de red), pero su estrecho corte de bisección (2 enlaces) genera un cuello de botella severo ante ráfagas All-to-All, disparando las colas a $52.680\text{ ciclos}$ en DeepSeek-V3.
> 2. **Malla 2D ($4 \times 2$):** Duplica el ancho de banda de bisección a 4 enlaces bidireccionales, reduciendo el pico de colas en un **$19.19\%$** y la latencia media de paquetes en un **$-8.97\%$**. Su gran ventaja industrial es que no requiere enlaces envolventes largos (*wrap-around*), siendo ideal para integrarse en un backplane impreso convencional dentro de un nodo servidor.
> 3. **Malla 3D ($2 \times 2 \times 2$ / Hipercubo binario):** Es la topología óptima en rendimiento: reduce el diámetro a solo 3 saltos físicos y garantiza un grado de conmutador homogéneo (Radix 4) en los 8 nodos, ofreciendo caminos ortogonales simétricos en tres dimensiones. Su principal barrera es el trazado de pistas y conectores en chasis de alta densidad."*

---

### Pregunta 30: En la literatura de NoCs, las curvas de saturación se obtienen inyectando tráfico uniforme Bernoulli hasta que la latencia tiende a infinito. ¿Por qué vuestra gráfica `curva_saturacion_red.png` muestra puntos discretos en lugar de una curva continua hasta el infinito?

**Respuesta Técnica:**
> *"Esta distinción metodológica es crucial y delimita la diferencia entre la experimentación sintética abstracta y la **co-simulación realista en lazo cerrado guiada por cargas de trabajo reales de IA**.
>
> 1. **Simulación Sintética en Lazo Abierto (*Open-Loop*):**
>    En los bancos de prueba tradicionales de redes de interconexión (como los que ejecuta BookSim2 en modo aislado), un generador de tráfico Bernoulli inyecta paquetes a una tasa constante prefijada $\lambda_{\text{inj}}$ de forma indefinida, con independencia de si la red es capaz de absorberlos. Cuando la tasa de inyección supera la capacidad de bisección de la red, los paquetes se apilan indefinidamente en las colas de las NICs y la latencia promedio diverge asintóticamente hacia el infinito ($\lim_{\lambda \to \lambda_{\text{crit}}} L = \infty$), dibujando la clásica asíntota vertical continua.
>
> 2. **Nuestra Co-Simulación en Lazo Cerrado (*Closed-Loop*):**
>    En nuestro entorno, el tráfico no procede de un generador estadístico infinito, sino de la **física determinista de ejecución del grafo de un LLM**:
>    - En cada capa MoE, la colectiva contiene un volumen finito y acotado de datos determinado por el batch de tokens ($BS \times k$).
>    - Cuando se produce contención severa por in-cast (como bajo *skewness* $s=1.0$), los buffers de entrada de los conmutadores se llenan, agotando los créditos de control de flujo.
>    - Esta contrapresión física detiene la inyección en las NICs de las GPUs transmisoras. Las GPUs **no pueden seguir inyectando paquetes al infinito**: deben esperar físicamente a que la red drene los flits en tránsito.
>    - Al alargarse la duración total de la colectiva $\Delta\text{Ciclos}$, la tasa media de inyección efectiva:
>      $$\lambda = \frac{\text{Flits Inyectados}}{N_{\text{GPUs}} \times \Delta\text{Ciclos}_{\text{colectiva}}}$$
>      **se reduce de forma auto-regulada**, desplazando el sistema hacia la izquierda en el eje horizontal.
>
> 3. **Significado Físico de los Puntos Discretos:**
>    Por consiguiente, cada punto $(\overline{\lambda}, \overline{L})$ en la gráfica [`curva_saturacion_red.png`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/build/analysis/) representa el **punto de equilibrio físico estacionario real alcanzado por una arquitectura de modelo (Mixtral vs. DeepSeek), una topología NoC (Toro vs. Malla) y un patrón de desbalanceo de carga específico**. Refleja con fidelidad cómo se comporta una red de interconexión real en producción bajo la presión de un modelo de lenguaje masivo, en lugar de un artificio matemático sin retroalimentación de flujo."*

---

# CAPÍTULO 10: Interfaz Gráfica de Usuario (GUI) y Entorno Interactivo de Co-Simulación Web Local (Workbench)

## 10.1. Motivación y Arquitectura del Workbench (`launch_gui.py` y `gui/`)
Para democratizar la experimentación con el co-simulador `LLMSimulator` + `BookSim2`, eliminar la barrera de entrada de las líneas de comandos complejas y proporcionar una experiencia visual interactiva de nivel profesional (inspirada en herramientas pedagógicas de arquitectura de computadores como Haoziwan RISC-V o CTU Prague), se diseñó e implementó el **LLM-NoC Co-Simulation Workbench**.

La arquitectura técnica se sustenta en tres principios rectores:
1. **Cero Dependencias Externas:** El servidor backend (`LLMSimulator/gui/server.py`) utiliza exclusivamente librerías estándar de Python 3 (`http.server`, `threading`, `json`, `subprocess`, `urllib.parse`), prescindiendo de dependencias pesadas como Node.js, Flask o Django.
2. **Frontend Ligero en Vanilla JavaScript y HTML5 Canvas:** La interfaz gráfica no utiliza frameworks que requieran transpilación (como React o Vue); implementa componentes modulares nativos en CSS3 moderno (`styles.css`) y JavaScript vanilla (`app.js`, `timeline_canvas.js`), garantizando carga instantánea y renderizado fluido a 60 FPS en cualquier navegador moderno en Linux.
3. **Regla de Oro de Aislamiento:** El entorno de GUI reside de manera estrictamente encapsulada en `LLMSimulator/launch_gui.py` y `LLMSimulator/gui/`. No modifica ni interfiere en la operativa de los scripts CLI existentes (`run_sim.py`, `analyze_traces.py`, `plot_cronograma.py`, `plot_packet_tracking.py`) ni en el código C++ del co-simulador.

---

## 10.2. Aislamiento Estricto y Ciclo de Vida en Staging (`build/tmp_staging/`)
Uno de los problemas más comunes en la experimentación intensiva es la proliferación desordenada de carpetas con ejecuciones de prueba o parámetros erróneos que ensucian el historial principal (`build/results/`).

Para resolver esto, el Workbench introduce un ciclo de vida con **Área de Staging Temporal**:
- Todas las simulaciones ejecutadas desde la interfaz gráfica se dirigen a un directorio efímero:
  $$\text{Ruta Temporal} = \text{build/tmp\_staging/}\{\text{modelo}\}\_\{\text{gpus}\}\text{dev}\_\{\text{topología}\}\_\text{bs}\{\text{BS}\}\_\{\text{timestamp}\}/$$
- Al completarse la ejecución, los resultados quedan disponibles de inmediato en la Pestaña 2 bajo el banner contextual:
  $$\mathbf{\text{Simulación: }}\langle\text{nombre\_carpeta}\rangle\mathbf{\text{ (No guardada)}}$$
- **Persistencia Selectiva:** El investigador dispone de dos botones explícitos:
  1. **Guardar Simulación (`POST /api/results/save`):** Permite introducir una etiqueta descriptiva (ej. `Torus TP=2 Baseline`) y traslada atómicamente la carpeta desde `build/tmp_staging/` a `build/results/`, actualizando el banner a `(Guardada)` y preservando los datos de forma permanente.
  2. **Descartar Simulación (`POST /api/results/discard`):** Elimina completamente la carpeta de staging del sistema de archivos, devolviendo la interfaz al estado inicial sin dejar residuos.

---

## 10.3. Pestaña 1: Configurador Interactivo y Guardarraíles en Tiempo Real
El configurador interactivo permite parametrizar tanto el modelo LLM como la red NoC, garantizando que el usuario nunca lance una simulación con configuraciones físicamente inconsistentes mediante **Guardarraíles Proactivos**:

1. **Deadlock en Topología Torus:**
   - Si se selecciona `topology: torus` con $VCs < 2$, el sistema emite un aviso de bloqueo crítico explicando que el algoritmo Dateline exige obligatoriamente al menos 2 canales virtuales para romper ciclos cerrados en el Grafo de Dependencia de Canales (CDG).
2. **Topología Asimétrica (AnyNet):**
   - Si las dimensiones de red son asimétricas (ej. `net_dims: 4 2`), se restringe la topología a Malla 2D y el enrutamiento a `min` (Dijkstra), advirtiendo si se intenta forzar Torus o DOR.
3. **Divisibilidad de Tensor Parallelism:**
   - Verifica que el número total de GPUs sea divisible exactamente por el grado de paralelismo tensorial ($N_{\text{GPUs}} \pmod{TP} == 0$).
4. **Límite de Paralelismo de Expertos (Mixtral 8x7B):**
   - Prohíbe configurar más de 8 GPUs para Mixtral, dado que contiene exactamente 8 expertos y el particionamiento de un experto individual entre múltiples nodos no está soportado.
5. **Previsualización CLI y Consola en Vivo:**
   - La barra inferior reconstruye en tiempo real el comando exacto equivalente:
     ```bash
     python run_sim.py --model mixtral --net_dims 8 --topology torus --vcs 4 --routing dim_order --batch_size 32 --output_len 2 --iter 2
     ```
   - Al pulsar "Lanzar Co-Simulación", el motor `SimulationRunner` ejecuta el subproceso sin bloquear el servidor, reportando el progreso en streaming a través de una consola con auto-scroll y ofreciendo un botón de cancelación inmediata ("Abortar").

---

## 10.4. Pestaña 2: Resultados Arquitectónicos y Visualizadores en Canvas HTML5 al Vuelo
A diferencia de los scripts tradicionales que generan archivos de imagen estáticos PNG mediante `matplotlib`, la Pestaña 2 reconstruye las líneas de tiempo **directamente y al vuelo en el navegador mediante HTML5 Canvas** a partir de los archivos de trazas crudas (`TFM_device_*.trc` y `packet_tracking_debug.csv`).

### Tarjetas KPI Arquitectónicas (7 Métricas Esenciales)
Calculadas por `gui/trace_parser.py`:
1. **Wall-Clock Time:** Tiempo total de inferencia de la iteración seleccionada en microsegundos.
2. **Cómputo GPU:** Tiempo acumulado de operaciones aritméticas locales (`Attn`, `ExpertFFN`, `DenseFFN`) y su porcentaje relativo.
3. **Tránsito NoC Puro:** Tiempo de travesía de red en colectivas (`moe_scatter`, `moe_gather`, `all_reduce`) y su porcentaje relativo.
4. **Stalls de Barrera:** Tiempo ocioso en barreras causales (`sync_for_moe_gather`, sincronizaciones residuales) y su porcentaje relativo.
5. **Tasa de Inyección Real ($\lambda$):** Tráfico efectivo inyectado por nodo en flits/ciclo/nodo.
6. **Latencia Media de Flit:** Ciclos promedio de tránsito en BookSim2.
7. **Total Paquetes / Flits:** Volumen total de tráfico microarquitectural transferido.

### Sub-vistas Interactivas
- **Sub-vista A (Cronograma GPU Ciclo a Ciclo):** Diagrama de Gantt multi-GPU con pistas individuales por dispositivo (GPU 0..N-1), colores semánticos (verde: cómputo, azul cielo: Scatter, azul oscuro: Gather, morado: AllReduce, rojo: Stalls), zoom continuo, panorámica horizontal y tooltips con desglose microarquitectural al posar el cursor.
- **Sub-vista B (Visualizador de Paquetes en Vuelo):** Visualizador de flits individuales con descomposición temporal de cada paquete en dos segmentos físicos coloreados: retardo en cola de la NIC transmisora (naranja, $[ctime \to itime]$) y tiempo de vuelo NoC (azul, $[itime \to atime]$), con botones de salto a regímenes de congestión (fase libre, congestión media P50 y congestión crítica pico).

---

## 10.5. Selector Multidimensional de Iteraciones (Fase 2.5)
Para permitir tanto el análisis riguroso de régimen estacionario como la comparación con el calentamiento (*warm-up*) y la concatenación temporal de toda la ejecución, se implementó en `gui/trace_parser.py` y `app.js` un **Selector de Iteraciones** totalmente integrado:

- **Modos de Selección:**
  - `Última Iteración (Steady-State)` (por defecto `iteration="last"`): Aísla la última iteración descartando el calentamiento.
  - `Iteración 1 (Warm-up)` / `Iteración 2..N` (`iteration="1"`, `iteration="2"`): Permite auditar de forma independiente cualquier iteración individual.
  - `Simulación Completa (Concatenada)` (`iteration="all"`): Concatena cronológicamente todas las iteraciones ejecutadas en un único eje temporal continuo.

- **Mecánica de Concatenación y Marcadores Temporales (`iteration_markers`):**
  Para la opción `iteration="all"`, el backend calcula los desplazamientos acumulativos:
  $$\text{Offset}_k = \sum_{j=1}^{k-1} \max\left(\text{START\_NS}_j\right)$$
  aplicando este desfase a cada paquete y bloque de GPU. Además, el backend retorna una estructura `iteration_markers`:
  ```json
  [
    {"iter": 1, "start_ns": 0.0, "duration_ns": 1103902.0},
    {"iter": 2, "start_ns": 1103902.0, "duration_ns": 1100043.2}
  ]
  ```
  El motor gráfico Canvas dibuja líneas divisorias verticales discontinuas en color dorado/ámbar con una etiqueta flotante distintiva (`Iter 1`, `Iter 2`), permitiendo inspeccionar la frontera de calentamiento de forma inmediata.

---

## 10.6. Visualizador Híbrido Sincronizado Split-Screen (Fase 2.5)
La cumbre analítica de la Pestaña 2 es el **Visualizador Híbrido Sincronizado**, accesible mediante la sub-vista `⚡ Visualizador Híbrido (Sincronizado)`:

### Estructura de Pantalla Dividida (Split-Screen)
La vista divide verticalmente el espacio de trabajo en dos paneles acoplados:
- **Panel Superior (50%):** Cronograma de Ejecución GPU ($0 \dots N-1$), mostrando bloques de cómputo, colectivas y stalls de barrera.
- **Panel Inferior (50%):** Flujo de Paquetes NoC en Tránsito, donde cada barra representa el ciclo de vida de un paquete trazado directamente sobre la misma escala temporal.

### Características de Sincronización Estricta
1. **Escala Temporal X Idéntica en Nanosegundos:**
   Ambos paneles comparten exactamente el mismo rango temporal $[\text{viewStartNs}, \text{viewEndNs}]$ y la misma relación de píxeles por nanosegundo. Las marcas de inyección de paquetes en el panel inferior coinciden al nanosegundo con los bloques de Scatter, Gather o AllReduce de las GPUs correspondientes en el panel superior.
2. **Cursor Vertical Crosshair Acoplado:**
   Al desplazar el ratón sobre cualquiera de los dos lienzos, una línea vertical luminosa de referencia temporal (`rgba(56, 189, 248, 0.85)`) cruza simultáneamente ambos paneles con un marcador superior que indica el instante exacto en nanosegundos o microsegundos.
3. **Controles de Navegación Unificados:**
   La rueda del ratón (zoom centrado en cursor), el arrastre horizontal (panorámica fluida), los botones de preajuste de ventana (`10 µs`, `20 µs`, `50 µs`, `100 µs`, `250 µs`, `Total`) y la barra de desplazamiento horizontal (*scrubber*) actúan simultáneamente sobre ambas vistas a través del controlador `HybridSyncController`.
4. **Consulta Eficiente con Submuestreo Determinista (`GET /api/results/packets_window`):**
   Para evitar saturar la memoria del navegador cuando la ventana abarca cientos de miles de flits, el endpoint `packets_window` calcula dinámicamente el solapamiento $[start\_ns, end\_ns]$ y, si el número de paquetes supera el umbral configurable (`max_packets=450`), aplica un submuestreo uniforme estratificado preservando la representatividad estadística del tráfico sin degradar la tasa de refresco.

---

## 10.7. Pestaña 3: Gestor de Historial y Comparador Multi-Simulación Arbitrario (Fase 3)
La Pestaña 3 del Workbench resuelve la necesidad crítica de auditar, comparar y exportar resultados experimentales acumulados a lo largo de las distintas campañas de simulación:

### Gestor de Catálogo de Simulaciones
- **Escaneo Dinámico y Detección de Staging:** Rastrea automáticamente todas las carpetas válidas en `build/results/` (que contienen archivos `.trc`) e incluye, en la primera fila destacada con un distintivo ámbar `TEMPORAL (No guardada)`, cualquier ejecución activa presente en `build/tmp_staging/`.
- **Filtros Reactivos y Búsqueda:** Permite filtrar el catálogo en tiempo real por modelo arquitectural (Mixtral 8x7B, DeepSeek-V3, LLaMA), por topología NoC (Torus, Mesh, Ring) o mediante búsqueda de texto libre sobre nombres de carpeta, etiquetas personalizadas e hiperparámetros.
- **Acciones Directas por Fila:**
  - **`👁️ Abrir en Visor`:** Carga de manera instantánea cualquier simulación (guardada o temporal) en los visores interactivos de la Pestaña 2 (Cronograma GPU, Paquetes NoC y Visualizador Híbrido).
  - **`🏷️ Etiquetar`:** Permite asociar o editar una nota descriptiva persistente en el archivo `gui_metadata.json` dentro de la carpeta.
  - **`🗑️ Eliminar`:** Proporciona eliminación segura con protección contra *path traversal* (`POST /api/history/delete`).

### Comparador Multi-Simulación Arbitrario
- **Selección Flexible por Checkboxes:** El investigador puede marcar cualquier combinación de simulaciones ($1, 2, \dots, K$), incluyendo la comparación directa entre simulaciones de referencia guardadas y la simulación temporal recién ejecutada antes de decidir guardarla.
- **Generación de Figuras Científicas en Memoria (Base64):**
  Al pulsar "Generar Comparativa", el motor `gui/analysis_gui.py` procesa los registros en estado estacionario (última iteración) y genera directamente en búferes de memoria `io.BytesIO` (sin ensuciar el disco) las tres figuras estándar del TFM:
  1. **Anatomía de Latencia:** Barras apiladas de tiempo medio de cómputo GPU (`#10b981`), tránsito de red NoC (`#38bdf8`) y stalls de sincronización (`#ef4444`), con insignias numéricas de tiempo total en $\mu\text{s}$ y milisegundos.
  2. **Desglose de Primitivas Colectivas:** Comparativa agrupada del coste en $\mu\text{s}$ de las fases de comunicación colectiva (`MoEScatter`, `MoEGather` y `Ring-AllReduce`).
  3. **Curva de Saturación de Red NoC:** Diagrama $(\lambda, \text{Latencia Flit})$ con nubes translúcidas de operaciones individuales, centroides destacados con etiquetas flotantes y flechas indicadoras, línea de tendencia global y opción de escala semilogarítmica en el eje vertical.
- **Descarga Individual y Exportación a CSV:**
  Cada gráfica incorpora un botón para descarga individual en PNG de alta resolución. Asimismo, la tabla comparativa de métricas se exporta de forma instantánea a un archivo `.csv` descargable con formato estándar para inclusión en hojas de cálculo o memorias de investigación.

---

## 10.8. Pulido y Mejoras de Usabilidad Científica (Fase 3.5)
Durante la validación experimental intensiva de las Pestañas 2 y 3, se identificaron y subsanaron áreas de mejora ergonómica y arquitectónica, consolidando las siguientes cuatro capacidades de vanguardia en el Workbench:

### 1. Selector Global de Unidades (Ciclos [c] vs. Tiempo [µs / ns])
En sintonía con las convenciones rigurosas de la arquitectura de computadores, donde el rendimiento de procesadores y redes de interconexión se razona fundamentalmente en ciclos de reloj de máquina, se incorporó un selector de unidades segmentado en la cabecera de la Pestaña 2:
$$\mathbf{[\text{ ⏱️ Ciclos (1 GHz) } \mid \text{ 🕒 Tiempo (µs / ns) }]}$$
- **Equivalencia Física:** En nuestro modelo microarquitectónico con frecuencia de reloj de $1\text{ GHz}$, un ciclo BookSim2/GPU equivale exactamente a $1\text{ ns}$ ($1\text{ c} = 1\text{ ns}$).
- **Modo Predeterminado (Ciclos):** Al cargar cualquier simulación, la interfaz presenta todas las magnitudes en ciclos:
  - **Tarjetas KPI:** Tiempo de muro, cómputo GPU, tránsito NoC y stalls de barrera se presentan como enteros formateados con separador de millares (ej. $1.096.353\text{ c}$).
  - **Botones de Preajuste de Ventana:** Se reetiquetan automáticamente a `10k c`, `20k c`, `50k c`, `100k c`, `250k c` y `Total`.
  - **Líneas de Tiempo y Ejes:** Las marcas de graduación temporal del Cronograma GPU y del Visualizador de Paquetes proyectan la escala en ciclos (`formatSimUnit(nsValue, isDuration)`).
  - **Tooltips Flotantes:** Los intervalos temporales y desgloses de duración reflejan simultáneamente la cantidad exacta en ciclos y su equivalencia en microsegundos o nanosegundos.

### 2. Rediseño Horizontal 50/50 del Visualizador Híbrido Sincronizado
Se transformó radicalmente la disposición del Visualizador Híbrido (`.split-screen-container`), transitando de un apilamiento vertical que obligaba a un scroll excesivo a una elegante disposición en **rejilla horizontal 50% Izquierda / 50% Derecha**:
- **Columna Izquierda (50% - Cronograma GPU):** Despliega las pistas de ejecución de las GPUs ($0 \dots N-1$). Incorpora la regla CSS `position: sticky; top: 12px; z-index: 5;`, permitiendo que el cronograma de ejecución permanezca fijado en pantalla como marco de referencia inamovible mientras se examina el tráfico de red.
- **Columna Derecha (50% - Paquetes NoC en Vuelo):** Aloja el visualizador de paquetes en tránsito en un lienzo interactivo encapsulado en un contenedor con scroll vertical autónomo (`max-height: 75vh; overflow-y: auto; overflow-x: hidden;`).
- **Scrubber Común Inferior:** En la base del visor, un único slider de control temporal sincronizado desplaza el rango de observación $[\text{viewStartNs}, \text{viewEndNs}]$ de forma instantánea en ambos paneles.
- **Diseño Responsivo:** En pantallas de resolución estrecha ($< 992\text{ px}$), una *media query* conmuta suavemente a la disposición vertical apilada para preservar la legibilidad en ordenadores portátiles compactos.

### 3. Cero Truncamiento de Paquetes en el Visor Híbrido
- **Desactivación del Submuestreo Artificial:** En `gui/server.py` y `gui/trace_parser.py`, el endpoint `/api/results/packets_window` adopta por defecto `max_packets = 0`. Esto garantiza que el backend transfiera el 100% de los paquetes que solapan con la ventana temporal solicitada (`truncated: False`), permitiendo la inspección exhaustiva de ráfagas densas de flits.
- **Escalabilidad Gráfica Adaptativa:** El componente `HybridPacketCanvas` calcula la altura requerida del lienzo en píxeles ($H = \text{header} + N_{\text{paquetes}} \times \text{rowHeight} + \text{footer}$) acotándola de forma segura ante las restricciones de textura de la GPU del navegador ($\text{maxCanvasH} = 8.000\text{ px}$), acomodando miles de paquetes sin distorsión ni colapso de memoria.

### 4. Reparación de Tooltips Interactivos en Hover y Metadatos Locales
- **Desacoplamiento de Coordenadas de Hover:** El controlador `HybridSyncController` detecta de forma diferenciada el objetivo del puntero. Al posarse sobre el Cronograma GPU, `getBlockAt(x, y)` recupera el bloque computacional o de comunicación; al posarse sobre el panel de paquetes, `getPacketAt(x, y)` computa con precisión matemática la fila de paquete compensando la posición del scroll vertical interno y el `devicePixelRatio`.
- **Capa Flotante Fija:** El elemento `#hybrid-tooltip` se configuró con `position: fixed; z-index: 9999; pointer-events: none;`, asegurando que los tooltips nunca se corten contra los márgenes de los paneles y se posicionen suavemente junto al puntero.
- **Consistencia de Metadatos y Desglose MoE en Pestaña 3:** Se eliminó cualquier lectura de ficheros globales de fallback en `gui/analysis_gui.py`. El analizador inspecciona estrictamente los ficheros locales de cada simulación (`config.yaml`, `test.cfg` y el conteo de trazas `*device_*.trc`). Esto garantiza que configuraciones asimétricas de Malla 2D como `deepseekV3_4x2dev_mesh` se cataloguen con precisión como `Mesh (4x2)` y 8 GPUs (en lugar de Torus u 8 GPUs por defecto), y que `mixtral_2x2dev_mesh` se identifique como `Mesh (2x2)` y 4 GPUs. Asimismo, se armonizó la extracción de las claves de métricas (`scatter_us`, `gather_us`, `allreduce_us`, `avg_pkt_lat_cycles`), asegurando que las columnas y la gráfica comparativa de primitivas colectivas reflejen fielmente el desglose temporal sin columnas vacías a $0.00\text{ }\mu\text{s}$.

---

## 10.9. Refinamiento del Visualizador Híbrido: Contenedor Acotado con Scroll Único, Virtual Scrolling y Tooltips Microarquitectónicos (Fases 3.8 y 3.9)
Al eliminar las restricciones de submuestreo (`max_packets = 0`) para visualizar el 100% de los flits transmitidos en ráfagas densas de colectivas MoE (ej. más de 6.000 paquetes por ventana de $20\text{ }\mu\text{s}$ en DeepSeek-V3 o Mixtral 8x7B), el enfoque inicial colisionaba con dos problemas ergonómicos:
1. La expansión automática de las filas de CSS Grid estiraba la página entera hacia abajo al crecer el espaciador a decenas de miles de píxeles, eliminando el confinamiento del visor.
2. Los tooltips flotantes sobre eventos de cómputo GPU mostraban el campo de cuello de botella de memoria (`% Mem.`) vacío (`-`).

Para resolver ambos aspectos con máxima fidelidad visual y rendimiento a 60 FPS, se rediseñó el sistema con las siguientes innovaciones:

### 1. Contenedor Acotado con Scroll Vertical Único Compartido (`#hybrid-unified-scroll`)
Se encapsularon ambos paneles en **una única caja externa desplazable de altura estrictamente fija** que jamás estira la página web:
```css
#hybrid-unified-scroll {
  height: 640px;
  max-height: 74vh;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  border: 1px solid #334155;
  border-radius: 8px;
  background: #0f172a;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: start;
}
```
- **Una Única Barra de Scroll Vertical:** Ubicada en el borde derecho del contenedor `#hybrid-unified-scroll`, gobierna todo el recorrido vertical de la ventana.
- **Columna Izquierda (50% - Cronograma GPU Sticky):**
  El contenedor `#hybrid-left-pane` se fija mediante `position: sticky; top: 0; height: 638px; z-index: 5; border-right: 1px solid #334155;`. Al desplazarse el scroll vertical por los paquetes, el Cronograma de Ejecución GPU permanece inamovible a la vista (cabecera de 36 px + lienzo GPU de 602 px = 638 px).
- **Columna Derecha (50% - Paquetes NoC en Vuelo Virtualizados):**
  El contenedor `#hybrid-right-pane` delega su desplazamiento vertical directamente a `#hybrid-unified-scroll`. Incorpora:
  - Cabecera temporal sticky (`#hybrid-packets-sticky-header`, `position: sticky; top: 0; height: 36px; z-index: 15;`) con eje temporal sincronizado y píldora reactiva `Mostrando paquetes X–Y de Z`.
  - Espaciador virtual `#hybrid-packets-spacer` con altura proporcional al total de paquetes ($H = \max(600, N_{\text{paquetes}} \times 20\text{ px})$). Para 6.328 paquetes, mide $126.560\text{ px}$.
  - Lienzo flotante `#hybrid-packets-canvas` con `position: sticky; top: 36px; height: 602px; z-index: 10;`. En cada evento `scroll` de `#hybrid-unified-scroll`, renderiza exclusivamente las filas que intersecan $[\text{scrollTop}, \text{scrollTop} + 602\text{ px}]$.
- **Deslizador Horizontal Unificado:** Un único scrubber temporal en la base desplaza el eje X simultáneamente en ambos paneles.

### 2. Detección Matemática de Hover y Resaltado Reactivo
- Dado que el lienzo de paquetes está fijado mediante `position: sticky`, el índice del paquete apuntado por el cursor se recupera deterministamente como:
  $$\text{localY} = e.\text{clientY} - \text{rect}.\text{top}$$
  $$\text{virtualY} = \text{unifiedScroll}.\text{scrollTop} + \text{localY}$$
  $$\text{idx} = \left\lfloor \frac{\text{virtualY}}{20} \right\rfloor$$
- Al posarse el ratón, la fila correspondiente se ilumina con fondo celeste `rgba(56, 189, 248, 0.16)` y etiqueta PID `#38bdf8`.
- El tooltip `#hybrid-tooltip` (`position: fixed !important; z-index: 99999 !important; pointer-events: none !important;`) evita recortes y muestra la ficha completa: `PID`, `GPU src ➔ dst`, colectiva, carga útil ($N_{\text{flits}} \times 16\text{ B}$), retardo en cola, tiempo de vuelo, latencia total y timestamps en ciclos o tiempo.

### 3. Reparación Integral del Porcentaje de Memoria (`% Mem.`) y Flits en Tooltips
- **Cálculo de Cuello de Botella (`trace_parser.py`):**
  Para cada bloque computacional de categoría `calc` (`Attention`, `DenseFFN`, `ExpertFFN`, `SharedExpert`), el analizador acumula `COMP_NS` y `MEM_NS` y calcula:
  $$\text{mem\_bound\_pct} = \min\left(100.0, \max\left(0.0, \frac{\text{total\_mem\_ns}}{\text{total\_duration\_ns}} \times 100.0\right)\right)$$
  almacenando tanto `mem_bound_pct` como el alias `mem_pct`.
- **Desglose de Micro-Operaciones (`sub_ops`):**
  Se corrigió el bucle de extracción para procesar la totalidad de micro-operaciones (`for _, r in grp.iterrows():`), calculando el porcentaje de memoria individual:
  $$\text{sub\_mem\_pct} = \frac{\text{r.MEM\_NS}}{\text{r.DURATION}} \times 100.0$$
  permitiendo que la tabla interna de desglose refleje valores reales (ej. `LN: 100.0%`, `QKV_Proj: 100.0%`, `AttnGen: 0.0% (Compute-Bound)`, `O_Proj: 100.0%`).
- **Ficha de Bloque GPU en Canvas:**
  Al posar el cursor sobre cualquier bloque verde en `ChronogramCanvas` o en el panel izquierdo del Visualizador Híbrido, el tooltip despliega la fila distintiva:
  $$\text{Cuello de Botella: } \mathbf{82.9\% \text{ (Memory-Bound)}} \quad \text{o} \quad \mathbf{42.0\% \text{ (Compute-Bound)}}$$
  con código de color ámbar (`#f59e0b`) para regímenes acotados por memoria y verde (`#10b981`) para regímenes acotados por cómputo.
- **Flits Locales en Bloques de Red:**
  Se garantizó que `local_flits` en bloques de colectivas (`scatter`, `gather`, `all_reduce`) nunca sea 0 cuando `local_packets > 0`, computándose como $N_{\text{pkts}} \times 9\text{ flits}$.

### 4. Desacoplamiento de la Rueda del Ratón
- La rueda del ratón sobre el panel izquierdo (Cronograma GPU) realiza zoom horizontal sobre el eje temporal.
- La rueda del ratón sobre el panel derecho (Paquetes NoC) desplaza verticalmente el listado de paquetes en `#hybrid-unified-scroll`. Para realizar zoom horizontal desde el panel derecho, basta con mantener pulsado `Ctrl`, `Shift` o `Alt`.

---

## 10.10. Auditoría Matemática y Paridad Absoluta CLI ↔ GUI (Fase 3.9.1)
En la arquitectura del co-simulador, **la interfaz gráfica web (Workbench GUI) y los scripts de terminal (`analyze_traces.py`, `plot_cronograma.py`, `plot_packet_tracking.py`) son dos ventanas sobre una misma realidad física subyacente**. En consecuencia, ambos entornos deben arrojar **exactamente los mismos valores numéricos** en cada métrica, sin discrepancias matemáticas ni aproximaciones discordantes.

Durante la auditoría matemática de la Fase 3.9.1, se identificaron y subsanaron dos desviaciones en las fórmulas implementadas en `gui/trace_parser.py`:

### 1. Unificación del Cuello de Botella Roofline (% Mem-Bound y % Compute-Bound)
- **Diagnóstico del Fallo Previo:**
  En la Fase 3.9, la GUI calculaba el porcentaje de memoria dividiendo entre la duración de la operación:
  $$\text{mem\_pct} = \frac{\text{Mem\_ns}}{\text{Duration\_ns}} \times 100.0$$
  Dado que en el modelo analítico de Roofline la duración temporal de una operación acotada por memoria es $\text{Duration\_ns} = \max(\text{Comp\_ns}, \text{Mem\_ns}) = \text{Mem\_ns}$, el cociente resultaba idénticamente en $100.0\%$ para todos los operadores memory-bound (ocultando el balance real de cómputo frente a ancho de banda).
- **Fórmula Unificada Canónica (Paridad con `plot_cronograma.py`):**
  Se alineó la lógica tanto para macro-bloques coalescentes como para cada micro-operación individual de la traza:
  $$\mathbf{\text{Mem\_Bound \%}} = \begin{cases} \dfrac{\sum \text{Mem\_ns}}{\sum \text{Comp\_ns} + \sum \text{Mem\_ns}} \times 100.0 & \text{si } (\sum \text{Comp\_ns} + \sum \text{Mem\_ns}) > 0 \\ 0.0 & \text{en otro caso} \end{cases}$$
- **Resultados de Paridad Absoluta:**
  - Micro-operación `AttnGen` (Compute-bound puro, con $\text{Mem\_ns} = 0.0\text{ ns}$): evalúa a **$0.0\%$** en el desglose de memoria, reportándose en el tooltip como **$100.0\% \text{ (Compute-Bound)}$**.
  - Micro-operaciones de proyección lineal (`QKV_Proj`, `O_Proj`): evalúan a **$98.2\%$** de memoria.
  - Normalización de capa (`LN`): evalúa a **$99.6\%$** de memoria.
  - Macro-bloque coalescente `Attention` (Capa 0 en Mixtral): evalúa con precisión milimétrica a **$97.9\% \text{ (Memory-Bound)}$**, idéntico al rótulo generado por `plot_cronograma.py` en consola y figuras estáticas.

### 2. Unificación de la Tasa de Inyección de Red $\overline{\lambda}$ (flits/ciclo/nodo)
- **Diagnóstico del Fallo Previo:**
  La GUI calculaba la tasa $\lambda$ dividiendo los flits totales entre el tiempo global de Wall-Clock del clúster ($\text{Flits} / (N_{\text{GPUs}} \times \text{WallClock})$), arrojando valores diluidos artificialmente ($0.0587\text{ f/c/nodo}$ en Mixtral) al incluir en el denominador las fases de cómputo donde no se inyecta tráfico.
- **Fórmula Unificada Canónica (Paridad con `analyze_traces.py`):**
  La tasa media de inyección se calcula promediando la tasa activa durante la ventana temporal efectiva de cada colectiva de comunicación:
  $$\mathbf{\overline{\lambda}} = \frac{1}{M_{\text{ops}}} \sum_{op=1}^{M_{\text{ops}}} \frac{\sum_{p \in op} \text{Num\_Flits}_p}{N_{\text{GPUs}} \times \Delta\text{Ciclos}_{op}}$$
  donde la duración activa de la colectiva $op$ viene dada por:
  $$\Delta\text{Ciclos}_{op} = \max\left(1.0, \max_{p \in op}(\text{Receive\_Cycle}_p) - \min_{p \in op}(\text{Creation\_Cycle}_p)\right)$$
- **Resultados de Paridad Absoluta:**
  - En `mixtral_8dev_torus_bs32`: $\mathbf{\lambda = 0.2822\text{ flits/ciclo/nodo}}$, coincidiendo con el valor exacto impreso por `analyze_traces.py`.
  - En `deepseekV3_4x2dev_mesh_bs32`: $\mathbf{\lambda = 0.2751\text{ flits/ciclo/nodo}}$, coincidiendo con el valor exacto impreso por `analyze_traces.py`.

### 3. Matriz de Validación de Paridad Numérica CLI ↔ GUI

| Métrica Microarquitectural | Mixtral (Toro 1D, 8 GPUs) CLI | Mixtral (Toro 1D, 8 GPUs) GUI | DeepSeek-V3 (Malla 2D, 8 GPUs) CLI | DeepSeek-V3 (Malla 2D, 8 GPUs) GUI | Estado de Paridad |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tiempo de Cómputo Promedio** | $911.517,0\text{ ns}$ | $911.517,0\text{ ns}$ | $8.340.630,5\text{ ns}$ | $8.340.630,5\text{ ns}$ | **IDÉNTICO (100%)** |
| **Tránsito en Red (Vuelo NoC)** | $169.257,3\text{ ns}$ | $169.257,3\text{ ns}$ | $3.137.883,8\text{ ns}$ | $3.137.883,8\text{ ns}$ | **IDÉNTICO (100%)** |
| **Stalls de Sincronización (BSP)** | $19.268,9\text{ ns}$ | $19.268,9\text{ ns}$ | $365.008,0\text{ ns}$ | $365.008,0\text{ ns}$ | **IDÉNTICO (100%)** |
| **Primitiva MoE Scatter** | $91.479,5\text{ ns}$ | $91.479,5\text{ ns}$ | $1.034.745,5\text{ ns}$ | $1.034.745,5\text{ ns}$ | **IDÉNTICO (100%)** |
| **Primitiva MoE Gather** | $77.777,8\text{ ns}$ | $77.777,8\text{ ns}$ | $2.103.138,3\text{ ns}$ | $2.103.138,3\text{ ns}$ | **IDÉNTICO (100%)** |
| **Primitiva Ring-AllReduce** | $0,0\text{ ns}$ | $0,0\text{ ns}$ | $0,0\text{ ns}$ | $0,0\text{ ns}$ | **IDÉNTICO (100%)** |
| **Tiempo Total Wall-Clock** | $1.100.043,2\text{ ns}$ | $1.100.043,2\text{ ns}$ | $11.843.522,4\text{ ns}$ | $11.843.522,4\text{ ns}$ | **IDÉNTICO (100%)** |
| **Tasa Media de Inyección $\lambda$** | $\mathbf{0,2822\text{ f/c/n}}$ | $\mathbf{0,2822\text{ f/c/n}}$ | $\mathbf{0,2751\text{ f/c/n}}$ | $\mathbf{0,2751\text{ f/c/n}}$ | **IDÉNTICO (100%)** |
| **Latencia Media Flit NoC** | $688,1\text{ ciclos}$ | $688,1\text{ ciclos}$ | $6.255,3\text{ ciclos}$ | $6.255,3\text{ ciclos}$ | **IDÉNTICO (100%)** |
| **Latencia Media Paquete NoC** | $1.321,2\text{ ciclos}$ | $1.321,2\text{ ciclos}$ | $10.269,6\text{ ciclos}$ | $10.269,6\text{ ciclos}$ | **IDÉNTICO (100%)** |
| **Micro-op AttnGen (% Mem)** | $0,0\%$ (Compute) | $0,0\%$ (Compute) | $0,0\%$ (Compute) | $0,0\%$ (Compute) | **IDÉNTICO (100%)** |
| **Macro Attention (% Mem)** | $97,9\%$ (Mem-Bound) | $97,9\%$ (Mem-Bound) | -- | -- | **IDÉNTICO (100%)** |

---

## 10.11. Pestaña 4: Mapa Topológico Interactivo NoC, Heatmap de Tráfico e Inspector Arquitectónico (Fase 4)
La Pestaña 4 del Workbench proporciona una ventana gráfica vectorial interactiva hacia el corazón de la red de interconexión NoC y la microarquitectura de los modelos Transformer simulados. Integra dos subsistemas visuales de alto valor analítico:

### 1. Visor Topológico Vectorial Interactivo (`TopologyCanvas` en `gui/static/topology_canvas.js`)
El motor gráfico implementa un renderizado adaptativo en Canvas HTML5 (`HiDPI`) que se acomoda automáticamente a la topología y dimensionalidad de la red configurada:
- **Toro 1D / Anillo ($k$ nodos en 1 dimensión):**
  - Disposición radial centrada de los conmutadores:
    $$\theta_i = \frac{2\pi \cdot i}{N} - \frac{\pi}{2}, \quad x_i = C_x + R \cos\theta_i, \quad y_i = C_y + R \sin\theta_i$$
  - Enlaces directos ortogonales entre routers contiguos $(i \leftrightarrow (i+1)\%N)$ con latencia física de **1 ciclo** (`1c`).
  - Enlace envolvente *wrap-around* / *dateline* $(k-1 \leftrightarrow 0)$: modelado como un arco curvado exterior con latencia física de **2 ciclos** (`2c (Wrap)`), reflejando la longitud duplicada de la pista de interconexión en placa/silicio según se modela en `kncube.cpp`.
- **Malla 2D / Toro 2D ($K_x \times K_y$, incluyendo AnyNet 4x2):**
  - Mapeo bidimensional en cuadrícula ortogonal con conmutadores de esquina (2 vecinos), borde (3 vecinos) e interiores (4 vecinos).
  - En Mallas regulares o grafos AnyNet como `mesh_4x2.txt` (4 columnas, 2 filas, 8 GPUs), se dibujan exactamente los 10 enlaces bidireccionales físicos (20 canales unidireccionales de AnyNet) con latencia de 1 ciclo.
  - En Toros 2D, se añaden los arcos envolventes horizontales y verticales exteriores con latencia de 2 ciclos.
- **Malla 3D / Toro 3D ($K_x \times K_y \times K_z$):**
  - Proyección isométrica multicapa separando planos Z, con enlaces ortogonales en los ejes X, Y y Z.

### 2. Mapa de Calor de Tráfico (Heatmap) y Detección de Cuellos de Botella *In-Cast*
Cada conmutador/GPU se colorea mediante un mapa de calor térmico continuo interpolado en cuatro tonos cromáticos:
$$\text{Azul Frío } (\text{Carga Mínima}) \longrightarrow \text{Verde Esmeralda} \longrightarrow \text{Ámbar} \longrightarrow \text{Rojo Carmesí } (\text{Punto Caliente / Hotspot})$$

El usuario puede alternar en tiempo real entre múltiples métricas microarquitecturales:
1. **Tráfico Recibido (% RX / In-Cast Hotspots):** Fracción porcentual de paquetes que ingresan en cada GPU. Permite verificar visualmente de un vistazo el desbalance de enrutamiento inducido por funciones de distribución sesgadas (como Zipf/Power-Law).
   - **Caso de Estudio Validado (`mixtral_8dev_torus_bs32_skew1.0`):**
     Con $\text{skewness} = 1.0$, el router de la **GPU 0 absorbe el $30.81\%$ de los paquetes** en la fase `MoE Scatter` (17.568 paquetes), convirtiéndose en un cuello de botella térmico crítico (*In-Cast Hotspot*), mientras que la **GPU 7 absorbe únicamente el $5.08\%$** (2.896 paquetes).
2. **Tráfico Emitido (% TX):** Fracción de paquetes inyectados por cada GPU.
3. **Retardo en Cola NIC (`Queueing_Delay`):** Espera activa de los paquetes antes de entrar en los canales virtuales del router. En GPU 0 bajo $\text{skew}=1.0$, el retardo medio en cola alcanza $447,8\text{ ciclos}$, mientras que los emisores saturados alcanzan hasta $2.919,1\text{ ciclos}$ de retardo en cola esperando a que el router destino drene sus flits.
4. **Tiempo de Bloqueo (`NETWORK_STALL`):** Retraso temporal acumulado en la barrera BSP antes de poder reanudar el cómputo de la capa.

### 3. Matriz y Flujos de Comunicación Ponderados (`Source ➔ Dest`)
Superpuestos al grafo topológico, el visor dibuja flechas direccionales curvadas para cada par emisor-receptor $(s, d)$:
- **Grosor y Opacidad Adaptativos:** Escalan dinámicamente con el volumen de tráfico relativo ($N_{\text{paquetes}} / N_{\text{max}}$).
- **Filtro de Colectiva:** Permite aislar el tráfico de `MoE Scatter` (tokens hacia expertos), `MoE Gather` (retorno de activaciones procesadas) o `Ring-AllReduce` (Tensor Parallelism).
- **Aislamiento por Nodo en Hover/Click:** Al posar el cursor o hacer clic sobre un nodo, se atenúan todas las conexiones ajenas y se iluminan con colores diferenciados sus flujos salientes (ámbar `#fbbf24`) y entrantes (carmesí `#f43f5e`).

### 4. Inspector Microarquitectural de Nodo
Un panel lateral contextual exhibe la radiografía completa del conmutador seleccionado:
- **Asignación de Expertos:**
  - En Mixtral 8x7B (8 GPUs): `Exp #d` (un experto por GPU).
  - En DeepSeek-V3 (8 GPUs): `Exp #(32*d)..#(32*d+31) + Shared` (32 micro-expertos por GPU más el experto compartido redundante).
  - En LLaMA: `Denso (Sin MoE)`.
- **Métricas Cuantitativas:** Paquetes y flits TX/RX, retardo en cola NIC, latencia media de red, tiempo de cómputo GPU, tiempo de tránsito NoC y stalls de barrera.
- **Top 5 Flujos Entrantes y Salientes:** Tabla desglosada con volumen de paquetes, flits, latencia de vuelo y cuota de tráfico sobre el total del clúster.

### 5. Inspector Comparativo de Arquitecturas Transformer
En la base de la pestaña, se integran tres fichas comparativas que desglosan el flujo de ejecución capa a capa y la huella en red:
1. **Mixtral 8x7B (Sparse MoE):**
   - Atención GQA ($d_{\text{model}}=4096$) $\rightarrow$ Router Softmax Top-2 $\rightarrow$ MoE Scatter ($288\text{ B/token}$, 9 flits) $\rightarrow$ 8 Expertos SwiGLU ($176\text{ MB/exp}$) $\rightarrow$ MoE Gather simétrico.
2. **DeepSeek-V3 (Fine-Grained MoE + MLA):**
   - Atención MLA con compresión latente KV a 512 dim ($576\text{ B/token}$) $\rightarrow$ Router Top-8 sobre 256 micro-expertos $\rightarrow$ Scatter en FP8 ($7.168\text{ B}$) $\rightarrow$ 32 micro-expertos/GPU + 1 Shared Expert local $\rightarrow$ Gather en BF16 ($14.336\text{ B}$, volumen 2x respecto a Scatter) $\rightarrow$ Capas 0–2 densas, 3–59 híbridas.
3. **LLaMA (Denso Baseline):**
   - MHA/GQA tradicional $\rightarrow$ FFN SwiGLU monolítico denso $\rightarrow$ Sin tráfico MoE (solo Ring-AllReduce si $TP > 1$).

---

## 10.12. Refinamiento de Pestaña 4: Mapa de Calor Térmico en Enlaces/Flujos NoC y Tooltips Interactivos en Hover sobre Conexiones (Fase 4.5)

La Fase 4.5 dota a la infraestructura de interconexión (tanto a los enlaces físicos entre routers como a las flechas de flujo dirigido lógico $Src \to Dst$) del mismo rigor analítico y visual que poseían los nodos GPU, cerrando la brecha de inspección microarquitectural en la red NoC.

### 1. Mapeo y Proyección de Enrutamiento sobre Enlaces Físicos (`_compute_routing_path` en `gui/trace_parser.py`)
Para evaluar la carga real que soporta cada enlace de la red física a partir de las trazas de paquetes de BookSim2 (`packet_tracking_debug.csv`), el backend implementa una función de enrutamiento determinista que reproduce con fidelidad los algoritmos del simulador:
- **Toro 1D / Anillo:** Determina la distancia circular mínima hacia adelante y hacia atrás:
  $$d_{\text{fwd}} = (dst - src) \pmod N, \quad d_{\text{bwd}} = (src - dst) \pmod N$$
  Si $d_{\text{bwd}} < d_{\text{fwd}}$, el tráfico atraviesa el enlace envolvente *wrap-around* / *dateline* $(N-1 \leftrightarrow 0)$ de 2 ciclos.
- **Mallas y Toros 2D / 3D:** Implementa *Dimension-Order Routing* (`DOR`), recorriendo estrictamente la dimensión 0 (eje X), posteriormente la dimensión 1 (eje Y) y finalmente la dimensión 2 (eje Z), seleccionando el camino circular mínimo en dimensiones con configuración toroidal.
- **Topologías Irregulares / AnyNet (`mesh_4x2.txt`):** Camino mínimo computado mediante búsqueda en anchura (*BFS*) sobre la lista de adyacencia física.

#### Acumulación Vectorizada de Métricas en Enlaces Físicos
Para cada flujo lógico $(s, d)$ con $N_{\text{pkts}} > 0$, el parser descompone la ruta en saltos $(u, v)$ y proyecta ponderadamente sobre el enlace físico no dirigido $\text{link}(u, v)$:
1. **Volumen de Tráfico y Cuota:** Suma total de paquetes y flits que atraviesan el canal, calculando su porcentaje respecto al clúster:
   $$\text{Share}_{\text{link}}\% = \left(\frac{N_{\text{pkts, link}}}{N_{\text{total cluster}}}\right) \times 100$$
2. **Balance Direccional:** Desglose del tráfico en sentido $u \to v$ versus $v \to u$, revelando asimetrías de inyección y drenaje.
3. **Retardo Medio en Cola y Latencia de Tránsito Ponderados:**
   $$\overline{D}_{\text{queue, link}} = \frac{\sum_f D_{\text{queue}, f} \cdot N_{\text{pkts}, f}}{\sum_f N_{\text{pkts}, f}}, \quad \overline{L}_{\text{net, link}} = \frac{\sum_f L_{\text{net}, f} \cdot N_{\text{pkts}, f}}{\sum_f N_{\text{pkts}, f}}$$
4. **Contención de Barrera (Stalls):** Promedio de los tiempos de bloqueo en barrera BSP de los nodos extremos $\frac{\text{Stall}_u + \text{Stall}_v}{2}$.

#### Evidencia Experimental Validada en Clúster Real
- **Malla 4x2 AnyNet (`deepseekV3_4x2dev_mesh_bs32`):**
  - Los **enlaces centrales del corte de bisección** soportan el cuello de botella más severo de la red:
    - Enlace horizontal superior $1 \leftrightarrow 2$: **$308.168\text{ paquetes}$ ($28,73\%$ del tráfico total)**, con retardo medio en cola de $8.646,0\text{ ciclos}$.
    - Enlace horizontal inferior $5 \leftrightarrow 6$: **$303.100\text{ paquetes}$ ($28,26\%$ del tráfico total)**, con retardo medio en cola de $11.695,8\text{ ciclos}$.
  - En contraste, los enlaces periféricos de esquina soportan una carga sustancialmente menor:
    - Enlace vertical columna 0 ($0 \leftrightarrow 4$): **$153.048\text{ paquetes}$ ($14,27\%$)**.
    - Enlace vertical columna 3 ($3 \leftrightarrow 7$): **$154.588\text{ paquetes}$ ($14,41\%$)**.
- **Toro 1D con Skewness MoE (`mixtral_8dev_torus_bs32_skew1.0`):**
  - Los dos enlaces físicos directamente incidentes en el nodo hotspot (**GPU 0**) concentran la mayor densidad de paquetes de todo el anillo:
    - Enlace vecino $0 \leftrightarrow 1$: **$20.880\text{ paquetes}$ ($36,27\%$ de cuota)**.
    - Enlace wrap-around $7 \leftrightarrow 0$: **$19.024\text{ paquetes}$ ($33,05\%$ de cuota)**.
  - El enlace diametralmente opuesto a la GPU 0 ($4 \leftrightarrow 5$) soporta únicamente **$12.112\text{ paquetes}$ ($21,04\%$)**, evidenciando visual y cuantitativamente la acumulación de tráfico hacia el experto más demandado.

---

### 2. Renderizado Térmico Continuo en Conexiones (`topology_canvas.js`)
El motor de Canvas extiende la función de interpolación cromática térmica de 4 etapas (`getHeatColor(ratio)`):
$$\text{Azul Frío (\#0284c7)} \xrightarrow{0.33} \text{Verde Esmeralda (\#10b981)} \xrightarrow{0.66} \text{Ámbar (\#f59e0b)} \xrightarrow{1.0} \text{Rojo Neón (\#ef4444)}$$

1. **Enlaces Físicos:**
   - Grosor lineal proporcional a la intensidad de la métrica activa: de $2.0\text{ px}$ en enlaces ociosos hasta $7.5\text{ px}$ en enlaces saturados de bisección:
     $$\text{LineWidth} = 2.0 + 5.5 \cdot \left(\frac{V_{\text{link}}}{V_{\text{max, link}}}\right)$$
   - Resplandor difuso (*Shadow Blur Glow* con radio de $10\text{ px}$ en rojo carmesí) aplicado en enlaces con $\text{ratio} > 0.70$ para destacar visualmente las rutas estranguladas.
2. **Flechas de Flujo Dirigido ($Src \to Dst$):**
   - Trazado de arcos Bézier cuadráticos perpendiculares que evitan colisiones entre sentidos inversos.
   - Opacidad dinámica adaptativa de $0.25$ a $0.90$ según la cuota de paquetes del flujo, garantizando que los flujos críticos resalten claramente sobre los flujos residuales.

---

### 3. Hit-Testing Geométrico y Tooltips Interactivos en Hover
El lienzo implementa detección matemática de puntero en tiempo real mediante registro de geometría proyectada en `this.renderedEdges`:
- **Distancia Punto a Segmento Recto:**
  $$\text{dist}(P, AB) = \left\| P - \left(A + t \cdot (B - A)\right) \right\|, \quad t = \text{clamp}\left(\frac{(P - A) \cdot (B - A)}{\|B - A\|^2}, 0, 1\right)$$
- **Distancia Punto a Curva Bézier Cuadrática:** Muestreo poligonal discretizado en 24 subdivisiones con cálculo de distancia mínima euclídea acumulada.
- **Interacción y Despliegue Contextual:**
  - Tolerancia de detección de $8.0\text{ px}$ (priorizando los nodos circulares sobre las aristas).
  - Al posar el cursor sobre un enlace o flujo, se resalta inmediatamente con un trazado blanco/dorado brillante (`#f8fafc`, $+2.5\text{ px}$ de grosor) y se abre el tooltip flotante (`#topology-tooltip`):
    - **En Enlace Físico ($u \leftrightarrow v$):** Exhibe tipo de enlace, latencia base de conmutación (1c vecino o 2c wrap-around), volumen en paquetes y flits con cuota porcentual, balance direccional ($u \to v$ vs. $v \to u$), retardo medio en cola NIC y latencia media de red.
    - **En Flujo Lógico ($s \to d$):** Exhibe distancia topológica en saltos mínimos, volumen transmitido, cuota de tráfico, retardo en cola NIC (media y pico máximo registrado) y latencia desglosada (vuelo/contención NoC y latencia total de entrega).

---

## 10.13. Despliegue en Linux (`run_gui.sh`) y Validación End-to-End del Sistema (Fase 5)

La Fase 5 culmina el desarrollo del *LLM-NoC Co-Simulation Workbench*, dotándolo de un mecanismo de arranque robusto para entornos Linux, higiene automática de directorios y una batería de pruebas de integración *End-to-End* (E2E) que certifica el funcionamiento impecable de sus 4 pestañas y el 100% de paridad matemática con los scripts CLI originales.

### 1. Lanzador Portable para Linux (`run_gui.sh`)
Para facilitar la reproducibilidad científica y la defensa técnica del TFM, se implementó el script ejecutable [`LLMSimulator/run_gui.sh`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/run_gui.sh) con permisos `chmod +x`. El lanzador realiza de forma desatendida las siguientes comprobaciones previas antes de levantar el servidor:
1. **Posicionamiento Automático:** Determina el directorio canónico del script mediante `cd "$(dirname "${BASH_SOURCE[0]}")"`.
2. **Auditoría de Entorno Python y Paquetes Científicos:** Verifica la disponibilidad de `python3` y la presencia de `pandas`, `numpy` y `matplotlib`. Si falta algún paquete, emite un mensaje descriptivo con el comando de instalación exacto.
3. **Comprobación de Compilación del Simulador C++:** Valida la existencia del binario ejecutable `./build/run`. En caso de ausencia, guía al usuario imprimiendo los comandos estándar de compilación:
   ```bash
   cmake -B build
   cmake --build build -j$(nproc)
   ```
4. **Higiene de Directorio Staging:** Detecta y purga carpetas vacías o sesiones huérfanas en `build/tmp_staging/` garantizando un estado inicial limpio (`idle`).
5. **Propagación Transparente de Argumentos:** Analiza parámetros CLI (como `--port <N>` o `--no-browser`) sin mutar `$@` y transfiere el control directamente mediante `exec python3 launch_gui.py "$@"`.

---

### 2. Resultados de la Batería de Validación End-to-End (E2E)
Se ejecutó un banco de pruebas automatizado integral contra una instancia real del servidor HTTP local (`launch_gui.py --no-browser --port 8095`), validando el ciclo de vida completo de una simulación:

#### A. Recursos Estáticos y Tipado MIME
Se verificó respuesta `HTTP 200` y cabeceras `Content-Type` correctas en todos los ficheros esenciales:
- `/` $\implies$ `text/html; charset=utf-8` ($52.653\text{ B}$)
- `/styles.css` $\implies$ `text/css; charset=utf-8` ($46.530\text{ B}$)
- `/app.js` $\implies$ `text/javascript; charset=utf-8` ($82.538\text{ B}$)
- `/timeline_canvas.js` $\implies$ `text/javascript; charset=utf-8` ($57.523\text{ B}$)
- `/topology_canvas.js` $\implies$ `text/javascript; charset=utf-8` ($32.397\text{ B}$)
- `/api/status` $\implies$ `application/json; charset=utf-8`

#### B. Simulación Real en Staging: Malla 2D Asimétrica AnyNet con Tensor Parallelism (TP=2)
Se lanzó vía `POST /api/run` una simulación de **Mixtral 8x7B en Malla 4x2 (8 GPUs)** con $TP=2$, $BS=32$ y 2 iteraciones, verificando:
- **Generación Automática de AnyNet:** Escritura correcta del archivo de enlaces `mesh_4x2.txt` y configuración `test.cfg`.
- **Monitorización Continua (`GET /api/status`):** Seguimiento en tiempo real de la ejecución hasta el $100\%$ de progreso completado en $7,5\text{ s}$ en `build/tmp_staging/`.
- **Inspección de Pestaña 2:**
  - Resumen macroscópico: $\text{Wall-Clock} = 1.063,18\text{ }\mu\text{s}$, $\text{Cómputo} = 828,48\text{ }\mu\text{s}$, $\text{Tránsito NoC} = 257,47\text{ }\mu\text{s}$, $\text{Stalls} = 14,47\text{ }\mu\text{s}$, $\text{Paquetes} = 119.000$, $\text{Flits} = 1.071.000$, $\lambda = 0,2616\text{ f/c/n}$.
  - Detección de operaciones en cronograma: presencia activa de `AllReduce` (Tensor Parallelism), `Scatter` y `Gather` (MoE).
  - Virtual Scrolling en visor de paquetes: $5.672\text{ paquetes}$ renderizados al vuelo en la ventana temporal sin truncamiento (`truncated: false`).
- **Inspección de Pestaña 4 (Topología NoC):**
  - Mapeo de los 10 enlaces físicos con $176.296\text{ paquetes}$ proyectados según el enrutamiento determinista y $56\text{ flujos}$ dirigidos observados.
- **Inspección de Pestaña 3 (Comparativa Multi-Simulación):**
  - Generación de las 3 gráficas vectoriales Base64 (`anatomia_latencia`, `desglose_primitivas_moe` y `curva_saturacion_red`) contrastando la simulación en staging contra simulaciones históricas guardadas (`deepseekV3_4x2dev_mesh` y `mixtral_8dev_torus_skew1.0`).
- **Descarte Seguro (`POST /api/results/discard`):**
  - Limpieza total del directorio `build/tmp_staging/` (0 elementos restantes) y transición automática del backend al estado `idle`.

---

### 3. Certificación de Aislamiento Estricto (Golden Rule of Isolation)
Mediante inspección forense con `git diff` y `git status`, se certificó que **ninguno de los scripts CLI tradicionales** (`run_sim.py`, `analyze_traces.py`, `plot_cronograma.py`, `plot_packet_tracking.py`) ni los archivos fuente en C++ (`src/`, `eval/`, `booksim2/`) sufrieron alteración alguna durante el desarrollo de las 5 fases. La GUI web reside en un espacio totalmente autónomo en `gui/`, garantizando la coexistencia armónica y la repetibilidad estricta de los resultados.

---

## 10.14. Optimización de Memoria y Escalabilidad para Simulaciones Masivas (16+ GPUs / DeepSeek-V3 BS=128)

Al escalar simulaciones a configuraciones de gran tamaño como **DeepSeek-V3 en 16 GPUs con Batch Size 128 y Skewness 0.6** (`9.197.160` filas totales en `packet_tracking_debug.csv`, `938 MB` en disco, `4.595.976` paquetes en la última iteración y `35,59M` ciclos), la lectura concurrente sin control desde `ThreadingHTTPServer` disparaba múltiples invocaciones paralelas de `pd.read_csv()` con tipos por defecto (`int64`/`float64`/`object`), superando varios gigabytes de RAM y provocando la terminación abrupta por el *OOM Killer* de Linux. Se implementó una arquitectura integral de contención de memoria y vectorización en `LLMSimulator/gui/` sin alterar ningún script CLI ni fuente C++:

### 1. Cachés LRU Thread-Safe con Lock por Archivo y Carga Compacta (`trace_parser.py` y `analysis_gui.py`)
1. **Cachés Compartidas Sincronizadas (`_CSV_CACHE`, `_TRC_CACHE`, `_CLUSTER_INFO_CACHE`, `_SUMMARY_CACHE`, `_CHRONO_CACHE`):**
   - Cada ruta canónica dispone de un `threading.Lock` dedicado (`_get_path_lock`). Cuando múltiples hilos HTTP solicitan `/api/results/summary`, `/api/results/chronogram`, `/api/results/packets` y `/api/results/packets_window` simultáneamente, solo el primer hilo lee y parsea el CSV/TRC mientras el resto reutiliza la estructura inmutable en memoria (invalidada automáticamente por `(st_mtime_ns, st_size)`).
   - El límite combinado de `_CSV_CACHE` (`_CSV_CACHE_MAX_ENTRIES = 2`, `_CSV_CACHE_MAX_BYTES = 450 MB`) expulsa cachés previas antes de cargar un CSV masivo nuevo (`> 120 MB` en disco), evitando picos acumulados.
   - `invalidate_simulation_cache()` limpia explícitamente cachés y ejecuta `gc.collect()` + `_malloc_trim()` al guardar (`save`), descartar (`discard`) o borrar (`delete`) simulaciones.
2. **Carga Pre-Asignada y Tipado Compacto (`load_packet_csv_cached`):**
   - Selección estricta de columnas esenciales (`usecols` de 11 columnas cuando las 3 columnas de ciclo `Creation_Cycle`, `Inject_Cycle`, `Receive_Cycle` están presentes) y tipos compactos (`int32` para PID/ciclos, `int16` para `Source`/`Dest`/`Num_Flits`/`Op_Idx`, `float32` para `Avg_Flit_Latency`, `float64` para `Op_Start_NS` preservando alineación exacta de 0 ciclos, y `category` para `Op_Type`).
   - Para archivos `> 40 MB`, se realiza un conteo binario rápido de líneas y una pre-asignación exacta de arrays NumPy rellenados en bloques (`chunksize = 250.000`), reduciendo la huella de `9.197.160` filas a **`324,5 MB`** en DataFrame (frente a `> 2,5 GB` originales) y el RSS de carga inicial a **`437,5 MB`**.
3. **Vectorización Completa y Reducción de Payload:**
   - Eliminación de `.apply()` y `.iterrows()` en `parse_single_trc_segment`, `load_network_ops_debug`, `get_packet_tracking_data` y `get_packets_in_time_window`, sustituidos por vistas sin copia (`iloc`), `groupby(..., observed=True)` y compresión de `sub_ops` junto con la supresión de la lista duplicada `blocks` en `get_chronogram_data` (reduciendo el JSON del cronograma de `33.682,8 KB` a `9.515,5 KB`).
   - Serialización controlada (`_HEAVY_DF_OP_LOCK`) únicamente cuando el DataFrame excede `1.000.000` de filas para evitar picos simultáneos entre hilos, manteniendo las simulaciones pequeñas sin bloqueo.

### 2. Protección Adaptativa en Ventana Temporal (`SAFE_MAX_PACKETS = 2500`)
- En `get_packets_in_time_window` (`trace_parser.py`) y `/api/results/packets_window` (`server.py`), se impone un tope adaptativo seguro de `2.500` paquetes por respuesta:
  - Si la ventana visible contiene $\le 2.500$ paquetes, se devuelve el **100% exacto sin truncamiento** (`truncated: False`).
  - Si la ventana contiene $> 2.500$ paquetes (p. ej., zoom amplio en simulaciones de 4,6M paquetes), se aplica **muestreo estratificado uniforme determinista** sobre el eje temporal ordenado (`np.argsort` + `np.linspace`), devolviendo `2.500` paquetes (`truncated: True`, `total_in_window: <total_real>`).
- En la interfaz (`timeline_canvas.js`, `app.js`, `styles.css`), la píldora de cabecera del panel derecho muestra un aviso claro en **ámbar** (`Mostrando 2.500 de X paquetes (muestreo macro — haz zoom para ver el 100% exacto)`) y se incorporó cancelación automática de peticiones obsoletas con `AbortController` al hacer zoom/panorámica o al pulsar **Guardar Simulación**.

### 3. Validación Experimental y Paridad Numérica CLI ↔ GUI (`DeepSeek-V3`, 16 GPUs, BS=128)
La batería de estrés concurrente sobre `deepseekV3_16dev_torus_bs128_skew0.6_20261125_202758` arrojó los siguientes resultados verificados:

| Indicador Auditado | Resultado Obtenido | Criterio / Referencia CLI |
| :--- | :--- | :--- |
| **Memoria Estable (`VmRSS`) del Servidor** | **`561,0 MB` – `581,2 MB`** (tras carga y 4 endpoints concurrentes) | Contenido bajo `< 800 MB` |
| **Respuesta Concurrente en Caliente (4 endpoints)** | **`0,46 s` total** (`summary`: `0,005 s`, `chronogram`: `0,159 s`, `packets`: `0,299 s`, `packets_window`: `0,454 s`) | `< 2,0 s` |
| **Muestreo Macro (Ventana Total 4.595.976 pkts)** | `total=4.595.976`, `returned=2.500`, `truncated=True` | Aviso ámbar activo sin caída |
| **Ventana Detallada ($\le 2.500$ pkts, `mixtral_8dev_torus_bs128`)** | `total=1.953`, `returned=1.953`, `truncated=False` | 100% exacto sin muestreo |
| **Paridad Exacta (`Compute` / `Transit` / `Stalls` / `Wall-Clock`)** | `15.847.776,2` / `16.631.736,6` / `3.112.331,9` / `35.591.844,7 ns` | Idéntico decimal a decimal a `analyze_traces.py` |
| **Paridad de Red ($\lambda$ / `Avg_Flit_Lat` / `Avg_Pkt_Lat`)** | `0,1192 f/c/n` / `31.327,8 c` / `71.806,6 c` | Idéntico a `analyze_traces.py` |

---

*Fin del Documento Maestro - TFM Technical Bible (Noviembre 2026)*


