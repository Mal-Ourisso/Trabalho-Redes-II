FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 \
    tshark \
    tcpdump \
    iproute2 \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app