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
   - 3.5. Diseño del Wrapper C++ `booksim_api` y Desacoplamiento de `main.cpp`
   - 3.6. Topologías de Red en BookSim2: Construcción de Mallas y Toros (`booksim2/src/networks/kncube.cpp`)
   - 3.7. Microarquitectura del Router Virtual-Channel y Prevención de Deadlock (`booksim2/src/routers/iq_router.cpp`, `routefunc.cpp`, `buffer_state.cpp`, `allocator/`)
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
   - 6.5. Visualizador de Congestión en Red (`plot_packet_tracking.py`)
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

## 3.5. Diseño del Wrapper C++ `booksim_api` y Desacoplamiento de `main.cpp`

Para integrar BookSim2 como librería dinámica/estática en `LLMSimulator` sin colisiones de enlace:
1. Se aislaron las variables globales de BookSim2 (`gPrintActivity`, `gK`, `gN`, etc.) en [`booksim2/src/booksim_api.cpp:L15-L22`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp#L15-L22), evitando enlazar con el `main.cpp` original de BookSim2.
2. Se implementó la clase derivada `API_TrafficManager` que hereda de `TrafficManager`:
   - Sobrescribe `_RetireFlit()` para capturar métricas sin alterar las estadísticas internas de BookSim2.
   - Encola las estructuras `BookSimPacketInfo` en la cola `arrived_packets`.
   - Si la variable de entorno `SIM_DEBUG_PIDS=1` está activa, emite la traza estructurada `[TRACK_PID]` hacia `stdout`.
3. Se expuso una API pura en C en [`booksim2/src/booksim_api.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.hpp):
   - `BookSim_Initialize(const char* config_file)`
   - `BookSim_InjectPacket(int src, int dst, int size_in_flits)`
   - `BookSim_AdvanceCycle()`
   - `BookSim_CheckReceived(BookSimPacketInfo& info)`

---

## 3.6. Topologías de Red en BookSim2: Construcción de Mallas y Toros (`booksim2/src/networks/kncube.cpp`)

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

## 3.7. Microarquitectura del Router Virtual-Channel y Prevención de Deadlock (`booksim2/src/routers/iq_router.cpp`, `routefunc.cpp`, `buffer_state.cpp`, `allocator/`)

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

## 4.1. El Paradigma de Integración Oráculo en Modo Bulk Synchronous Parallel (BSP)

La integración entre LLMSimulator y BookSim2 implementa un **modelo Oráculo centralizado de predicción causal**:

Cuando el clúster alcanza una fase de comunicación colectiva en `MoEScatter` o `MoEGather` ([`src/module/communication.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/communication.cpp)):
1. La primera GPU en alcanzar el módulo (GPU 0) detecta que `BookSimCoSimManager::calls_per_module[layer_name] == 0`.
2. Como GPU 0 tiene acceso a la estructura global del planificador (`sequences_metadata->scheduler`), predice exhaustivamente la matriz completa de tráfico de todos los pares $(src, dst)$ del clúster.
3. Inyecta todos los paquetes correspondientes en BookSim2 y ejecuta el bucle de reloj `BookSim_AdvanceCycle()` hasta que todos los paquetes inyectados son recibidos.
4. Almacena la latencia resultante en nanosegundos en `BookSimCoSimManager::cached_latency[layer_name]`.
5. Todas las GPUs (incluidas las que alcancen la fase posteriormente) leen esta latencia cacheada y avanzan sus relojes en consecuencia.
6. La última GPU en procesar el módulo resetea los contadores del Oráculo, garantizando que la siguiente iteración comience con un estado completamente limpio.

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

