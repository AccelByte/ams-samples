BINARY   := amsshim
GOFLAGS  := -trimpath
LDFLAGS  := -ldflags="-s -w"

.PHONY: build clean

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build $(GOFLAGS) $(LDFLAGS) -o $(BINARY) .

clean:
	rm -f $(BINARY)
