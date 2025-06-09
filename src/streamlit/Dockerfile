FROM python:3.11-slim

WORKDIR /app

COPY src/streamlit/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# tell Python where to look for `src`
ENV PYTHONPATH=/app

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port", "8501", \
     "--server.headless", "true"]
