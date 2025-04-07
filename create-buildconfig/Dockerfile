# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

# Download AMS CLI
RUN apt-get update && apt-get install -y curl && \
    curl -o /app/ams-cli https://cdn.prod.ams.accelbyte.io/linux_amd64/ams && \
    chmod +x /app/ams-cli

# Copy the server script into /app
COPY upload_and_create_buildconfig.py /app

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run server.py when the container launches
CMD ["python", "upload_and_create_buildconfig.py"]