## 4.4. Secuencia Causal de Barreras en la Capa MoE: De Attention a MoEGather

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
    3. MoEScatter (sync=true) ◄─── BARRERA GLOBAL PREVIA (sync_devices)
              │                    GPU 0 ejecuta el Oráculo BookSim2 (~3.9 us)
              ▼
    4. sync_for_moe_scatter (sync=false)
              │
              ▼
    5. ExpertFFN (~22.1 us) ────── Ejecución Local de los Expertos (Memory-Bound)
              │
              ▼
    6. sync_2 (sync=false)
              │
              ▼
    7. all_reduce_for_e_tp
              │
              ▼
    8. sync_3 (sync=true) ◄─────── BARRERA GLOBAL DE COMPILACIÓN (sync_devices)
              │                    Las GPUs esperan a la más lenta en computar FFN
              ▼
    9. MoEGather (sync=false) ◄─── Oráculo BookSim2 ejecutado por GPU 0 (~4.5 us)
              │
              ▼
   10. sync_for_moe_gather (sync=false)
              │
              ▼
   11. Residual + Siguiente Capa
```

### Análisis Detallado de los Flags `sync`:
- **`MoEScatter` (`sync = true`):** Obliga a que todas las GPUs sincronicen sus relojes al valor máximo antes de que se inicie la dispersión de red. Cuando GPU 0 entra a ejecutar el Oráculo de BookSim2, **los relojes de todas las GPUs ya han sido igualados previamente en `sync_devices()`**.
- **`sync_3` (`sync = true`):** Situado inmediatamente antes de `MoEGather`. Obliga a que ninguna GPU comience a recopilar resultados de expertos remotos hasta que la GPU más lenta haya terminado de procesar su `ExpertFFN`. Es aquí donde se absorben las diferencias de nanosegundos del cómputo local mediante eventos `NETWORK_STALL`.
- **`MoEGather` (`sync = false`):** No requiere barrera previa directa porque `sync_3` ya garantizó la sincronización global del clúster instantes antes.

---

## 4.5. Auditoría Crítica de `cached_latency[layer_name]`: Escalar Global vs. Vector por GPU Destino

### El Mecanismo Actual y su Limitación
Actualmente, el código de `communication.cpp` finaliza la simulación de BookSim2 con:

```cpp
while(BookSimCoSimManager::total_received < BookSimCoSimManager::total_injected) {
    BookSim_AdvanceCycle();
    cycles++;
    while(BookSim_CheckReceived(pkt_info)) { 
        BookSimCoSimManager::total_received++;
    }
}
BookSimCoSimManager::cached_latency[layer_name] = cycles * 1.0;
```

El valor `cycles` devuelto representa el ciclo de llegada del **último paquete de toda la red**. Este valor es almacenado como un escalar único y asignado por igual a todas las 8 GPUs:

$$\text{network\_latency\_ns}(\text{GPU}_i) = \text{cached\_latency}[layer\_name] = \max_{p \in \text{Paquetes}} (atime_p) \quad \forall i \in [0, 7]$$

### Efecto en el Cronograma Actual
Todas las GPUs dibujan una barra azul de comunicación de exactamente la misma longitud (ej. 3.933 ns en Scatter, 3.962 ns en Gather), comenzando y terminando al mismo tiempo.

### Análisis Teórico: ¿Qué Ocurriría si Usamos `max_atime_per_dst[dst]`?
Si modificamos el Oráculo para registrar el ciclo máximo de llegada individual para cada GPU receptora:

$$\text{latency\_per\_dst}[dst] = \max_{p \in \text{Paquetes},\, p.dest == dst} (atime_p)$$

1. **Variación en la Llegada de Red:**
   - Una GPU situada a solo 1 salto de red o que recibe menos tokens (ej. GPU 7 con 4 tokens) terminaría de recibir sus datos mucho antes (ej. ciclo 1200 en vez de 3933).
   - Su barra azul de comunicación sería considerablemente más corta.
2. **Impacto en el Cómputo de `ExpertFFN`:**
   - La GPU 7 podría comenzar su cómputo de `ExpertFFN` de inmediato (en el ciclo 1200).
   - Como su FFN dura ~22.155 ns, terminaría su cómputo aproximadamente en el ciclo 23.355 ns.
3. **El Destino Inevitable en `sync_3`:**
   - Sin embargo, antes de `MoEGather`, el grafo impone la barrera `sync_3 (sync = true)`.
   - La GPU más rezagada en la red (GPU 0 o GPU 5, que recibieron 11 tokens) termina su comunicación en el ciclo 3.933 ns y su FFN en el ciclo 26.088 ns.
   - **En `sync_3`, la GPU 7 sufriría un `NETWORK_STALL` idéntico a la diferencia temporal ganada**:
     $$\text{STALL}_{\text{GPU 7}} = 26,088\text{ ns} - 23,355\text{ ns} = \mathbf{2,733 \text{ ns}}$$
4. **Conclusión:** La latencia total de la capa no variaría, pero el cronograma mostraría un comportamiento micro-arquitectural asimétrico y mucho más realista: finalizaciones escalonadas de red, solapamiento parcial de cómputo en GPUs ligeras y grandes bloques rojos de `NETWORK_STALL` en las GPUs que esperan en `sync_3`.

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
   Utiliza `std::endl` para vaciar el búfer del sistema operativo de inmediato, protegiendo los datos contra interrupciones anormales del simulador.
3. **Filtrado de Eventos Nulos:** En [`src/module/module_graph.cpp:L332`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp#L332), solo se registran eventos con `exec_status.total_duration > 0`, eliminando del archivo miles de llamadas declarativas nulas que saturaban el almacenamiento.

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
- Si se pasa `--debug_pids`, intercepta mediante pipes de subproceso las líneas que comienzan por `[TRACK_PID]` emitidas por BookSim2 y las vuelca estructuradas a `packet_tracking_debug.csv`.
- Sella y organiza los archivos generados en subdirectorios únicos por marca temporal en `build/results/<experimento>/`.

---

## 6.4. Análisis Macroscópico de Latencias (`analyze_traces.py`)

Ubicado en [`LLMSimulator/analyze_traces.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/analyze_traces.py):
- Analiza las ejecuciones más recientes (`--recent N`, `--model`, `--today`).
- Extrae de los `.trc` el desglose acumulado de:
  - **Cómputo GPU Puro:** Suma de todas las duraciones de capas tensoriales (`Linear`, `Attention`, normalizaciones).
  - **Tránsito de Red:** Tiempo de vuelo físico en BookSim2 (`moe_scatter` y `moe_gather`).
  - **Bloqueos de Sincronización:** Tiempo ocioso en barreras BSP (`NETWORK_STALL`).
