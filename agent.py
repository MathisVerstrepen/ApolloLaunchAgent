import subprocess
import os
from concurrent import futures
import logging
import time
import yaml
import grpc

import py_protos.deployAgent_pb2_grpc as deployAgent_pb2_grpc
import py_protos.deployAgent_pb2 as deployAgent_pb2


def bytes_to_yaml(byte_data: bytes):
    """Convert bytes to yaml format

    Args:
        byte_data (bytes): The byte data to convert

    Returns:
        dict: The yaml data
    """
    try:
        string_data = byte_data.decode("utf-8")
        yaml_data = yaml.safe_load(string_data)

        return yaml_data
    except yaml.YAMLError as e:
        print(f"Error: {e}")
        return None


def run_subprocess_with_logging(command: list):
    """Run a subprocess and log the output

    Args:
        command (list): The command to run
    """
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    if result.stdout:
        logging.info(result.stdout.decode("utf-8"))
    if result.stderr:
        logging.info(result.stderr.decode("utf-8"))


def docker_auth():
    """Authenticate with the docker registry"""

    os.system(
        f'echo "{os.environ["DOCKER_REGISTRY_TOKEN"]}" | docker login --username {os.environ["DOCKER_REGISTRY_USERNAME"]} --password-stdin {os.environ["DOCKER_REGISTRY_URL"]}'
    )


class DeployServicer(deployAgent_pb2_grpc.DeployDockerComposeServicer):
    """gRPC server for the deploy agent

    Args:
        deployAgent_pb2_grpc (module): The gRPC module
    """

    def Deploy(self, request, _) -> deployAgent_pb2.DeployDockerComposeResponse:
        """Deploy the docker-compose file

        Args:
            request (deployAgent_pb2.DeployDockerComposeRequest): The request object
            context (grpc.ServicerContext): The context object

        Returns:
            deployAgent_pb2.DeployDockerComposeResponse: The response object
        """
        start_time = time.time()

        service_name = request.serviceName
        logging.basicConfig(
            filename=f"/agent/logs/{service_name}.log", level=logging.INFO
        )

        # Clear the tmp directory contents
        run_subprocess_with_logging(
            ["rm", "-rf", "/agent/tmp/*"],
        )

        # Write the docker-compose file
        docker_compose_bytes = request.dockerComposeYaml
        docker_compose = bytes_to_yaml(docker_compose_bytes)
        with open("/agent/tmp/docker-compose.yml", "w", encoding="utf-8") as f:
            f.write(yaml.dump(docker_compose, default_flow_style=False))

        # Write the .env file
        env_file_bytes = request.envFile
        with open("/agent/tmp/tmp.env", "wb") as f:
            f.write(env_file_bytes)

        # Down the docker compose
        run_subprocess_with_logging(
            ["docker", "compose", "-f", "/agent/tmp/docker-compose.yml", "down"],
        )

        # Force pull the images
        run_subprocess_with_logging(
            [
                "docker",
                "compose",
                "--env-file",
                "/agent/tmp/tmp.env",
                "-f",
                "/agent/tmp/docker-compose.yml",
                "pull",
            ],
        )

        # Deploy the docker compose
        run_subprocess_with_logging(
            [
                "docker",
                "compose",
                "--env-file",
                "/agent/tmp/tmp.env",
                "-f",
                "/agent/tmp/docker-compose.yml",
                "up",
                "-d",
            ],
        )

        end_time = time.time()

        return deployAgent_pb2.DeployDockerComposeResponse(
            message="Success", timeTaken=end_time - start_time
        )


def serve():
    """Start the gRPC server"""

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    deploy_servicer = DeployServicer()
    deployAgent_pb2_grpc.add_DeployDockerComposeServicer_to_server(
        deploy_servicer, server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    docker_auth()
    serve()
