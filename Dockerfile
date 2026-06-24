FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY tradenexus/ ./tradenexus/

EXPOSE 3000

CMD ["uvicorn", "tradenexus.api.app:app", "--host", "0.0.0.0", "--port", "3000"]
