# syntax=docker/dockerfile:1
FROM debian:trixie-slim

ARG DEBIAN_FRONTEND=noninteractive

LABEL org.opencontainers.image.title="dss libreoffice-writer" \
    org.opencontainers.image.description="Headless LibreOffice Writer UNO runtime with Vietnamese language support" \
    org.opencontainers.image.source="https://github.com/tranthethang/docker-shared-services"

# LibreOffice Writer + UNO bridge for the system Python. No application code:
# projects mount or build their own code on top of this runtime.
# Vietnamese support: UTF-8 locale, Vietnamese UI/l10n, spell-check dictionary,
# and fonts with full Vietnamese glyph coverage (Liberation, DejaVu, Noto).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        libreoffice-l10n-vi \
        hunspell-vi \
        python3 \
        python3-uno \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-core \
        tini

RUN useradd -m -u 1000 app && mkdir /data && chown app:app /data

COPY --chmod=755 --chown=app:app entrypoint.sh /entrypoint.sh

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    UNO_HOST=0.0.0.0 \
    UNO_PORT=2002

USER app
WORKDIR /data
EXPOSE 2002
VOLUME /data
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
