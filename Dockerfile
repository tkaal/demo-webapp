FROM python:3.10-alpine

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY webapp.py /app/
RUN addgroup -S webapp && adduser -S webapp -G webapp && chown webapp:webapp /app/webapp.py && chmod u+x /app/webapp.py

USER webapp

CMD [ "python", "/app/webapp.py" ]


