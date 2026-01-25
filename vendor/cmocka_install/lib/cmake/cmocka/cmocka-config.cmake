
####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was cmocka-config.cmake.in                            ########

get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)

####################################################################################

get_filename_component(cmocka_CMAKE_DIR "${CMAKE_CURRENT_LIST_FILE}" PATH)
if(NOT TARGET cmocka::cmocka)
	include("${cmocka_CMAKE_DIR}/cmocka-targets.cmake")
endif()

# for backwards compatibility
set(CMOCKA_LIBRARY cmocka::cmocka)
set(CMOCKA_LIBRARIES cmocka::cmocka)
