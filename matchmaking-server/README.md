# Sample Matchmaking Server

This directory contains a very simple matchmaking app that uses AMS as a dedicated server provider.

This README explains how to build the Docker container and run the matchmaking server locally.

## Building the Docker Container

To build the Docker container, navigate to the directory containing the `Dockerfile` and run the following command:

```sh
docker build -t matchmaking_server .
```

## Running the Docker Image

To run the Docker image with the required environment variables, use the following command:

```sh
docker run -d --rm -p 8080:8080 \
    -e AB_BASE_URL=<your_base_url> \
    -e AB_NAMESPACE=<your_namespace> \
    -e AB_CLIENT_ID=<your_client_id> \
    -e AB_CLIENT_SECRET=<your_client_secret> \
    --name matchmaking_server \
    matchmaking_server
```

Replace `<your_base_url>`, `<your_namespace>`, `<your_client_id>`, and `<your_client_secret>` with the appropriate values for your environment.

Your local game client can now connect to `ws://localhost:8080` for matchmaking. 

## Required Environment Variables

- `AB_BASE_URL`: The base URL for the API.
- `AB_NAMESPACE`: The namespace for the API.
- `AB_CLIENT_ID`: The client ID for authentication.  This client must have `update` permission on `NAMESPACE:{namespace}:AMS:SERVER:CLAIM`
- `AB_CLIENT_SECRET`: The client secret for authentication.

## Optional Environment Variables

- `CLAIM_KEYS`: The list of claim keys to use for the AMS claim request (default: "default")
- `REGIONS`: The list of regions to use for the AMS claim request (default: "us-west-2,us-east-1")
- `LOCAL_SERVER`: For easier testing of your local game integration with this sample server set this to the IP:PORT you want it to return clients instead of claiming a server from AMS

## Stopping the Docker Container

To stop the Docker container, use the following command:

```sh
docker stop matchmaking_server
```

## Additional Information

For more information on Docker, visit the [official Docker documentation](https://docs.docker.com/).