- Genera automáticamente en `build/analysis/`:
  - `anatomia_latencia.png`: Gráfico de barras apiladas comparativas.
  - `desglose_primitivas_moe.png`: Comparativa del coste de `moe_scatter` frente a `moe_gather`.

---

## 6.5. Visualizador de Congestión en Red (`plot_packet_tracking.py`)

Ubicado en [`LLMSimulator/plot_packet_tracking.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_packet_tracking.py):
- Parsea `packet_tracking_debug.csv` y genera diagramas de Gantt de la vida de los paquetes con barras horizontales compuestas de dos colores:
  - 🟧 **Espera en Cola del NIC (Queueing Delay):** Desde $ctime$ hasta $itime$.
  - 🟦 **Vuelo en Red (NoC Flight Time):** Desde $itime$ hasta $atime$.
- Anota cada barra individual con su metadato de tráfico: `S{src}→D{dst} (9 flits / 288 B)`.
- Genera tres ventanas clave:
  - `gantt_1_fase_libre.png`: Fase inicial con red vacía.
  - `gantt_2_congestion_media.png`: Primeros paquetes en superar 1.500 ciclos (aparición del efecto escalera en cola).
  - `gantt_3_congestion_critica.png`: Paquetes que superan 2.000 ciclos durante el cuello de botella masivo All-to-All.

---

## 6.6. Cronograma Micro-Arquitectural Causal GPU Cycle-to-Cycle (`plot_cronograma.py`)

Ubicado en [`LLMSimulator/plot_cronograma.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_cronograma.py):
- Genera cortes temporales de alta resolución (ej. ventanas de 10.000 ns a 100.000 ns) en `cycle-to-cycle/`.
- **Clasificación Semántica y Coalescencia Algorítmica:**
  Inspecciona `TYPE` y `DETAILS` (`Module:`). Fusiona automáticamente micropasos consecutivos de una misma operación lógica (ej. `gate_proj`, `activation`, `up_proj`, `down_proj` se consolidan como un único bloque continuo de **ExpertFFN**).
