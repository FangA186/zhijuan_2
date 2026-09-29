FROM python:3.12-slim
ARG HERMES_REVISION
LABEL org.opencontainers.image.revision=$HERMES_REVISION
WORKDIR /opt/hermes
COPY vendor/hermes-agent/ /opt/hermes/
RUN --mount=type=cache,target=/root/.cache/pip pip install -e . && useradd --uid 10001 --create-home solver && mkdir /state /work && chown solver:solver /state /work
RUN --mount=type=cache,target=/root/.cache/pip pip install aiohttp==3.14.3
COPY infra/hermes-solver/config.yaml /etc/hermes-solver/config.yaml
COPY infra/hermes-solver/start.sh /usr/local/bin/start-hermes-solver
RUN chmod 755 /usr/local/bin/start-hermes-solver
USER solver
WORKDIR /work
CMD ["/usr/local/bin/start-hermes-solver"]
