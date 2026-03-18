FROM python:3.14-slim
WORKDIR /app
COPY . .
RUN pip install .
ENV DB_PATH=/data/asoul.db
VOLUME /data
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
