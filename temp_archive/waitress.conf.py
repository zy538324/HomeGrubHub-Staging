# Waitress Configuration for HomeGrubHub Production
# Configuration values for production deployment

# Server configuration
HOST = '127.0.0.1'
PORT = 8050

# Performance settings
THREADS = 6  # Number of threads to handle requests
CONNECTION_LIMIT = 100  # Maximum number of concurrent connections
CLEANUP_INTERVAL = 30  # Cleanup interval in seconds
CHANNEL_TIMEOUT = 120  # Channel timeout in seconds

# Timeouts
SOCKET_TIMEOUT = 60  # Socket timeout
TASK_DISPATCHER_TIMEOUT = 60  # Task dispatcher timeout

# Logging
LOG_SOCKET_ERRORS = True
LOG_UNTRUSTED_PROXY_HEADERS = False

# Security
EXPOSE_TRACEBACKS = False  # Don't expose tracebacks in production

# URL scheme (for reverse proxy setups)
URL_SCHEME = 'http'  # Use 'https' if behind SSL terminating proxy

# Additional settings for production
SEND_BYTES = 8192  # Number of bytes to send at once
RECV_BYTES = 8192  # Number of bytes to receive at once

# Asyncore settings
ASYNCORE_USE_POLL = True  # Use poll() instead of select() on Unix

# IPv4/IPv6 settings
IPV4 = True
IPV6 = False

# Backlog
LISTEN_BACKLOG = 1024  # Socket listen backlog

# Buffer size
OUTBUF_OVERFLOW = 1048576  # 1MB buffer overflow threshold

# Connection settings
OUTBUF_HIGH_WATERMARK = 16777216  # 16MB high watermark
OUTBUF_OVERFLOW_LOGGER = None  # Logger for buffer overflow

# Request settings
MAX_REQUEST_HEADER_SIZE = 262144  # 256KB max header size
MAX_REQUEST_BODY_SIZE = 1073741824  # 1GB max body size (for file uploads)
