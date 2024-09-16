FROM python:3.11-alpine
COPY ./cogs /eva/cogs
COPY ./domain /eva/domain
COPY ./models /eva/models
COPY ./modules /eva/modules
COPY ./views /eva/views
COPY ./services /eva/services
COPY ./utils /eva/utils
COPY ./main.py /eva/main.py
COPY ./EVA.py /eva/EVA.py
COPY ./discord.log /eva/discord.log

COPY requirements.txt /tmp/requirements.txt
COPY startup.sh /startup.sh

RUN python3 -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
RUN chmod +x /startup.sh

CMD sh /startup.sh
# CMD python3 /bin/test.py