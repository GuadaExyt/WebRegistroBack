FROM python:3.9

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY credentials.json /usr/src/app/credentials.json

ENV GOOGLE_APPLICATION_CREDENTIALS=/usr/src/app/credentials.json

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
