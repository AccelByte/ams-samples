# these environment variables are required:
# AB_BASE_URL
# AB_NAMESPACE
# AB_CLIENT_ID
# AB_CLIENT_SECRET
# Furthermore, adjust thet constants in the script below to match your needs.

import accelbyte_py_sdk
import accelbyte_py_sdk.services.auth as auth_service
import json
import os
import re
import subprocess
from accelbyte_py_sdk.api.ams.models import ApiDevelopmentServerConfigurationCreateRequest
from accelbyte_py_sdk.api.ams.operations.development import DevelopmentServerConfigurationCreate
from accelbyte_py_sdk.core import EnvironmentConfigRepository, run_request
from datetime import datetime, timedelta

BUILD_VERSION = datetime.now().strftime('%Y-%m-%d_%H-%M')

# Constants, update these with values according to your needs.
CONFIG_NAME = f"mygame_{BUILD_VERSION}"               # Unique configuration name (max 128 chars)
COMMAND_LINE = "-dsid ${dsid} -port ${default_port}"  # Command line arguments passed to your DS
AMS_CLI_PATH = "./ams-cli"                            # AMS CLI executable path.
DS_FOLDER_PATH = "example_dedicated_server"           # Filepath containing your DS executable
DS_EXECUTABLE_NAME = "ds_executable"                  # Filename of your DS executable
DS_IMAGE_NAME = f"image-{BUILD_VERSION}"              # Unique image name

AB_BASE_URL, AB_CLIENT_ID, AB_CLIENT_SECRET, AB_NAMESPACE = (
    os.getenv(var) for var in ["AB_BASE_URL", "AB_CLIENT_ID", "AB_CLIENT_SECRET", "AB_NAMESPACE"]
)

def upload_image():
    if not os.path.exists(AMS_CLI_PATH):
        print("AMS CLI not found")
        exit(1)

    hostname = AB_BASE_URL.split("//")[-1]
    command = [
        AMS_CLI_PATH,
        "upload",
        "-c", AB_CLIENT_ID,
        "-s", AB_CLIENT_SECRET,
        "-e", DS_EXECUTABLE_NAME,
        "-n", DS_IMAGE_NAME,
        "-H", hostname,
        "-p", DS_FOLDER_PATH
    ]
    try:
        # Execute the CLI to upload the DS
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Upload successful.")
        image_id = re.search(r'img_[a-zA-Z0-9_-]+', result.stderr.decode()).group(0)
        print(f"DS Image ID: {image_id}")
        return image_id

    except subprocess.CalledProcessError as e:
        print("An error occurred during the upload process:" + e.stderr.decode())

def create_build_config(image_id):
    # Initialize the SDK (uses AB_BASE_URL, AB_CLIENT_ID, AB_CLIENT_SECRET, and AB_NAMESPACE)
    accelbyte_py_sdk.initialize()

    # Login using client credentials
    token, error = auth_service.login_client()
    if error:
        print("Login failed:", error)
        exit(1)

    # Set expiration to 30 days from now
    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

    # Build the request body
    body = ApiDevelopmentServerConfigurationCreateRequest.create(
        command_line_arguments=COMMAND_LINE,
        expires_at=expires_at,
        image_id=image_id,
        name=CONFIG_NAME
    )

    # Create the operation using the extend SDK's create method
    operation = DevelopmentServerConfigurationCreate.create(
        body=body,
        namespace=AB_NAMESPACE
    )

    # Execute the operation
    result, error = run_request(operation)
    if error:
        print("Error creating configuration:", error)
        exit(1)

    print("Your build configuration:")
    print(json.dumps(result.to_dict(), indent=2))

if __name__ == "__main__":
    for var_name in ["AMS_CLI_PATH", "AB_CLIENT_ID", "AB_NAMESPACE", "AB_CLIENT_SECRET", "DS_EXECUTABLE_NAME", "DS_IMAGE_NAME", "DS_FOLDER_PATH"]:
        var_value = globals().get(var_name)
        if var_value is None or var_value == "":
            raise ValueError(f"Missing or empty required variable: {var_name}")

    image_id = upload_image()
    if image_id is None or image_id == "":
        exit(1)
    create_build_config(image_id)
    print("Done.")