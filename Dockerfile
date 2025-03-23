FROM python:3.10-slim

WORKDIR /app

# Cài g++ + curl để compile C++ và test
RUN apt-get update && \
    apt-get install -y g++ curl docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 20256

CMD ["python", "manage.py", "runserver", "0.0.0.0:20256"]
