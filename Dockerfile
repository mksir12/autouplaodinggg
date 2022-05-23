FROM noobmaster669/gg-bot-base:latest

WORKDIR /app

ENV IS_CONTAINERIZED=true
ENV IS_FULL_DISK_SUPPORTED=false

# add local files
COPY requirements.txt .
RUN \
  echo "**** install pip packages ****" && \
  pip3 install -r requirements.txt && \
  pip3 freeze > requirements.txt

COPY . .
RUN rm auto_reupload.py && chmod +x auto_upload.py

# ports and volumes
VOLUME /data /temp_upload

ENTRYPOINT [ "python3", "auto_upload.py"]
