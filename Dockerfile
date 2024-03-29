FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY mealwise /app
COPY mealwise/requirements.txt /app/config/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/config/requirements.txt

# Expose port
EXPOSE 80

# Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]