# HPC_S_series
Hitachi prometheus exporter - S node
 - To build the image: docker build -t <image_name> . (For example: docker build -t sseries .)
 - To start docker container (Note: map the "config.yml" to change the default config): docker run --name <container_name> --rm -p 8000:8000 -d <image_name>
 # E.g. docker run --name sseries_container --rm -p 8000:8000 -d sseries
