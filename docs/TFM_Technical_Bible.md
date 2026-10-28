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
5. [Capítulo 5: Parches Arquitectónicos Aplicados al Simulador Base](#capítulo-5-parches-arquitectónicos-aplicados-al-simulador-base)
   - 5.1. Correcciones Críticas en `decoder.cpp`: Conexiones Residuales y Tipado de Capas
   - 5.2. Correcciones en `layer.cpp`: Cadena de Dependencias en Bloques SwiGLU
   - 5.3. Correcciones en `timeboard.cpp`: Preservación de la Causalidad Temporal Asíncrona
6. [Capítulo 6: Sistema de Trazabilidad Completa (.trc y .csv) y Suite de Análisis en Python](#capítulo-6-sistema-de-trazabilidad-completa-trc-y-csv-y-suite-de-análisis-en-python)
   - 6.1. Arquitectura del Logger C++ en `Device`, `Module` y `ModuleGraph`
   - 6.2. Propagación de Identidad Jerárquica (`module_map_name`) a Nodos POP
   - 6.3. Automatización de Ejecución y Orquestación (`run_sim.py`)
   - 6.4. Análisis Macroscópico de Latencias (`analyze_traces.py`)
   - 6.5. Visualizador de Congestión en Red y Paginación de Paquetes (`plot_packet_tracking.py`)
   - 6.6. Cronograma Micro-Arquitectural Causal GPU Cycle-to-Cycle (`plot_cronograma.py`)
7. [Capítulo 7: Amenazas a la Validez, Limitaciones Actuales y Hoja de Ruta de Mejoras](#capítulo-7-amenazas-a-la-validez-limitaciones-actuales-y-hoja-de-ruta-de-mejoras)
   - 7.1. Simplificaciones Asumidas en el Co-Simulador Actual
   - 7.2. Evaluación de Impacto en la Precisión Científica
   - 7.3. Hoja de Ruta y Roadmap de Extensiones Futuras
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
- **Caché de Memoización:** Como simular millones de transacciones DRAM ciclo a ciclo en cada capa ralentizaría la simulación miles de veces, `Device` implementa una caché hash (`addExecutionCache` / `checkExecutionCache` en [`src/hardware/device.cpp:L90-L98`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/hardware/device.cpp#L90-L98)). Las dimensiones de tensores idénticas consultadas previamente devuelven instantáneamente la latencia DRAM simulada en la primera llamada.

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

#### Paso 3: Retiro de Flits y Medición de Llegada por Destino
Durante el bucle de avance de BookSim2:
```cpp
std::map<int, int> max_relative_atime;
for (int d = 0; d < total_num_device; d++) max_relative_atime[d] = delta_t[d];

while (total_received < total_injected) {
    if (packets_by_cycle.count(cycles)) {
        for (const auto& pkt : packets_by_cycle[cycles]) {
            BookSim_InjectPacket(pkt.src, pkt.dst, pkt.flits);
        }
        packets_by_cycle.erase(cycles);
    }
    BookSim_AdvanceCycle();
    cycles++;
    while (BookSim_CheckReceived(pkt_info)) {
        total_received++;
        if (cycles > max_relative_atime[pkt_info.dst]) {
            max_relative_atime[pkt_info.dst] = cycles;
        }
    }
}
```

#### Paso 4: Asignación Individual y Registro
Para cada dispositivo $dst$:
```cpp
for (int d = 0; d < total_num_device; d++) {
    double t_end = t_min + (double)max_relative_atime[d];
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
- **Trazabilidad de Paquetes Activa por Defecto:** Activa de forma predeterminada `SIM_DEBUG_PIDS="1"`, interceptando mediante pipes de subproceso las líneas `[TRACK_PID]` emitidas por BookSim2 y volcándolas de forma estructurada a `packet_tracking_debug.csv`. Incorpora el flag `--no_debug_pids` para deshabilitar esta exportación en barridos masivos de baja sobrecarga de I/O.
- Sella y organiza los archivos generados en subdirectorios únicos por marca temporal en `build/results/<experimento>/`.

---

## 6.4. Análisis Macroscópico de Latencias (`analyze_traces.py`)

Ubicado en [`LLMSimulator/analyze_traces.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/analyze_traces.py), realiza el posprocesamiento macroscópico de los archivos `.trc` generados por el clúster.

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
- **Tránsito Físico de Red ($\overline{T}_{\text{transit}}$):** Retardo de propagación y enrutamiento en BookSim2 derivado de primitivas All-to-All (`moe_scatter` y `moe_gather`).
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
    `S{src}→D{dst} (9 flits / 288B) | Lat.Mitja: {avg_flit_lat:.1f}c | Prod: {prod:.3f} flits/c | NS: {g_start:.0f}-{g_end:.0f}`
  - **Formulación Matemática de las Métricas Acumuladas:**
    $$\text{Avg\_Flit\_Latency}(atime) = \frac{\sum_{k \in \text{flits recibidos en la op hasta } atime} (t_{\text{retire}, k} - ctime)}{\text{Total global de flits recibidos en la op hasta } atime} \quad [\text{ciclos}]$$
    $$\text{Throughput}(atime) = \frac{\text{Total global de flits recibidos en la op hasta } atime}{\max(1, atime - t_{\text{start\_op}})} \quad [\text{flits/ciclo}]$$
- **Sombreado Semántico por Operación de Red (`ax.axhspan`):**
  - Identifica transiciones entre operaciones colectivas sucesivas (`Scatter NºX` vs. `Gather NºX`).
  - Aplica franjas horizontales de fondo suaves alternas (azul claro para Scatter, violeta/verde claro para Gather).
  - Dibuja líneas horizontales discontinuas (`linestyle='--'`) en la frontera exacta de cambio de operación.
  - Inserta tarjetas o badges destacados en el extremo derecho del gráfico con la leyenda de operación y su intervalo en nanosegundos: `Scatter Nº1 \n NS 6362 - 10547`.
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

#### Umbrales Adaptativos de Renderizado
Para prevenir cualquier solapamiento tipográfico o desbordamiento fuera de las cajas de tiempo:
- **`dibujo_dur >= 2500 ns`:** Renderizado completo de 3 líneas (tamaño de fuente entre $6.5\text{ pt}$ y $7.5\text{ pt}$).
- **`1500 ns <= dibujo_dur < 2500 ns`:** Renderizado balanceado de 2 líneas (Cabecera + Secuencia de operaciones).
- **`dibujo_dur < 1500 ns`:** Renderizado ultracompacto de 1 línea (`L{L} | {MacroOp}` a $6.0\text{ pt}$).

### 6.6.4. Enriquecimiento de Bloques de Red Colectivos (Scatter y Gather)

Los bloques azules de comunicación física en BookSim2 incorporan:
- **Cabecera con Capa y Operación Ordinal:** `Layer {L} | Scatter Nº{k}` o `Layer {L} | Gather Nº{k}`.
- **Cruce en Memoria con `packet_tracking_debug.csv` (Última Iteración):**
  - **Identificadores de Paquetes:** Rango exacto de identificadores y recuento total: `PIDs {min}-{max} ({count} pkts)`.
  - **Métricas de Flits en Tiempo Real:** Latencia media por flit y productividad acumulada calculadas en BookSim2:
    $$\text{"Lat.Mitja: 1631.2c | Prod: 2.05 flits/c"}$$

### 6.6.5. Coalescencia Causal Global Previa a la Ventana y Filtro Anti-Appends

- **Coalescencia Global Invariante:** Para evitar que un bloque largo de cómputo (por ejemplo, un `ExpertFFN` de $44.3\,\mu\text{s}$ en 4 GPUs) resulte fracturado o pierda su diagnóstico de operaciones al cruzar el límite de una ventana de $10.000\text{ ns}$, la coalescencia se efectúa a escala completa sobre toda la traza de cada GPU antes de segmentar en ventanas.
- **Filtro Anti-Appends:** Detecta automáticamente saltos negativos en la columna `START_NS` ($\Delta t < 0$), saneando las trazas si el archivo `.trc` contenía ejecuciones previas y analizando exclusivamente la última iteración simulada.

---

# CAPÍTULO 7: Amenazas a la Validez, Limitaciones Actuales y Hoja de Ruta de Mejoras

Para mantener el máximo rigor científico en esta investigación de Máster, se declaran de manera transparente las simplificaciones y limitaciones presentes en el entorno de co-simulación actual.

## 7.1. Estado de las Simplificaciones del Simulador y Resoluciones del Bloque C

1. **Latencia de Red Individualizada por GPU Destino (Resuelto en Bloque C - ✅):**
   *Estado Previo:* El Oráculo calculaba el ciclo de llegada del último paquete global de la red y aplicaba ese escalar uniforme a todas las GPUs.
   *Resolución Implementada:* Mediante `BookSimCoSimManager::cached_latency_per_gpu[layer_name][dst]`, el Oráculo ahora monitorea el ciclo exacto de recepción (`atime`) del último paquete dirigido a cada GPU $dst$. Cada GPU aplica exclusivamente su duración neta individual de red.
2. **Desfase Causal de Inyección ($\Delta t_{src}$) según Reloj Real (Resuelto en Bloque C - ✅):**
   *Estado Previo:* Todos los paquetes se inyectaban en BookSim2 asumiendo un reloj local relativo común en ciclo 0.
   *Resolución Implementada:* El Oráculo muestrea los tiempos reales absolutos de llegada $t_{\text{src}}[s]$ de cada GPU al módulo de red, calcula el desfase relativo $\Delta t_{\text{src}}[s] = \text{round}(t_{\text{src}}[s] - t_{\min})$ e inyecta los paquetes en BookSim2 en el ciclo exacto `cycles == delta_t[src]`. Las GPUs rápidas comienzan a emitir de inmediato y las lentas entran posteriormente.
3. **Desacoplamiento de Cómputo Local en `ExpertFFN` (Resuelto en Bloque C - ✅):**
   *Estado Previo:* La barrera `sync_for_moe_scatter` contenía `device_list`, obligando a todo el clúster a sincronizarse antes de que cualquier GPU pudiera iniciar su cómputo.
   *Resolución Implementada:* `sync_for_moe_scatter` se acota a `{device_total_rank}`, permitiendo a las GPUs que reciben menos tokens (o más cercanas) comenzar su cómputo `ExpertFFN` inmediatamente. La barrera previa a Gather (`sync_3`) opera con `equalize_time = false` para verificar la dependencia de datos sin aplanar los relojes de fin de cómputo, y la barrera colectiva `sync_for_moe_gather` (`equalize_time = true`) absorbe con precisión milimétrica el desbalance acumulado generando el bloque rojo **`NETWORK_STALL`**.
4. **Comunicaciones Colectivas No-MoE Analíticas (Línea Base Preservada):**
   Operaciones como el `AllReduce` de la atención se modelan mediante la formulación analítica de ancho de banda NVLink ($T = \text{Data} / \text{BW}$), delegando a BookSim2 el modelado de alta resolución para la dispersión y reunión MoE (`moe_scatter` y `moe_gather`).
5. **Ausencia de Backpressure sobre la GPU:**
   El simulador asume colas de software de red sin desbordamiento. Los flits son retenidos en BookSim2 en las colas de inyección sin aplicar contrapresión física bloqueante hacia los registros de ejecución de la GPU.

---

## 7.2. Evaluación de Impacto en la Precisión Científica

Gracias a las innovaciones de fidelidad física introducidas en el **Bloque C**:
- Se reproduce con total fidelidad la asincronía natural de los clústeres heterogéneos y la dispersión All-to-All desbalanceada.
- Se cuantifica empíricamente el beneficio de solapamiento de cómputo en GPUs ligeras que reciben menos tokens.
- Se capturan las burbujas reales de sincronización (`NETWORK_STALL`) en las barreras colectivas, permitiendo evaluar el coste exacto de la heterogeneidad de cómputo y de tráfico en la red de interconexión.
- Se mantiene una congruencia temporal perfecta: la suma de Cómputo + Tránsito de Red + Bloqueos Stalls coincide hasta el último decimal de nanosegundo con el Wall-Clock Time de la simulación.

---

## 7.3. Hoja de Ruta y Roadmap de Extensiones Futuras

1. **[COMPLETADO - Bloque C] Vectorización de Latencias Receptora por Receptora:**
   Implementado en `BookSimCoSimManager::cached_latency_per_gpu` y verificado en Mixtral 8x7B.
2. **[COMPLETADO - Bloque C] Desfase Causal de Inyección ($\Delta t_{\text{src}}$):**
   Implementado en `packets_by_cycle` dentro de `MoEScatter::forward()` y `MoEGather::forward()`.
3. **Soporte Jerárquico Multi-Nodo (NVLink + InfiniBand):**
   Integrar una red de dos niveles en BookSim2: enlaces de ultra-alto ancho de banda ($900\text{ GB/s}$) intra-nodo y enlaces de red de área de sistema ($100\text{ GB/s}$) inter-nodo.
4. **Modelado de Capacidad Finita de Buffers NIC:**
   Introducir un límite estricto de paquetes en las colas del host para simular caídas de rendimiento por contrapresión física hacia los hilos de la GPU.

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
- **Punto Crítico de Integración (Bloque C):** Aloja el singleton `BookSimCoSimManager`. En `forward()` de `MoEScatter` y `MoEGather`, GPU 0 calcula los instantes reales de llegada $t_{\text{src}}[s]$ y el desfase de inyección $\Delta t_{\text{src}}[s] = \text{round}(t_{\text{src}}[s] - t_{\min})$. Organiza los paquetes en `packets_by_cycle` para inyectarlos en BookSim2 exactamente cuando `cycles == delta_t[src]`. Registra el ciclo de llegada individual del último paquete para cada GPU en `cached_latency_per_gpu[layer_name][dst]`. Cada GPU suma únicamente su latencia neta individual a su reloj local `device_time`. Incorpora guarda de `perform_execution` en `AllReduce::forward()`.

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
  - Habilitación por defecto de la instrumentación de paquetes (`SIM_DEBUG_PIDS="1"`), interceptando las líneas `[TRACK_PID]` para generar `packet_tracking_debug.csv` (17 columnas) sin requerir parámetros manuales adicionales.
  - Soporte para bandera `--no_debug_pids` para anular la captura en barridos masivos donde se desee máxima velocidad.

### [`LLMSimulator/analyze_traces.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/analyze_traces.py)
- **Propósito:** Analizador macroscópico de trazas. Parsea los registros `.trc` de cada GPU, calcula promedios de latencia por tipo de capa y genera tablas resumen de tiempos de cómputo vs. comunicación.
- **Mecanismos Clave:**
  - Resolución dual robusta del directorio base (`resolve_base_dir()`), operable tanto desde la raíz del TFM como desde `LLMSimulator/`.
  - **Filtro Anti-Appends Temporal:** Detecta caídas en la serie cronológica (`START_NS.diff() < 0`) para aislar la última iteración en simulaciones multi-iteración (`iter > 1`), eliminando inflaciones artificiales de tiempo acumulado.
  - Normalización exacta de Wall-Clock Time por dispositivo, balanceo estricto Cómputo + Red + Stalls y exportación gráfica de alta definición (`anatomia_latencia.png`, `desglose_primitivas_moe.png`).

### [`LLMSimulator/plot_packet_tracking.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_packet_tracking.py)
- **Propósito:** Visualizador gráfico del tráfico en la red BookSim2. Reconstruye el ciclo de vida de los paquetes, descompone latencias ($ctime \to itime \to atime$), calcula productividad acumulada y segmenta la visualización por páginas de 50 paquetes en la subcarpeta `gantt/`.
- **Mecanismos Clave:**
  - **Doble Eje X de Congruencia Temporal:** Muestra ciclos de BookSim2 en el eje inferior y nanosegundos globales del LLM en el eje superior ($Global\_NS = Op\_Start\_NS + (Cycle - Op\_Start\_Cycle)$).
  - Filtro automático de última iteración mediante detección de retroceso temporal en `Op_Start_NS` (anulable con `--all_iters`).
  - Paginación dinámica en subcarpeta `gantt/` (`--samples 50`, `--max_pages 30`), con sombreado de franjas por operación (`Scatter` vs. `Gather`), líneas divisorias y badges laterales con marcas de tiempo en nanosegundos.
  - Renderizado de etiquetas enriquecidas por paquete: `S{src}→D{dst} (9 flits / 288B) | Lat.Mitja: {avg_flit_lat:.1f}c | Prod: {prod:.3f} flits/c | NS: {g_start:.0f}-{g_end:.0f}`.

### [`LLMSimulator/plot_cronograma.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_cronograma.py)
- **Propósito:** Generador de cronogramas causales de alta resolución (Diagramas de Gantt cycle-to-cycle). Reconstruye la ejecución concurrente de todas las GPUs con granularidad de ciclo y nanosegundo, exportando secuencias de imágenes de alta fidelidad en `cycle-to-cycle/timeline_part_*.png`.
- **Mecanismos Clave:**
  - **Aislamiento Estricto por Capa:** Extrae el identificador de capa (`MoE_decoder_X` / `decoder_X`) y prohíbe taxativamente la fusión entre operaciones de capas decodificadoras distintas.
  - **Identificación de Operaciones Elementales y Multi-Experto:** Reconstruye la secuencia ordenada de pasos elementales (`(LN + QKV_Proj + AttnGen + O_Proj + Res + Gate)`) y desglosa los expertos locales asignados a la GPU, identificando ejecuciones multi-experto secuenciales (`(Exp#0,1: 2x[Gate+SiLU+Up+Down])`) cuando $N_{\text{GPUs}} < E$.
  - **Sub-divisiones Físicas Internas:** Dibuja líneas discontinuas blancas (`alpha=0.6, linestyle='--'`) en las marcas exactas `END_NS` de cada micro-operación interna dentro del macro-bloque verde.
  - **Diagnóstico Cuantitativo de Cuello de Botella:** Calcula el ratio $\sum Mem\_ns / (\sum Comp\_ns + \sum Mem\_ns)$ y despliega en la tercera línea del bloque el veredicto arquitectural (`Mem-Bound XX.X%` vs. `Compute-Bound XX.X%`).
  - **Enriquecimiento de Red:** Cruza datos con `packet_tracking_debug.csv` mostrando en los bloques azules la capa, PIDs, número de paquetes, latencia media de flits y productividad en flits/ciclo.
  - **Coalescencia Causal Global:** Procesa toda la traza de cada GPU de forma previa a la partición en ventanas para garantizar que las operaciones que cruzan fronteras de visualización mantengan íntegro su contexto analítico.

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

*Fin del Documento Maestro - TFM Technical Bible (Octubre 2026)*

