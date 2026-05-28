package main

import (
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

// This is a simple stub for testing ams-shim that simply starts and listens on the specified port.
func main() {
	log.SetPrefix("[stubds] ")
	log.SetFlags(log.Ltime)

	var port string
	for _, arg := range os.Args[1:] {
		if strings.HasPrefix(arg, "-port=") {
			port = strings.TrimPrefix(arg, "-port=")
		}
	}

	if port == "" {
		log.Fatal("missing required -port argument")
	}

	conn, err := net.ListenPacket("udp", ":"+port)
	if err != nil {
		log.Fatalf("failed to bind UDP port %s: %v", port, err)
	}
	defer conn.Close()

	log.Printf("bound UDP port %s", port)
	log.Printf("args: %v", os.Args[1:])

	// Simulate periodic server activity on stdout and stderr.
	go func() {
		for i := 1; ; i++ {
			fmt.Printf("[stubds] tick %d\n", i)
			time.Sleep(5 * time.Second)
		}
	}()

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGTERM, syscall.SIGINT)
	s := <-sig
	log.Printf("received %s, shutting down", s)
}
