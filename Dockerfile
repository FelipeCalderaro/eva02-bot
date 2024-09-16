FROM python:3.11-alpine

WORKDIR /app
COPY . ./
COPY requirements.txt /tmp/requirements.txt
COPY startup.sh /startup.sh

RUN python3 -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
RUN chmod +x /startup.sh

CMD sh /startup.sh
# CMD python3 /bin/test.py