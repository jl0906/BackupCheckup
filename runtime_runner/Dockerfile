ARG BUILD_FROM=ghcr.io/home-assistant/home-assistant:stable
FROM ${BUILD_FROM}

ARG BUILD_VERSION=3.0.0
ARG BUILD_ARCH

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

USER root

RUN apk add --no-cache iproute2 util-linux

COPY rootfs /

RUN chmod 0755 /opt/backup-checkup-runner/run.sh

CMD ["/opt/backup-checkup-runner/run.sh"]
