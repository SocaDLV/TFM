CMAKE_MINIMUM_REQUIRED (VERSION 3.14)

PROJECT (llm_system)


add_library(llm_system SHARED)
add_compile_options(-fPIC)


include_directories(src)
include_directories(src/dram/ramulator2/src)
add_subdirectory(src)
add_subdirectory(eval)

# TFM: Importar BookSim2 (co-simulación)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../booksim2 ${CMAKE_CURRENT_BINARY_DIR}/booksim2_build)

target_link_libraries(
    llm_system
    PRIVATE hardware
    PRIVATE -Wl,--whole-archive dram -Wl,--no-whole-archive 
    #PRIVATE dram
    PRIVATE module
    PRIVATE model
    PRIVATE scheduler
    # TFM: Añadimos booksim2
    booksim2
)

set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR})

configure_file(dram_config_HBM3_80GB.yaml ${EXECUTABLE_OUTPUT_PATH}/dram_config_HBM3_80GB.yaml COPYONLY)
configure_file(dram_config_HBM3E_192GB.yaml ${EXECUTABLE_OUTPUT_PATH}/dram_config_HBM3E_192GB.yaml COPYONLY)
configure_file(config.yaml ${EXECUTABLE_OUTPUT_PATH}/config.yaml COPYONLY)

# TFM: Copiar automáticamente la configuración de BookSim2
configure_file(test.cfg ${EXECUTABLE_OUTPUT_PATH}/test.cfg COPYONLY)
