#!/usr/bin/env bash
# ==============================================================================
# LLM-NoC Co-Simulation Workbench — Lanzador de Interfaz Web Local (Linux)
# LLMSimulator + BookSim2 Cycle-Accurate Framework
# ==============================================================================

set -e

# Posicionarse en el directorio raíz de LLMSimulator donde reside este script
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "========================================================================"
echo "   🧠 LLM-NoC Co-Simulation Workbench (GUI)"
echo "   🔬 Entorno de Co-Simulación LLMSimulator + BookSim2"
echo "========================================================================"

# 1. Comprobación del intérprete Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ [ERROR] No se ha encontrado 'python3' en el sistema."
    echo "   Por favor, instala Python 3 (versión 3.9 o superior recomendada)."
    exit 1
fi

# 2. Verificación de dependencias científicas requeridas (pandas, numpy, matplotlib)
MISSING_PKGS=()
for pkg in pandas numpy matplotlib; do
    if ! python3 -c "import $pkg" &>/dev/null; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo "❌ [ERROR] Faltan librerías Python esenciales: ${MISSING_PKGS[*]}"
    echo "   Instálalas en tu entorno activo ejecutando:"
    echo "   pip install ${MISSING_PKGS[*]}"
    exit 1
fi

# 3. Comprobación de compilación del simulador C++ (./build/run)
if [ ! -f "./build/run" ]; then
    echo "❌ [ERROR] No se ha encontrado el binario ejecutable './build/run'."
    echo "   Por favor, compila el motor C++ del simulador antes de iniciar la GUI:"
    echo "   ------------------------------------------------------------------"
    echo "   cmake -B build"
    echo "   cmake --build build -j\$(nproc)"
    echo "   ------------------------------------------------------------------"
    exit 1
fi

# 4. Higiene y limpieza de staging temporal
if [ -d "build/tmp_staging" ]; then
    # Eliminar carpetas vacías huérfanas en staging
    find build/tmp_staging -mindepth 1 -maxdepth 1 -type d -empty -delete 2>/dev/null || true
fi

# 5. Información de acceso y arranque
DEFAULT_PORT=8080
PORT_ARG="$DEFAULT_PORT"

# Extraer puerto si el usuario especificó --port <p> o --port=<p> sin mutar "$@"
prev_was_port=false
for arg in "$@"; do
    if [ "$prev_was_port" = true ]; then
        PORT_ARG="$arg"
        prev_was_port=false
    elif [ "$arg" = "--port" ]; then
        prev_was_port=true
    elif [[ "$arg" == --port=* ]]; then
        PORT_ARG="${arg#*=}"
    fi
done

echo "   🚀 Servidor web listo en: http://127.0.0.1:${PORT_ARG}"
echo "   💡 Argumentos soportados:"
echo "      --port <N>      Cambiar puerto HTTP (por defecto: 8080)"
echo "      --no-browser    No abrir automáticamente el navegador web"
echo "========================================================================"

# 6. Transferencia de control al lanzador Python
exec python3 launch_gui.py "$@"
