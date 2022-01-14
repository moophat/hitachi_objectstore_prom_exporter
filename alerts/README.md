# alerts_S_series
Collect the alerts from HPC and send the alerts to Prometheus alertmanager
 - To build the image: docker build -t <image_name> . (For example: docker build -t alerthpc .)
 - To start docker container (Note: map the "config.yml" to change the default config): docker run --name <container_name> --rm -d <image_name>
 # E.g. docker run --name alerthpc_container --rm -d alerthpc
