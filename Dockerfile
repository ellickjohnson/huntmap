FROM python:3.12-slim
WORKDIR /app
COPY api/server.py /app/server.py
COPY web/ /app/web/
COPY db/hunt.db /app/db/hunt.db
ENV HUNTMAP_PORT=8086
EXPOSE 8086
# HUNTMAP_ADMIN_EMAIL + HUNTMAP_ADMIN_PASSWORD bootstrap the first admin at startup
# HUNTMAP_BASE_URL is used in verification-email links (default https://huntmap.ellickjohnson.net)
CMD ["python3", "server.py"]