FROM python:3

RUN apt update && apt -y install tmux htop netcat

ENV COMPONENT_NAME="EMPTY_DOCKER_COMPONENT_NAME"


# WORKDIR /usr/src/app


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# COPY . .
COPY ./entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]



# CMD [ "python", "./main.py" ,"-c", '$COMPONENT_NAME']