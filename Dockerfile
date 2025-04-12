# Use the official Python 3.12 image to build the app
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file and install Python dependencies
COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    poppler-utils \
    libglib2.0-0 \
    libcairo2 \
    libpango1.0-0 \
    libgdk-pixbuf2.0-0 \
    libjpeg-dev \
    libffi-dev \
    tesseract-ocr

RUN pip install --no-cache-dir --upgrade pip setuptools
RUN pip install -r requirements.txt

# Copy the entire app to the container
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Run the Flask app
CMD ["python", "Api.py"]

