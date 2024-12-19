# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server script into /app
COPY server.py /app

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run server.py when the container launches
CMD ["python", "server.py"]