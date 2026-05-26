# AMS Unreal Engine Quickstart

A PowerShell script that automates the end-to-end workflow for uploading a dedicated server build to AccelByte Managed Servers (AMS) and creating a fleet, using the AGS CLI and AMS CLI.

## What it does

1. Downloads the latest [AGS CLI](https://github.com/AccelByte/accelbyte-ags-cli/releases) and [AMS CLI](https://cdn.prod.ams.accelbyte.io/windows_amd64/ams.exe) into a local `tools/` folder
2. Prompts for your environment and build details (base URL, namespace, build path, etc.)
3. Configures the AGS CLI (base URL and namespace)
4. Registers a temporary public IAM client via OAuth 2.0 Dynamic Client Registration (RFC 7591) and authenticates via browser (OAuth authorization code flow)
5. Creates a confidential IAM client scoped for AMS uploads
6. Uploads the server build with the AMS CLI and captures the resulting image ID
8. Lets you select an instance type and region interactively
9. Creates an AMS fleet from the `fleet.json` template

## Prerequisites

- Windows 10/11, PowerShell 5.1 or later
- Internet access (to download the CLI tools and reach your AGS environment)
- An admin-level user account in your namespace (used during browser login)

## Usage

```powershell
.\ams-quickstart.ps1
```

The script will prompt for every required value interactively. You can also supply values as parameters to skip the prompts:

```powershell
.\ams-quickstart.ps1 `
    -BaseUrl    "development.accelbyte.io" `
    -Namespace  "mygame" `
    -BuildPath  "C:\MyGame\LinuxServer" `
    -Executable "MyGameServer.sh" `
    -ImageName  "MyGame Server v1.0" `
    -FleetName  "MyGame Fleet 1"
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `-BaseUrl` | AGS base URL **without** `https://` (e.g. `development.accelbyte.io`) |
| `-Namespace` | AccelByte namespace |
| `-BuildPath` | Local directory containing the dedicated server build |
| `-Executable` | Server executable path, relative to `-BuildPath` (e.g. `MyGameServer.sh`) |
| `-ImageName` | Display name for the uploaded image |
| `-FleetName` | Name for the new fleet (defaults to `-ImageName`) |
| `-SkipClientCreation` | Skip creating an AMS upload client; you'll be prompted for an existing client ID and secret |

### Using an existing upload client

If you already have a confidential IAM client with AMS upload permissions (or if you're on AccelByte Shared Cloud and used the **Create DS Uploader IAM Client** button in the portal):

```powershell
.\ams-quickstart.ps1 -SkipClientCreation
```

The script will prompt for the client ID and secret instead of creating a new one.

## Fleet template

`fleet.json` is the template used when creating the fleet. The script substitutes these fields at runtime:

| Field | Source |
|-------|--------|
| `name` | `-FleetName` parameter |
| `imageDeploymentProfile.imageId` | image ID returned after upload |
| `dsHostConfiguration.instanceId` | instance type you select interactively |
| `regions[0].region` | region you select interactively |

Edit `fleet.json` directly to adjust timeouts, port configuration, server count, sampling rules, claim keys, or the server command line before running the script.

## Output

On success the script prints:

```
Image ID : img_01975bf9-...
Fleet ID : flt_...
Fleet    : My Fleet Name
Region   : us-west-2
```

The fleet is created **inactive**. The script prints a direct link to the fleet in the Admin Portal — open it and activate the fleet from there.

## Notes

- CLI binaries are downloaded once into `tools/` and reused on subsequent runs.
- The public IAM client is registered on every run via OAuth 2.0 Dynamic Client Registration (RFC 7591) at `/iam/v3/oauth/register`. AccelByte's IAM advertises this endpoint in `/.well-known/oauth-authorization-server` and accepts unauthenticated registration requests, so no portal setup is required.
- The IAM upload client is created with resource `AMS:UPLOAD` and action `5` (Create + Update).
- The `ags ams info list-supported-insstances` command name has a double-s typo — this matches the typo present in the AMS API spec that the CLI is generated from.
