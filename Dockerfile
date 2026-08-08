FROM python:3.9-slim

# Install system dependencies required for face_recognition (dlib) and OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set environment variable to limit cmake RAM usage during dlib build
ENV CMAKE_BUILD_PARALLEL_LEVEL=1

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Start the Flask app using Gunicorn
CMD gunicorn web_app:app --bind 0.0.0.0:${PORT:-10000}
