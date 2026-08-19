# Job Automation - Multi-portal job application bot
FROM base AS job-automation

# Copy service-specific requirements
COPY automations/job-automation/requirements.txt /tmp/requirements-service.txt
RUN pip install --no-cache-dir -r /tmp/requirements-service.txt

# Copy application code
COPY automations/job-automation /app

# Create sessions directory
RUN mkdir -p .sessions output/logs

# Make run.py executable
RUN chmod +x run.py

# Default command
CMD ["python", "run.py"]