- **Renderizado Dual en Cómputo Verde:**
  Dibuja en la parte superior del bloque `"Calc"` y en la parte inferior el nombre de la macro-operación real (**ExpertFFN**, **Attention**, **Linear**, etc.) en texto **blanco en negrita** (`fontweight='bold'`).
- **Filtro Anti-Appends:** Detecta caídas en la serie temporal (`diff < 0`), garantizando que si una simulación concatenó datos antiguos en el archivo `.trc`, el visualizador extrae de forma limpia y exclusiva la última ejecución realizada.

---

# CAPÍTULO 7: Amenazas a la Validez, Limitaciones Actuales y Hoja de Ruta de Mejoras

Para mantener el máximo rigor científico en esta investigación de Máster, se declaran de manera transparente las simplificaciones y limitaciones presentes en el entorno de co-simulación actual.

## 7.1. Simplificaciones Asumidas en el Co-Simulador Actual

1. **Latencia de Red como Escalar Global en el Oráculo:**
   El Oráculo actual computa el ciclo de llegada del último paquete global de la red y aplica ese escalar uniforme a todas las GPUs. Como se analizó en la Sección 4.5, en una red física real las GPUs destino más cercanas o con menor carga terminan de recibir sus paquetes antes.
2. **Desacoplamiento Temporal de la Inyección:**
   Cuando la GPU 0 invoca a BookSim2, inyecta todos los paquetes del clúster con $ctime = 0$ relativo al inicio de la fase de red. En una ejecución física real, si una GPU termina su capa de atención $100\text{ ns}$ antes que otra, comenzaría a inyectar sus paquetes en la red antes, alterando los patrones de contención temporal.
3. **Comunicaciones Colectivas No-MoE Analíticas:**
   Operaciones como el `AllReduce` de la atención o los gradientes en entrenamiento se modelan mediante la fórmula estática de ancho de banda NVLink ($T = \text{Data} / \text{BW}$), delegando a BookSim2 únicamente las operaciones de dispersión y reunión MoE (`moe_scatter` y `moe_gather`).
4. **Ausencia de Backpressure sobre la GPU:**
   El simulador asume que las colas de software del NIC tienen capacidad infinita. En hardware real, si la red se colapsa, los buffers del NIC se llenan y aplican *backpressure* sobre los procesadores de la GPU, bloqueando el avance de las instrucciones de emisión.

---

## 7.2. Evaluación de Impacto en la Precisión Científica

A pesar de estas simplificaciones, el co-simulador proporciona una fidelidad inmensamente superior a los modelos analíticos convencionales:
- Captura la saturación física real de los canales virtuales ante ráfagas All-to-All.
- Identifica los cuellos de botella por arbitraje y enrutamiento en topologías restringidas (Torus vs. Mesh).
- Modela con exactitud matemática el régimen memory-bound de los expertos MoE y cuantifica los bloqueos de sincronización BSP reales en las barreras de clúster.

---

## 7.3. Hoja de Ruta y Roadmap de Extensiones Futuras

Para evolucionar el co-simulador hacia una plataforma de publicación doctoral o industrial:

1. **Vectorización de Latencias Receptora por Receptora:**
   Modificar `BookSimCoSimManager::cached_latency` para que sea un `std::vector<time_ns> latency_per_dst(total_num_device)` indexado por GPU receptora, permitiendo a las GPUs con menos tokens finalizar su recepción de red antes y comenzar su cómputo de manera asíncrona.
2. **Co-Simulación en Lazo Cerrado con Eventos Discretos Bidireccionales:**
   Sustituir el enfoque de Oráculo de ráfaga completa por un bucle de avance conjunto paso a paso, donde cada GPU inyecte sus flits en BookSim2 exactamente en el nanosegundo en que su reloj local alcanza la instrucción de red.
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

