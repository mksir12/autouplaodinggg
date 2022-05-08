FROM alpine:3.14

ENV IS_CONTAINERIZED=true
ENV IS_FULL_DISK_SUPPORTED=false

RUN \
 echo "**** install build packages ****" && \
 apk add --no-cache --virtual=build-dependencies \
	g++ \
	py3-pip \
	python3-dev
RUN \
 echo "**** install runtime packages ****" && \
 apk add --no-cache --upgrade \
	ffmpeg \
	mediainfo \
	python3 \
	mktorrent \
	unrar

WORKDIR /app

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
