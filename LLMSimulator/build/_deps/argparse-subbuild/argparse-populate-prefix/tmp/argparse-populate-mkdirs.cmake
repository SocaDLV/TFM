# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "/home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/ramulator2/ext/argparse")
  file(MAKE_DIRECTORY "/home/igilolt/Escritorio/TFM/LLMSimulator/src/dram/ramulator2/ext/argparse")
endif()
file(MAKE_DIRECTORY
  "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-build"
  "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-subbuild/argparse-populate-prefix"
  "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-subbuild/argparse-populate-prefix/tmp"
  "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-subbuild/argparse-populate-prefix/src/argparse-populate-stamp"
  "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-subbuild/argparse-populate-prefix/src"
  "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-subbuild/argparse-populate-prefix/src/argparse-populate-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-subbuild/argparse-populate-prefix/src/argparse-populate-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/home/igilolt/Escritorio/TFM/LLMSimulator/build/_deps/argparse-subbuild/argparse-populate-prefix/src/argparse-populate-stamp${cfgdir}") # cfgdir has leading slash
endif()
