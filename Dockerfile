FROM python:3.9

WORKDIR /app

# Copy only requirements first (for caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Then copy app code
COPY app/ .

CMD ["python", "app.py"]