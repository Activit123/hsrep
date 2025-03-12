# Use the official Python image from Docker Hub
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt /app/

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . /app/

# Set environment variables for Flask (optional)
ENV FLASK_APP=rfid_reader.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=3030

# Expose the port the app will run on
EXPOSE 3030

# Create a script that will run both scripts
RUN echo '#!/bin/bash\n\
python /app/creare.py &\n\
python /app/rfid_reader.py &\n\
wait' > /app/start.sh

# Make the start script executable
RUN chmod +x /app/start.sh

# Run the start script
CMD ["/app/start.sh"]
