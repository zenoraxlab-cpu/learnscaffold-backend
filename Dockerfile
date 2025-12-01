# Base image with Python
FROM python:3.11-slim

# Install system dependencies: Tesseract and Poppler
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Work directory inside the container
WORKDIR /app

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Render passes PORT as env; we default to 10000
ENV PORT=10000

# Start FastAPI with uvicorn
# Если у тебя app = FastAPI(...) в app/main.py, оставь строку как есть.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
