# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Set the environment variable for the configuration file
ENV CONFIG_FILE=config.toml

# Expose the port for the web server
EXPOSE 5000

# Define the command to run the app when the container starts
CMD ["python", "app.py"]
