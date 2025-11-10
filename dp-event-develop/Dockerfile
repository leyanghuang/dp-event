# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the local directory contents into the container at /app
COPY . /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install necessary Python packages from a requirements list
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "-u", "main.py"]
