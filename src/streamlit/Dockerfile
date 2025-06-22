# Use official slim Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy and install dependencies first for caching
COPY ./src/streamlit/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into image
COPY ./src /app/src

# Expose Streamlit port
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "src/streamlit/app.py", "--server.port", "8501", "--server.headless", "true"]
