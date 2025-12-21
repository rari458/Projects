# Use an official Python runtime as a parent image (Slim version for smaller size)
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for some python packages like ta-lib or build tools)
# We install 'gcc' and 'g++' just in case pandas-ta needs compilation
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir helps keep the image size down
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install pandas-ta

# Copy the rest of the application code
COPY . .

# Run main.py when the container launches
CMD ["python", "main.py"]
