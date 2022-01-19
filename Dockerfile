FROM python:3.9-slim
ENV PYTHONUNBUFFERED True
WORKDIR /app
COPY *.txt .
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt
COPY . ./

CMD exec gunicorn -w 1 --threads 8 --bind :$PORT --timeout 0 main:main 
