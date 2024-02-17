# sudo docker cp ApolloLaunchAgent:/agent/py_protos/ .

FROM python:3.9-slim

# Install Docker CLI
RUN apt-get update \
    && apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - \
    && echo "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get install -y git

WORKDIR /agent

COPY ./requirements.txt /agent/requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt \
    && rm -rf /root/.cache/pip \
    && mkdir /agent/tmp \
    && mkdir /agent/logs

COPY ./protos /agent/protos
RUN mkdir /agent/py_protos \
    && python3 -m grpc_tools.protoc -I /agent/protos --python_out=/agent/py_protos --grpc_python_out=/agent/py_protos /agent/protos/deployAgent.proto \
    && sed -i 's/import deployAgent_pb2 as deployAgent__pb2/from . import deployAgent_pb2 as deployAgent__pb2/g' /agent/py_protos/deployAgent_pb2_grpc.py \
    && touch /agent/py_protos/__init__.py

COPY agent.py /agent/agent.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1\
    PYTHONIOENCODING=utf-8

CMD ["python3", "agent.py"]