### [`src/module/module_graph.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.h) & [`module_graph.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/module_graph.cpp)
- **Propósito:** Motor central de ejecución del grafo de dependencias estático.
- **Clases Clave:**
  - `ModuleGraph`: Grafo local por GPU. Mantiene la lista de nodos ordenados topológicamente (`topological_sort()`).
  - `TopModuleGraph`: Coordinador global que gobierna el bucle de ejecución de todas las GPUs mediante barreras `sync_devices()`, resolución de nodos PUSH/POP y avance causal de dependencias.
  - Acumula los contadores físicos de energía (`status.act_energy`, `status.mac_energy`, etc.).

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
- **Propósito:** Normalización por capas (`RMSNorm` / `LayerNorm`). Operación memory-bound analítica.

### [`src/module/residual.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/residual.h) & [`residual.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/residual.cpp)
- **Propósito:** Conexión residual que suma elemento a elemento la entrada del bloque con la salida de la atención o FFN.

### [`src/module/rope.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/rope.h) & [`rope.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/rope.cpp)
- **Propósito:** Embebido posicional rotacional (Rotary Position Embedding). Aplica rotaciones ortogonales a los vectores de Query y Key.

### [`src/module/route.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/route.h) & [`route.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/route.cpp)
- **Propósito:** Compuerta de enrutamiento MoE (Gating Network).
- **Métodos Clave:**
  - `Route::forward()`: Evalúa logits de enrutamiento, aplica softmax y selecciona los Top-$k$ expertos por token.
  - Modela distribuciones de selección sintéticas (uniforme o Zipfiana según el parámetro `skewness`) o basadas en trazas reales de dataset.

### [`src/module/expert.h`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.h) & [`expert.cpp`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/src/module/expert.cpp)
- **Propósito:** Módulo del conjunto de expertos MoE (`ExpertModule`). Ejecuta el bloque Feed-Forward Network (`SwiGLU`) para los tokens enrutados a los expertos locales alojados en la GPU.

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
- **Propósito:** Módulos de comunicación de red entre GPUs (`AllReduce`, `MoEScatter`, `MoEGather`).
- **Punto Crítico de Integración:** Aloja el singleton `BookSimCoSimManager`. En `forward()`, GPU 0 evalúa el Oráculo de red, invoca a BookSim2, inyecta paquetes unicast y cachea la latencia para todas las GPUs.

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

### [`LLMSimulator/analyze_traces.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/analyze_traces.py)
- **Propósito:** Analizador macroscópico de trazas. Parsea los registros `.trc` de cada GPU, calcula promedios de latencia por tipo de capa y genera tablas resumen de tiempos de cómputo vs. comunicación.

### [`LLMSimulator/plot_packet_tracking.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_packet_tracking.py)
- **Propósito:** Visualizador gráfico del tráfico en la red BookSim2. Genera diagramas de dispersión temporal, histogramas de latencia de paquetes ($ctime \to itime \to atime$) y análisis de contención en colas de NIC.

### [`LLMSimulator/plot_cronograma.py`](file:///home/igilolt/Escritorio/TFM/LLMSimulator/plot_cronograma.py)
- **Propósito:** Generador de cronogramas causales de alta precisión (Diagramas de Gantt cycle-to-cycle). Reconstruye la ejecución concurrente de todas las GPUs con resolución de nanosegundos, visualizando esperas por barrera, fases de cálculo y transferencias de red.

---

## 8.9. Subsistema de Red BookSim2 (`booksim2/src/`)

### [`booksim2/src/booksim_api.hpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.hpp) & [`booksim_api.cpp`](file:///home/igilolt/Escritorio/TFM/booksim2/src/booksim_api.cpp)
- **Propósito:** Wrapper y API en C++ para desacoplar BookSim2 como librería interactiva. Define `BookSim_Initialize()`, `BookSim_InjectPacket()`, `BookSim_AdvanceCycle()` y gestiona la clase `API_TrafficManager` con captura de PIDs y marcas temporales.

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

