FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
      python3 \
      python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip3 install -U pip && pip3 install -U \
      mitmproxy \
      redis && \
    useradd -ms /bin/bash ubuntu && \
    mkdir -p /opt/majsoul-rpa && \
    chown -R ubuntu /opt/majsoul-rpa

COPY --chown=ubuntu sniffer.py /opt/majsoul-rpa

USER ubuntu

WORKDIR /opt/majsoul-rpa

ENTRYPOINT ["mitmdump", "-qs", "/opt/majsoul-rpa/sniffer.py"]
