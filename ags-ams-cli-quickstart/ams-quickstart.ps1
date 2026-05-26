#Requires -Version 5.1
<#
.SYNOPSIS
    AMS Unreal Engine Quickstart — downloads CLI tools, uploads a server build, and creates an AMS fleet.

.PARAMETER BaseUrl
    AGS base URL without scheme (e.g. "development.accelbyte.io").

.PARAMETER Namespace
    AccelByte namespace.

.PARAMETER BuildPath
    Local directory containing the dedicated server build.

.PARAMETER Executable
    Path to the startup executable, relative to BuildPath (e.g. "MyGameServer.sh").

.PARAMETER ImageName
    Display name for the uploaded image.

.PARAMETER FleetName
    Name for the new fleet (defaults to ImageName).

.PARAMETER SkipClientCreation
    Skip creating an AMS upload client; you will be prompted for an existing client ID and secret.
#>
param(
    [string]$BaseUrl          = "",
    [string]$Namespace        = "",
    [string]$BuildPath        = "",
    [string]$Executable       = "",
    [string]$ImageName        = "",
    [string]$FleetName        = "",
    [switch]$SkipClientCreation
)

$ErrorActionPreference = "Stop"

# ── Paths ──────────────────────────────────────────────────────────────────────
$ScriptDir  = $PSScriptRoot
$ToolsDir   = Join-Path $ScriptDir "tools"
$AgsExe     = Join-Path $ToolsDir "ags.exe"
$AmsExe     = Join-Path $ToolsDir "ams.exe"
$AmsCliUrl  = "https://cdn.prod.ams.accelbyte.io/windows_amd64/ams.exe"
$AgsRelUrl  = "https://api.github.com/repos/AccelByte/accelbyte-ags-cli/releases/latest"
$CacheFile  = Join-Path $ScriptDir ".ams-upload-client.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step  { param([string]$t) Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Write-Ok    { param([string]$t) Write-Host "[OK] $t"  -ForegroundColor Green }
function Write-Info  { param([string]$t) Write-Host "     $t"  -ForegroundColor Gray }
function Write-Warn  { param([string]$t) Write-Host "[!!] $t"  -ForegroundColor Yellow }

function Read-Required {
    param([string]$Prompt, [string]$Default = "")
    $label = if ($Default) { "$Prompt [$Default]" } else { $Prompt }
    do {
        $v = (Read-Host $label).Trim()
        if (-not $v -and $Default) { return $Default }
        if (-not $v) { Write-Warn "Required." }
    } while (-not $v)
    return $v
}

function Invoke-Ags {
    param([string[]]$Cmd)
    $out = & $AgsExe @Cmd 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host $out
        throw "ags $($Cmd -join ' ') exited with code $LASTEXITCODE"
    }
    return $out
}

function New-ClientSecret {
    # Meets AccelByte rules: 8-32 chars, ≥3 of {upper,lower,digit,special},
    # no more than 2 identical consecutive characters.
    $upper   = [char[]]'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    $lower   = [char[]]'abcdefghijklmnopqrstuvwxyz'
    $digits  = [char[]]'0123456789'
    $special = [char[]]'!~<>,;:_=?*+#."&%()|-$^@/'
    $all     = $upper + $lower + $digits + $special

    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    function Get-RandChar([char[]]$set) {
        $buf = [byte[]]::new(4)
        $rng.GetBytes($buf)
        return $set[[BitConverter]::ToUInt32($buf, 0) % $set.Length]
    }

    do {
        # Seed with one of each type, then fill to 24 chars from the full set
        $chars = @(Get-RandChar $upper; Get-RandChar $lower; Get-RandChar $digits; Get-RandChar $special)
        for ($i = 4; $i -lt 24; $i++) { $chars += Get-RandChar $all }

        # Fisher-Yates shuffle
        for ($i = $chars.Length - 1; $i -gt 0; $i--) {
            $buf = [byte[]]::new(4); $rng.GetBytes($buf)
            $j = [BitConverter]::ToUInt32($buf, 0) % ($i + 1)
            $tmp = $chars[$i]; $chars[$i] = $chars[$j]; $chars[$j] = $tmp
        }

        $secret = -join $chars
        $ok = $true
        for ($i = 2; $i -lt $secret.Length; $i++) {
            if ($secret[$i] -eq $secret[$i-1] -and $secret[$i] -eq $secret[$i-2]) { $ok = $false; break }
        }
    } while (-not $ok)

    return $secret
}

