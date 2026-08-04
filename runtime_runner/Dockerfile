ARG BUILD_FROM=ghcr.io/home-assistant/home-assistant:stable
FROM ${BUILD_FROM}

ARG BUILD_VERSION=3.0.8
ARG BUILD_ARCH

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

# Namespace creation requires NET_ADMIN/SYS_ADMIN and root inside this protected
# app container. No host network, Docker socket, or production config is mounted.
USER root

RUN apk add --no-cache iproute2 openssl util-linux

COPY rootfs /

RUN chmod 0755 /opt/backup-checkup-runner/run.sh

CMD ["/opt/backup-checkup-runner/run.sh"]
