FROM python:3.6-slim
WORKDIR /opt/hitachi_prometheus_exporter/alerts
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . .
CMD ["python", "main.py"] 
