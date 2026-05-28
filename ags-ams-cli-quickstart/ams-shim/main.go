package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

const (
	watchdogAddr      = "ws://localhost:5555/watchdog"
	heartbeatInterval = 15 * time.Second
	portPollInterval  = 500 * time.Millisecond
	portFallbackDelay = 5 * time.Second
)

func main() {
	log.SetPrefix("[amsshim] ")
	log.SetFlags(log.Ltime)

	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: amsshim <executable> [args...]")
		os.Exit(1)
	}

	executable := os.Args[1]
	childArgs := os.Args[2:]

	var dsid string
	var port int

	for _, arg := range childArgs {
		switch {
		case strings.HasPrefix(arg, "-dsid="):
			dsid = strings.TrimPrefix(arg, "-dsid=")
		case strings.HasPrefix(arg, "-port="):
			p, err := strconv.Atoi(strings.TrimPrefix(arg, "-port="))
			if err != nil {
				log.Fatalf("invalid -port value: %v", err)
			}
			port = p
		}
	}

	if dsid == "" {
		log.Fatal("missing required -dsid argument")
	}

	ensureExecutable(executable)

	cmd := exec.Command(executable, childArgs...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stdout

	if err := cmd.Start(); err != nil {
		log.Fatalf("failed to start %q: %v", executable, err)
	}
	log.Printf("started %s (pid %d)", executable, cmd.Process.Pid)

	childDone := make(chan int, 1)
	go func() {
		code := 0
		if err := cmd.Wait(); err != nil {
			if ee, ok := err.(*exec.ExitError); ok {
				code = ee.ExitCode()
			} else {
				code = 1
			}
		}
		childDone <- code
	}()

	// Forward OS signals to child process.
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
	go func() {
		for sig := range sigCh {
			if err := cmd.Process.Signal(sig); err != nil {
				log.Printf("signal forward error: %v", err)
			}
		}
	}()

	hdr := http.Header{"ams-dsid": []string{dsid}}
	conn, _, err := websocket.DefaultDialer.Dial(watchdogAddr, hdr)
	if err != nil {
		log.Fatalf("failed to connect to watchdog: %v", err)
	}
	defer conn.Close()
	log.Printf("connected to watchdog")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var wsMu sync.Mutex
	send := func(v interface{}) error {
		wsMu.Lock()
		defer wsMu.Unlock()
		return conn.WriteJSON(v)
	}

	go runHeartbeat(ctx, send, cancel)

	drainCh := make(chan struct{}, 1)
	go runReceiver(ctx, conn, drainCh, cancel)

	go func() {
		waitForPort(port, ctx)
		if ctx.Err() != nil {
			return
		}
		log.Printf("sending ready signal")
		if err := send(map[string]interface{}{
			"ready": map[string]string{"dsid": dsid},
		}); err != nil {
			log.Printf("ready send error: %v", err)
		}
	}()

	select {
	case code := <-childDone:
		log.Printf("child exited with code %d", code)
		cancel()
		os.Exit(code)

	case <-drainCh:
		log.Printf("drain received, sending SIGTERM to child")
		if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
			log.Printf("SIGTERM error: %v", err)
		}
		code := <-childDone
		log.Printf("child exited with code %d after drain", code)
		os.Exit(code)

	case <-ctx.Done():
		log.Printf("watchdog connection lost, terminating child")
		if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
			log.Printf("SIGTERM error: %v", err)
		}
		code := <-childDone
		os.Exit(code)
	}
}

func runHeartbeat(ctx context.Context, send func(interface{}) error, cancel context.CancelFunc) {
	t := time.NewTicker(heartbeatInterval)
	defer t.Stop()
	for {
		select {
		case <-t.C:
			if err := send(map[string]interface{}{"heartbeat": struct{}{}}); err != nil {
				log.Printf("heartbeat error: %v", err)
				cancel()
				return
			}
		case <-ctx.Done():
			return
		}
	}
}

func runReceiver(ctx context.Context, conn *websocket.Conn, drainCh chan<- struct{}, cancel context.CancelFunc) {
	for {
		_, data, err := conn.ReadMessage()
		if err != nil {
			if ctx.Err() == nil {
				log.Printf("watchdog read error: %v", err)
				cancel()
			}
			return
		}
		var msg map[string]json.RawMessage
		if err := json.Unmarshal(data, &msg); err != nil {
			log.Printf("invalid watchdog message: %v", err)
			continue
		}
		if _, ok := msg["drain"]; ok {
			log.Printf("drain signal received from watchdog")
			select {
			case drainCh <- struct{}{}:
			default:
			}
			return
		}
	}
}

func waitForPort(port int, ctx context.Context) {
	if port <= 0 {
		select {
		case <-time.After(portFallbackDelay):
		case <-ctx.Done():
		}
		return
	}

	portHex := fmt.Sprintf("%04X", port)
	tick := time.NewTicker(portPollInterval)
	defer tick.Stop()

	for {
		select {
		case <-tick.C:
			if isPortBound(portHex) {
				return
			}
		case <-ctx.Done():
			return
		}
	}
}

func ensureExecutable(path string) {
	info, err := os.Stat(path)
	if err != nil {
		log.Fatalf("cannot stat %q: %v", path, err)
	}
	if info.Mode()&0111 == 0 {
		if err := os.Chmod(path, info.Mode()|0111); err != nil {
			log.Fatalf("cannot chmod %q: %v", path, err)
		}
		log.Printf("set executable bit on %s", path)
	}
}

// isPortBound checks /proc/net/{tcp,tcp6,udp,udp6} for the port appearing as
// a local address, indicating any process has bound to it.
func isPortBound(portHex string) bool {
	suffix := ":" + portHex
	for _, path := range []string{
		"/proc/net/tcp",
		"/proc/net/tcp6",
		"/proc/net/udp",
		"/proc/net/udp6",
	} {
		f, err := os.Open(path)
		if err != nil {
			continue
		}
		s := bufio.NewScanner(f)
		s.Scan() // skip header line
		found := false
		for s.Scan() {
			if fields := strings.Fields(s.Text()); len(fields) >= 2 && strings.HasSuffix(fields[1], suffix) {
				found = true
				break
			}
		}
		f.Close()
		if found {
			return true
		}
	}
	return false
}
