find_package(AWSSDK CONFIG COMPONENTS core dynamodb kinesis s3 REQUIRED)
target_include_directories(main PRIVATE ${AWSSDK_INCLUDE_DIRS})
target_link_libraries(main PRIVATE ${AWSSDK_LIBRARIES})