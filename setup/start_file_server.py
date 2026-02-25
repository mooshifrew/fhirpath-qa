#!/usr/bin/env python3
"""
Start HTTP server to serve FHIR data files to Docker containers.

This script starts a local HTTP server that serves the NDJSON files
from the compose/data directory so they can be accessed by Docker containers
during the import process.
"""

import os
import sys
import mimetypes
import http.server
import socketserver
from pathlib import Path

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import HTTP_SERVER_HOST, HTTP_SERVER_PORT, HTTP_SERVER_DIR
except ImportError:
    print("Error: config.py not found. Please ensure config.py exists.")
    sys.exit(1)


def start_server():
    """Start the HTTP server to serve files to Docker."""

    # Change to the data directory
    if not HTTP_SERVER_DIR.exists():
        print(f"Error: Data directory not found: {HTTP_SERVER_DIR}")
        print("Please ensure the compose/data directory exists with NDJSON files.")
        sys.exit(1)

    os.chdir(HTTP_SERVER_DIR)

    # Add MIME type for NDJSON files
    mimetypes.add_type("application/fhir+ndjson", ".ndjson")
    mimetypes.add_type("application/json", ".json")

    # Create server
    handler = http.server.SimpleHTTPRequestHandler

    try:
        with socketserver.TCPServer(
            (HTTP_SERVER_HOST, HTTP_SERVER_PORT), handler
        ) as httpd:
            print(f"Starting HTTP server...")
            print(f"Host: {HTTP_SERVER_HOST}")
            print(f"Port: {HTTP_SERVER_PORT}")
            print(f"Serving files from: {HTTP_SERVER_DIR}")
            print(f"URL: http://{HTTP_SERVER_HOST}:{HTTP_SERVER_PORT}")
            print()
            print("This server is needed for Docker containers to access NDJSON files.")
            print("Keep this running while importing data.")
            print("Press Ctrl+C to stop the server.")
            print("-" * 60)

            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"Error: Port {HTTP_SERVER_PORT} is already in use.")
            print("Either stop the existing server or change the port in config.py")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_server()
