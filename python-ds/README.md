# BasicDS

A Python-based Dedicated Server for use with AccelByte Multiplayer Servers (AMS) that implements the official AMS watchdog protocol.

## Quick Start

### Prerequisites
- UV package manager ([installation guide](https://github.com/astral-sh/uv))
- Python 3.10+

### Setup & Run
```bash
# Install dependencies
uv sync

# Run for development
uv run python -m basicds.main --dsid ds_0199ba9d-b79a-7d02-9390-c9fdc1cd3af0

# Build for deployment
./build.sh && cd dist && ./start.sh --dsid ds_0199ba9d-b79a-7d02-9390-c9fdc1cd3af0
```

## Usage

### Command Line Arguments
- **`--dsid`** (required): Server ID provided by AMS
- **`--port`** (optional): Game server port for player connections (default: 7777)
- **`--watchdog-url`** (optional): AMS watchdog URL (default: ws://localhost:5555/watchdog)  
- **`--log-level`** (optional): DEBUG, INFO, WARNING, ERROR (default: INFO)

### Examples
#### Run for Development
```bash
uv run python -m basicds.main --dsid ds_0199ba9d-b79a-7d02-9390-c9fdc1cd3af0 --log-level DEBUG
```
#### Build, test, and upload packages
```bash
amssim run # in a separat shell
./build.sh && cd dist
./start.sh --dsid ds_0199ba9d-b79a-7d02-9390-c9fdc1cd3af0 --port 8080
# verify amsim shows ds as connected and statis is ready (`ds status' command), then
# issue the `ds drain` command and verify the DS exits.

ams upload -c "8197082f20e445b5b89b3ed90f3ade22" -s "MyCli3nt5ecr3t" -e "./start.sh" -H "prod.gamingservices.accelbyte.io" -n "uv python DS" -p "./"
```

## Development

### Common Commands
```bash
uv sync                        # Install dependencies
uv add <package-name>          # Add dependency
uv build                       # Build packages
./build.sh                     # Build deployment package
```

## AMS Integration

Implements the [AccelByte AMS Watchdog Protocol](https://docs.accelbyte.io/gaming-services/services/ams/AMS-watchdog-protocol/):
- WebSocket connection to AMS watchdog (ws://localhost:5555/watchdog)
- Ready/heartbeat/drain signal handling  
- Graceful shutdown on node reclamation

### Customization

Add your game logic to these placeholder methods in `basicds/main.py`:
- `_initialize_server()` - Server startup (network listeners on `self.port`)
- `_run_server_loop()` - Main game loop  
- `_handle_drain()` - Graceful shutdown logic

## References
- [AccelByte AMS Watchdog Protocol](https://docs.accelbyte.io/gaming-services/services/ams/AMS-watchdog-protocol/)
- [AccelByte Multiplayer Servers](https://docs.accelbyte.io/gaming-services/services/ams/)
- [UV Documentation](https://github.com/astral-sh/uv)
- [Python Packaging Guide](https://packaging.python.org/)
