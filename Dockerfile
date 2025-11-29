# Use Python 3.11 slim image (stable for Playwright/Agno)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for building python packages and playwright
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
# We set the path to a location accessible by the non-root user or install globally
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir /ms-playwright && \
    playwright install --with-deps chromium && \
    chmod -R 777 /ms-playwright

# Create a non-root user for security (HF Spaces requirement)
RUN useradd -m -u 1000 user

# Copy application code and set ownership
COPY --chown=user:user . .

# Switch to non-root user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose port 7860 (standard for HF Spaces)
EXPOSE 7860

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
