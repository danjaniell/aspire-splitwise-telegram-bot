FROM python:3.10-slim
ENV PYTHONUNBUFFERED True
ENV ON_DOCKER True

#Set working directory
WORKDIR /app

#Install the dependencies
COPY *.txt .
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt

#Copy files
COPY . ./

#Expose the required port
EXPOSE $PORT

#Run the command
CMD exec gunicorn --log-level=info --workers 1 --threads 8 --bind :$PORT --timeout 0 app:app