function Write-TempJson {
    param([object]$Object)
    $path = Join-Path $env:TEMP "ams_qs_$([System.IO.Path]::GetRandomFileName()).json"
    $Object | ConvertTo-Json -Depth 10 | Set-Content -Path $path -Encoding UTF8
    return $path
}

# ── Step 1 · Download CLI tools ───────────────────────────────────────────────

function Get-CLIs {
    Write-Step "Downloading CLI tools"
    New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null

    # AGS CLI — resolve latest release URL from GitHub
    if (-not (Test-Path $AgsExe)) {
        Write-Info "Resolving latest AGS CLI release..."
        $release    = Invoke-RestMethod -Uri $AgsRelUrl -UseBasicParsing
        $asset      = $release.assets | Where-Object { $_.name -eq "ags-x86_64-pc-windows-msvc.zip" } | Select-Object -First 1
        if (-not $asset) { throw "Could not find Windows AGS CLI asset in latest release." }
        $zipPath    = Join-Path $ToolsDir "ags.zip"
        Write-Info "Downloading $($asset.browser_download_url)"
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -UseBasicParsing
        Expand-Archive -Path $zipPath -DestinationPath $ToolsDir -Force
        Remove-Item $zipPath
        $found = Get-ChildItem -Path $ToolsDir -Filter "ags.exe" -Recurse | Select-Object -First 1
        if (-not $found) { throw "ags.exe not found after extraction." }
        if ($found.FullName -ne $AgsExe) {
            Move-Item -Path $found.FullName -Destination $AgsExe -Force
        }
        Write-Ok "AGS CLI $($release.tag_name) downloaded"
    } else {
        Write-Ok "AGS CLI already present"
    }

    # AMS CLI
    if (-not (Test-Path $AmsExe)) {
        Write-Info "Downloading AMS CLI from $AmsCliUrl"
        Invoke-WebRequest -Uri $AmsCliUrl -OutFile $AmsExe -UseBasicParsing
        Write-Ok "AMS CLI downloaded"
    } else {
        Write-Ok "AMS CLI already present"
    }
}

# ── Step 2 · Gather inputs ────────────────────────────────────────────────────

$Cfg = @{}   # mutable config collected across steps

function Get-Inputs {
    Write-Step "Configuration"

    $Cfg.BaseUrl   = if ($BaseUrl)   { $BaseUrl }   else { Read-Required "AGS base URL (e.g. development.accelbyte.io, no https://)" }
    $Cfg.Namespace = if ($Namespace) { $Namespace } else { Read-Required "Namespace" }

    Write-Host ""
    $Cfg.BuildPath  = if ($BuildPath)  { $BuildPath }  else { Read-Required "Build directory path (e.g. C:\MyGame\LinuxServer)" }
    $Cfg.Executable = if ($Executable) { $Executable } else { Read-Required "Server executable (relative to build path, e.g. MyGameServer.sh)" }
    $Cfg.ImageName  = if ($ImageName)  { $ImageName }  else { Read-Required "Image name" }
    $Cfg.FleetName  = if ($FleetName)  { $FleetName }  else { Read-Required "Fleet name" $Cfg.ImageName }

    if (-not (Test-Path $Cfg.BuildPath)) {
        Write-Warn "Build path '$($Cfg.BuildPath)' does not exist. Continuing anyway."
    }
}

# ── Step 3 · Configure AGS CLI ────────────────────────────────────────────────

function Set-AgsConfig {
    Write-Step "Configuring AGS CLI"

    Invoke-Ags @("config", "set", "base-url", "https://$($Cfg.BaseUrl)") | Out-Null
    Invoke-Ags @("config", "set", "namespace", $Cfg.Namespace)          | Out-Null

    Write-Ok "Base URL and namespace set"
}

