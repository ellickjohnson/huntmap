FROM python:3.12-slim
WORKDIR /app
COPY api/server.py /app/server.py
COPY web/ /app/web/
COPY db/hunt.db /app/db/hunt.db
ENV HUNTMAP_PORT=8086
EXPOSE 8086
CMD ["python3", "server.py"]