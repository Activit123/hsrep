# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for compilation
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    build-essential \
    python3-rpi.gpio \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy the application files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the necessary port
EXPOSE 3070

# Define the command to run the application
CMD ["python", "rfid_reader.py"]
