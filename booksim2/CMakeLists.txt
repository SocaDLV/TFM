cmake_minimum_required(VERSION 3.10)
project(BookSim2)

# Buscar todos los archivos de C++ de BookSim2
file(GLOB_RECURSE BOOKSIM_CPP_SOURCES "src/*.cpp")

# EXCLUIR el main original de BookSim y nuestro test de la API
list(REMOVE_ITEM BOOKSIM_CPP_SOURCES 
    "${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/test.cpp"
)

# Los archivos generados por YACC/LEX son en lenguaje C puro
set(BOOKSIM_C_SOURCES 
    "src/lex.yy.c" 
    "src/y.tab.c"
)

# Crear la librería estática (nuestra nueva "API")
add_library(booksim2 STATIC ${BOOKSIM_CPP_SOURCES} ${BOOKSIM_C_SOURCES})

# Exponer los directorios de cabeceras para que LLMSimulator pueda encontrarlos
target_include_directories(booksim2 PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/src"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/allocators"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/arbiters"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/networks"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/power"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/routers"
)

# Silenciar las advertencias (warnings) de código heredado de los años 90
set_target_properties(booksim2 PROPERTIES 
    C_STANDARD 99 
    CXX_STANDARD 17 
    POSITION_INDEPENDENT_CODE ON
)
target_compile_options(booksim2 PRIVATE -w -O3)
