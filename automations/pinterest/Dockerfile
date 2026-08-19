# Pinterest Automation
FROM base AS pinterest

# Install additional system dependencies for Pinterest
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    libxrender1 \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgtk-3.0 \
    libgbm1 \
    libasound2 \
    libxss1 \
    libxtst6 \
    libxrandr2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Copy service-specific requirements
COPY automations/pinterest/requirements.txt /tmp/requirements-service.txt
RUN pip install --no-cache-dir -r /tmp/requirements-service.txt

# Copy application code
COPY automations/pinterest /app

# Copy shared browser module
COPY automations/browser.py /app/browser.py

# Create necessary directories
RUN mkdir -p output logs .sessions

# Default command
CMD ["python", "main.py", "run"]