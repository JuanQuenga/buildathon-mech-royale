# Mech Royale bot. Build: docker build -t mech-bot .
# Runs as uid 65534 on a read-only root (writable /tmp), 1 CPU, 512 MB, no network, map at /arena.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONHASHSEED=0
RUN pip install --no-cache-dir --disable-pip-version-check numpy==2.5.5
WORKDIR /app
COPY bot/ /app/bot/
COPY arena/ /app/arena/
# Precompile bytecode at build time: the runtime filesystem is read-only.
RUN python3 -m compileall -q /app/bot && \
    if [ -f /app/bot/build_cache.py ]; then python3 /app/bot/build_cache.py /app/arena /app/cache; fi && \
    chmod -R a+rX /app
USER 65534:65534
ENTRYPOINT ["python3", "-u", "/app/bot/main.py"]
