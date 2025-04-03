# Sample DS Upload Automation Script

This example shows how to upload a DS and create a build configuration for it.
The script is intended to be used in a build machine or CI/CD pipeline, or for other automation purposes.

This script does the following:
1. Log in to AGS
2. Upload a dedicated server (DS) image to AMS.
3. Create a build configuration for that image (also known as development build configuration).

For authentication, the script requires the following environment variables:
- `AB_BASE_URL`: The base URL for the API.
- `AB_NAMESPACE`: The namespace for the API.
- `AB_CLIENT_ID`: The client ID for authentication.
- `AB_CLIENT_SECRET`: The client secret for authentication.

Furthermore, make sure you set the following variables in the script according to your dedicated server:
- `CONFIG_NAME"`: Unique configuration name (max 128 chars)
- `COMMAND_LINE`: Command line arguments passed to your DS
- `AMS_CLI_PATH`: AMS CLI executable path
- `DS_FOLDER_PATH`: Filepath containing your DS executable
- `DS_EXECUTABLE_NAME`: Filename of your DS executable
- `DS_IMAGE_NAME`: Unique image name

This example uses the AccelByte Extend SDK to interact with the AccelByte Gaming Services API and the AMS CLI to upload the DS image.

# Running
You will want to adapt the script to your build system needs and run it as part of your build process.
If you just want to see the script in action, run it using Docker, as described below, or run it directly as follows:
```sh
# use python3.10
export AB_BASE_URL="https://<yourenvironment>.accelbyte.io" # For shared cloud use https://<studionamespace>-<gamenamespace>.prod.gamingservices.accelbyte.io
export AB_CLIENT_ID="your_client_id"
export AB_CLIENT_SECRET="your_client_secret"
export AB_NAMESPACE="your_namespace"
python3 upload_and_create_buildconfig.py
```

## Building the Docker Container

To build the Docker container, navigate to the directory containing the `Dockerfile` and run the following command:

```sh
docker build -t upload-script .
```

## Running the Docker Image

To run the Docker image with the required environment variables, use the following command:

```sh
docker run --rm \
    -e AB_BASE_URL=https://<your_environment>.accelbyte.io \
    -e AB_NAMESPACE=your_namespace \
    -e AB_CLIENT_ID=your_client_id \
    -e AB_CLIENT_SECRET=your_client_secret \
    -v ./example_dedicated_server:/app/example_dedicated_server \
    --name upload-script \
    upload-script
```

Replace `<your_base_url>`, `<your_namespace>`, `<your_client_id>`, and `<your_client_secret>` with the appropriate values for your environment.

# See also
Public documentation regarding this script's features: https://docs.accelbyte.io/gaming-services/services/ams/how-to/automate-dedicated-server-uploads-in-cicd/