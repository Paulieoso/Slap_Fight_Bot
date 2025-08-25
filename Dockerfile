FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libjpeg-dev zlib1g-dev \ 
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "bot.py"]
