FROM python:3.12-slim
WORKDIR /srv
COPY server.py .
RUN useradd --create-home appuser
USER appuser
EXPOSE 9000
CMD ["python", "server.py"]
