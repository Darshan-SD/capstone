# ---- Base image with Python ----
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies (Node.js and npm for Tailwind)
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies ----
# Create and activate virtual environment
ENV VIRTUAL_ENV=/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---- Tailwind Setup ----
# Install Tailwind and PostCSS
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy app files
COPY . .

# Build Tailwind CSS
# Input file assumed: src/input.css -> static/css/style.css
RUN npx tailwindcss -i ./static/css/style.css -o ./static/dist/output.css --minify

# ---- Runtime configuration ----
# Expose port (adjust if your app uses a different one)
EXPOSE 5000

# Populate the database when container builds (optional, or do at runtime)
# If you want it at runtime instead, remove this line and add to entrypoint
RUN python populate_database.py || true

# ---- Entry point ----
# Gunicorn for production (can switch to flask run for dev)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
