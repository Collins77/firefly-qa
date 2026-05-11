FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["pytest", "-v", "--tb=short", "-m", "not load", \
     "--html=reports/report.html", "--self-contained-html"]
