# ams-shim

A lightweight shim that adapts an unmodified Unreal dedicated server to [AccelByte Multiplayer Servers (AMS)](https://docs.accelbyte.io/gaming-services/modules/multiplayer/multiplayer-servers/) by implementing the [AMS watchdog protocol](https://docs.accelbyte.io/gaming-services/modules/multiplayer/multiplayer-servers/ams-watchdog-protocol/) on behalf of the DS.

## How it works

AMS expects a dedicated server to connect to its watchdog, send heartbeats, and signal when it is ready to accept players. Rather than modifying the DS, `amsshim` wraps it:

1. Parses `-dsid=` and `-port=` from the command line
2. Launches the DS as a child process, forwarding all its stdout and stderr to its own stdout
3. Connects to the AMS watchdog at `ws://localhost:5555/watchdog` using the DS ID
4. Polls the OS socket table until the DS's port is bound, then sends the ready signal
5. Sends a heartbeat every 15 seconds
6. On a drain signal from the watchdog, sends `SIGTERM` to the DS and waits for it to exit
7. Exits with the DS's exit code in all cases

## Usage

```
amsshim <executable> [args...]
```

The DS ID and port are read from the arguments passed to `amsshim` — they are not consumed and are passed through to the child process unchanged.

**Example:**
```sh
amsshim ./myds -dsid=ds_1234 -port=7777 -log
```

This launches `./myds -dsid=ds_1234 -port=7777 -log` as a child process. `amsshim` extracts `ds_1234` for the watchdog connection and watches port `7777` to determine when the DS is ready.

### Arguments

| Argument | Required | Description |
|---|---|---|
| `-dsid=<id>` | Yes | DS identifier, passed to the watchdog as the `ams-dsid` header |
| `-port=<n>` | No | Port the DS will bind; used to detect readiness. Falls back to a 5-second delay if omitted |

### Ready detection

`amsshim` polls `/proc/net/tcp`, `/proc/net/tcp6`, `/proc/net/udp`, and `/proc/net/udp6` every 500ms looking for the DS port as a bound local address. This works for any transport protocol (TCP or UDP). If `-port` is omitted, the ready signal is sent after a 5-second delay instead.

## Building

Requires Go 1.21+. The binary must target Linux.

**Linux / macOS:**
```sh
make
```

**Windows (PowerShell):**
```powershell
$env:CGO_ENABLED="0"; $env:GOOS="linux"; $env:GOARCH="amd64"
go build -trimpath -ldflags="-s -w" -o amsshim .
```

The resulting `amsshim` binary has no external dependencies.

## Testing with stubds

`cmd/stubds` is a minimal fake DS for local testing. It binds a UDP socket on the specified port, prints periodic output, and exits cleanly on `SIGTERM`.

**Build:**
```sh
# Linux / macOS
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o stubds ./cmd/stubds

# Windows PowerShell
$env:CGO_ENABLED="0"; $env:GOOS="linux"; $env:GOARCH="amd64"
go build -o stubds ./cmd/stubds
```

**Run (on Linux):**
```sh
./amsshim ./stubds -dsid=ds_test -port=7777
```

Expected sequence:
1. `amsshim` starts `stubds`
2. `stubds` binds UDP port 7777
3. `amsshim` detects the port, sends ready to the watchdog
4. `stubds` prints a tick to stdout every 5 seconds (captured by `amsshim`)
5. A drain message from the watchdog causes `amsshim` to SIGTERM `stubds` and exit