function Invoke-Auth {
    Write-Step "Authentication"

    # Check for an existing valid session. Exit code 0 only means the command ran —
    # inspect the output to confirm the access token is actually valid.
    $statusOut = & $AgsExe auth status 2>&1
    if ($LASTEXITCODE -eq 0 -and ($statusOut -match 'Access Token:\s+valid')) {
        $statusOut | ForEach-Object { Write-Host "     $_" }
        Write-Ok "Already authenticated — skipping login"
        return
    }

    # No valid session — register a temporary public client via OAuth 2.0 DCR
    # (RFC 7591). AccelByte's IAM advertises an open registration endpoint in
    # /.well-known/oauth-authorization-server; no prior credentials required.
    Write-Info "Registering public client via DCR..."
    $regUrl   = "https://$($Cfg.BaseUrl)/iam/v3/oauth/register"
    $regBody  = @{
        client_name                = "AGS CLI Quickstart"
        token_endpoint_auth_method = "none"
        redirect_uris              = @("http://127.0.0.1:8080")
        grant_types                = @("authorization_code")
        response_types             = @("code")
    } | ConvertTo-Json
    $response = Invoke-RestMethod -Method POST -Uri $regUrl `
        -ContentType "application/json" -Body $regBody -UseBasicParsing
    $clientId = $response.client_id
    if (-not $clientId) { throw "DCR response did not contain a client_id." }
    Write-Info "Public client: $clientId"

    $env:AGS_CLIENT_ID = $clientId
    Write-Info "A browser window will open. Log in and return here."
    & $AgsExe auth login
    if ($LASTEXITCODE -ne 0) { throw "Authentication failed (exit $LASTEXITCODE)." }
    Write-Ok "Authenticated"
}

# ── Step 4 · Create AMS upload client ─────────────────────────────────────────

function Get-CachedUploadClient {
    if (-not (Test-Path $CacheFile)) { return $false }
    $key = "$($Cfg.BaseUrl)|$($Cfg.Namespace)"
    try {
        $cache = Get-Content $CacheFile -Raw | ConvertFrom-Json
        $prop  = $cache.PSObject.Properties[$key]
        if ($prop -and $prop.Value.clientId -and $prop.Value.clientSecret) {
            $Cfg.UploadClientId     = $prop.Value.clientId
            $Cfg.UploadClientSecret = $prop.Value.clientSecret
            return $true
        }
    } catch { }
    return $false
}

function Save-UploadClientCache {
    $key   = "$($Cfg.BaseUrl)|$($Cfg.Namespace)"
    $entry = [PSCustomObject]@{ clientId = $Cfg.UploadClientId; clientSecret = $Cfg.UploadClientSecret }
    if (Test-Path $CacheFile) {
        try   { $cache = Get-Content $CacheFile -Raw | ConvertFrom-Json }
        catch { $cache = [PSCustomObject]@{} }
    } else {
        $cache = [PSCustomObject]@{}
    }
    if ($cache.PSObject.Properties[$key]) {
        $cache.PSObject.Properties[$key].Value = $entry
    } else {
        $cache | Add-Member -NotePropertyName $key -NotePropertyValue $entry
    }
    $cache | ConvertTo-Json -Depth 5 | Set-Content $CacheFile -Encoding UTF8
}

function New-UploadClient {
    Write-Step "Creating AMS upload IAM client"

    if (Get-CachedUploadClient) {
        Write-Ok "Reusing cached upload client: $($Cfg.UploadClientId)"
        return
    }

    # Create a confidential OAuth client.
    # AccelByte IAM v3 requires the caller to supply both clientId (32 hex chars)
    # and secret for confidential clients — neither is server-generated.
    $Cfg.UploadClientId     = [System.Guid]::NewGuid().ToString("N")
    $Cfg.UploadClientSecret = New-ClientSecret

    $clientBody = @{
        clientId         = $Cfg.UploadClientId
        secret           = $Cfg.UploadClientSecret
        clientName       = "AMS DS Uploader Quickstart"
        namespace        = $Cfg.Namespace
        oauthClientType  = "Confidential"
        redirectUri      = "http://127.0.0.1"
        baseUri          = ""
        audiences        = @()
        scopes           = @()
        twoFactorEnabled = $false
        skipLoginQueue   = $false
    }
    $clientJsonPath = Write-TempJson $clientBody

    Write-Info "Creating IAM client..."
    Invoke-Ags @("iam", "clients", "create", "--namespace", $Cfg.Namespace, "--json", "@$clientJsonPath") | Out-Null
    Remove-Item $clientJsonPath -ErrorAction SilentlyContinue

    # Grant AMS upload permissions.
    # action 15 = CREATE|READ|UPDATE|DELETE
    $permsBody = @{
        permissions = @(
            @{ resource = "AMS:UPLOAD"; action = 5 }   # Create=1, Update=4
        )
    }
    $permsJsonPath = Write-TempJson $permsBody

    Write-Info "Adding AMS:UPLOAD permissions..."
    Invoke-Ags @("iam", "clients", "add-permissions",
        "--namespace", $Cfg.Namespace,
        "--client-id", $Cfg.UploadClientId,
        "--json", "@$permsJsonPath") | Out-Null
    Remove-Item $permsJsonPath -ErrorAction SilentlyContinue

    Save-UploadClientCache
    Write-Ok "Upload client ready: $($Cfg.UploadClientId)"
}

function Get-ExistingClient {
    Write-Step "AMS upload client credentials"
    $Cfg.UploadClientId     = Read-Required "AMS uploader client ID"
    $Cfg.UploadClientSecret = Read-Required "AMS uploader client secret"
}

# ── Step 5 · Upload build ──────────────────────────────────────────────────────

function Invoke-Upload {
    Write-Step "Uploading build"
    Write-Info "Path      : $($Cfg.BuildPath)"
    Write-Info "Executable: $($Cfg.Executable)"
    Write-Info "Image name: $($Cfg.ImageName)"
    Write-Host ""

    # Shell scripts require an explicit target architecture; default to x86_64.
    $uploadArgs = @(
        "upload",
        "-H", $Cfg.BaseUrl,
        "-c", $Cfg.UploadClientId,
        "-s", $Cfg.UploadClientSecret,
        "-n", $Cfg.ImageName,
        "-p", $Cfg.BuildPath,
        "-e", $Cfg.Executable
    )
    if ($Cfg.Executable -like "*.sh") { $uploadArgs += @("-a", "linux-x86_64") }

    # Stream to terminal while capturing, so we can extract the image ID from the log.
    $uploadLines = [System.Collections.Generic.List[string]]::new()
    & $AmsExe @uploadArgs 2>&1 | ForEach-Object { Write-Host $_; $uploadLines.Add($_) }

    if ($LASTEXITCODE -ne 0) { throw "ams upload failed (exit $LASTEXITCODE)." }
    Write-Ok "Upload complete"

    # e.g. msg="imageID: img_019e6577-… has ended\n"
    $idLine = $uploadLines | Where-Object { $_ -match 'imageID:\s*(img_[0-9a-f-]+)' } | Select-Object -Last 1
    if ($idLine -match 'imageID:\s*(img_[0-9a-f-]+)') {
        $Cfg.ImageId = $Matches[1]
        Write-Ok "Image ID  : $($Cfg.ImageId)"
    }
}

function Get-ImageId {
    if ($Cfg.ImageId) { return }   # already parsed from upload output

    Write-Step "Resolving image ID"
    Write-Info "Fetching image list..."
    $raw    = Invoke-Ags @("ams", "images", "list", "--namespace", $Cfg.Namespace, "--format", "json")
    $images = $raw | ConvertFrom-Json

    $match = $images |
        Where-Object { $_.name -eq $Cfg.ImageName } |
        Sort-Object  { $_.createdAt } -Descending |
        Select-Object -First 1

    if (-not $match) {
        Write-Warn "No image found with name '$($Cfg.ImageName)'."
        Write-Host "Images available:"
        $images | ForEach-Object { Write-Host "  $($_.imageId)  $($_.name)  $($_.createdAt)" }
        $Cfg.ImageId = Read-Required "Enter image ID manually"
    } else {
        $Cfg.ImageId = $match.imageId
        Write-Ok "Image ID: $($Cfg.ImageId)"
    }
}

# ── Step 6 · Select instance type ─────────────────────────────────────────────

function Select-Instance {
    Write-Step "Select instance type"

    # Note: the operation ID in the AMS spec has a typo ("insstances") — the CLI
    # command reflects it exactly as generated from the spec.
    $raw = & $AgsExe ams info list-supported-insstances --namespace $Cfg.Namespace --format json 2>&1
    $ok  = $LASTEXITCODE -eq 0

    if ($ok) {
        try {
            $all       = ($raw | ConvertFrom-Json).availableInstanceTypes
            $instances = @($all | Where-Object { $_.name -in @('ttx1.s', 'ttx1.m') })
            Write-Host ""
            for ($i = 0; $i -lt $instances.Count; $i++) {
                $inst  = $instances[$i]
                $label = "$($inst.name) · $($inst.virtualCpu) vCPU · $($inst.memoryGiB) GiB"
                if ($inst.processorArchitecture) { $label += " · $($inst.processorArchitecture)" }
                Write-Host "  [$($i+1)] $label"
                Write-Host "       ID: $($inst.id)"
            }
            Write-Host ""
            $sel = Read-Host "Select instance type (1-$($instances.Count))"
            $Cfg.InstanceId = $instances[[int]$sel - 1].id
            Write-Ok "Instance: $($instances[[int]$sel - 1].name)"
            return
        } catch { }
    }

    Write-Warn "Could not retrieve instance types automatically."
    Write-Host "Run manually: ags ams info list-supported-insstances --namespace $($Cfg.Namespace) --format json"
    $Cfg.InstanceId = Read-Required "Instance type ID"
}

# ── Step 7 · Select region ────────────────────────────────────────────────────

function Select-Region {
    Write-Step "Select region"

    $raw = & $AgsExe ams info list-regions --namespace $Cfg.Namespace --format json 2>&1
    $ok  = $LASTEXITCODE -eq 0

    if ($ok) {
        try {
            $regionNames = ($raw | ConvertFrom-Json).regions
            Write-Host ""
            for ($i = 0; $i -lt $regionNames.Count; $i++) {
                Write-Host "  [$($i+1)] $($regionNames[$i])"
            }
            Write-Host ""
            $sel = Read-Host "Select region (1-$($regionNames.Count))"
            $Cfg.Region = $regionNames[[int]$sel - 1]
            Write-Ok "Region: $($Cfg.Region)"
            return
        } catch { }
    }

    Write-Warn "Could not retrieve regions automatically."
    $Cfg.Region = Read-Required "Region (e.g. us-west-2)" "us-west-2"
    Write-Ok "Region: $($Cfg.Region)"
}

# ── Step 8 · Create fleet ─────────────────────────────────────────────────────

function New-Fleet {
    Write-Step "Creating fleet"

    $templatePath = Join-Path $ScriptDir "fleet.json"
    if (-not (Test-Path $templatePath)) { throw "fleet.json not found next to script." }

    $fleet = Get-Content -Path $templatePath -Raw | ConvertFrom-Json

    $fleet.name = $Cfg.FleetName
    $fleet.imageDeploymentProfile.imageId       = $Cfg.ImageId
    $fleet.dsHostConfiguration.instanceId       = $Cfg.InstanceId
    $fleet.regions[0].region                    = $Cfg.Region

    $fleetJsonPath = Write-TempJson $fleet
    Write-Info "Fleet config written to $fleetJsonPath"

    $raw = Invoke-Ags @("ams", "fleets", "create", "--namespace", $Cfg.Namespace, "--json", "@$fleetJsonPath", "--format", "json")
    Remove-Item $fleetJsonPath -ErrorAction SilentlyContinue

    $Cfg.FleetId = ($raw | ConvertFrom-Json).id

    Write-Ok "Fleet created: $($Cfg.FleetId)"
}

# ── Main ───────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "AMS Unreal Engine Quickstart" -ForegroundColor White
Write-Host "─────────────────────────────" -ForegroundColor DarkGray

try {
    Get-CLIs
    Get-Inputs
    Set-AgsConfig
    Invoke-Auth

    if ($SkipClientCreation) {
        Get-ExistingClient
    } else {
        New-UploadClient
    }

    Invoke-Upload
    Get-ImageId
    Select-Instance
    Select-Region
    New-Fleet

    Write-Host ""
    Write-Host "─────────────────────────────" -ForegroundColor DarkGray
    Write-Host " Done!" -ForegroundColor Green
    Write-Host "─────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""
    $fleetUrl = "https://$($Cfg.BaseUrl)/admin/namespaces/$($Cfg.Namespace)/ams/fleets-manager/$($Cfg.FleetId)/status"

    Write-Host "Image ID : $($Cfg.ImageId)"
    Write-Host "Fleet ID : $($Cfg.FleetId)"
    Write-Host "Fleet    : $($Cfg.FleetName)"
    Write-Host "Region   : $($Cfg.Region)"
    Write-Host ""
    Write-Host "Fleet portal:"
    Write-Host "    $fleetUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The fleet was created inactive. Open the link above to activate it."
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    exit 1
}
