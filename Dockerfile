FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DIRPATH=/var/app

WORKDIR $DIRPATH

COPY requirements.txt $DIRPATH/

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . $DIRPATH

EXPOSE 8080

CMD ["python", "-m", "app.main"]
