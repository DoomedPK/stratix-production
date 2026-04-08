# Use the official, lightweight Python image
FROM python:3.12-slim

# Set environment variables for Python and Cloud Run
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed for PostgreSQL
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy your requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your Stratix Command Center code
COPY . .

# Collect static files for production
RUN python manage.py collectstatic --noinput

# Expose the port Google Cloud Run expects
EXPOSE 8080

# Command to run your production server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "core.wsgi:application"]
