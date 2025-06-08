FROM python:3.12.4-alpine
LABEL Maintainer="LRVT"

COPY requirements.txt gzctf_cloner.py /app/.
RUN pip3 install -r /app/requirements.txt

WORKDIR /app
ENTRYPOINT [ "python", "gzctf_cloner.py"]

CMD [ "python", "gzctf_cloner.py", "--help"]
