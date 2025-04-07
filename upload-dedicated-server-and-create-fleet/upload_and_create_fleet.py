import accelbyte_py_sdk
import accelbyte_py_sdk.services.auth as auth_service
import json
import os
import re
import subprocess
from datetime import datetime
from accelbyte_py_sdk.core import run_request

from accelbyte_py_sdk.api.ams.operations.fleets import FleetCreate
from accelbyte_py_sdk.api.ams.models import (
    ApiFleetParameters,
    ApiDSHostConfigurationParameters,
    ApiImageDeploymentProfile,
    ApiPortConfiguration,
    ApiFleetArtifactsSampleRules,
    ApiRegionConfig,
    ApiCoredumpSamplingRules,
    ApiArtifactTypeSamplingRules,
    ApiArtifactSamplingRule
)

# Constants, update these according to your environment.
# Set the following environment variables: AB_BASE_URL, AB_CLIENT_ID, AB_CLIENT_SECRET, and AB_NAMESPACE.
AMS_CLI_PATH = "./ams-cli"
DS_FOLDER_PATH = "build"
DS_EXECUTABLE_NAME = "runserver"
DS_IMAGE_NAME = f"fleet-image-{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
FLEET_NAME = f"my-production-fleet-{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
FLEET_COMMAND_LINE = "-dsid ${dsid} -port ${default_port}"

AB_BASE_URL, AB_CLIENT_ID, AB_CLIENT_SECRET, AB_NAMESPACE = (
    os.getenv(var) for var in ["AB_BASE_URL", "AB_CLIENT_ID", "AB_CLIENT_SECRET", "AB_NAMESPACE"]
)

def upload_image():
    if not os.path.exists(AMS_CLI_PATH):
        print("AMS CLI not found. Use `wget https://cdn.prod.ams.accelbyte.io/linux_amd64/ams -o ams-cli` to get it.")
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

def create_fleet(image_id: str):
    accelbyte_py_sdk.initialize()
    _, err = auth_service.login_client()
    if err:
        print("Login failed:", err)
        exit(1)

    # Construct the fleet configuration.
    # Note one could consider the alternative of creating the `params` from JSON with:
    # params = ApiFleetParameters.create_from_dict(json.loads(fleet_config_json))
    params = ApiFleetParameters.create(
        active=False,
        ds_host_configuration=ApiDSHostConfigurationParameters.create(
            servers_per_vm=1,
            instance_id="01884fee-1e9b-7b1b-b0d3-ab01420951d5" # see https://docs.accelbyte.io/api-explorer/#AMS/InfoSupportedInstances
        ),
        image_deployment_profile=ApiImageDeploymentProfile.create(
            command_line=FLEET_COMMAND_LINE,
            image_id=image_id,
            port_configurations=[
                ApiPortConfiguration.create(name="default_port", protocol="UDP")
            ]
        ),
        name=FLEET_NAME,
        on_demand=False,
        regions=[
            ApiRegionConfig.create(
                region="us-east-2",
                buffer_size=1,
                min_server_count=0,
                max_server_count=5,
                dynamic_buffer=False, # Recommended to leave this False.
            )
        ],
        sampling_rules=ApiFleetArtifactsSampleRules.create(
            coredumps=ApiCoredumpSamplingRules.create(
                crashed=ApiArtifactSamplingRule.create(collect=True, percentage=1)
            ),
            logs=ApiArtifactTypeSamplingRules.create(
                crashed=ApiArtifactSamplingRule.create(collect=True, percentage=100),
                success=ApiArtifactSamplingRule.create(collect=True, percentage=0),
                unclaimed=ApiArtifactSamplingRule.create(collect=True, percentage=0)
            )
        )
    )

    operation = FleetCreate.create(namespace=AB_NAMESPACE, body=params)
    result, error = run_request(operation)
    if error:
        print("Fleet creation failed:", error)
        exit(1)

    print("Production fleet created successfully.")
    print(json.dumps(result.to_dict(), indent=2))

if __name__ == "__main__":
    for var_name in ["AMS_CLI_PATH", "AB_CLIENT_ID", "AB_NAMESPACE", "AB_CLIENT_SECRET", "DS_EXECUTABLE_NAME", "DS_IMAGE_NAME", "DS_FOLDER_PATH"]:
        var_value = globals().get(var_name)
        if var_value is None or var_value == "":
            raise ValueError(f"Missing or empty required variable: {var_name}")
    image_id = upload_image()
    print(f"Image ID: {image_id}")
    create_fleet(image_id)
    print("Done.")