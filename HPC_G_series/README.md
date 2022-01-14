# hitachi_prometheus_exporter
Hitachi prometheus exporter - G node
 - To build the image: docker build -t <image_name> . (For example: docker build -t gseries .)
 - To start docker container (Note: map the "config.yml" to change the default config): docker run --name <container_name> --rm -p 8000:8000 -d <image_name>
 # E.g. docker run --name gseries_container --rm -p 8000:8000 -d gseries
