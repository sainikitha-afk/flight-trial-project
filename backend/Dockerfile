# Use official Python image
FROM python:3.10-slim

# Set working directory in the container
WORKDIR /app

# Copy requirements file into container
COPY requirements.txt .

# Install dependencies
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
