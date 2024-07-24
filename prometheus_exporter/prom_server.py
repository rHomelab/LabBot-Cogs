import logging
import socket
import threading
from functools import partial
from typing import Protocol
from wsgiref.simple_server import WSGIRequestHandler, make_server

from prometheus_client import CollectorRegistry, make_wsgi_app

logger = logging.getLogger("red.rhomelab.prom.server")


class _SilentHandler(WSGIRequestHandler):
    """WSGI handler that does not log requests."""

    def log_message(self, format, *args):
        """Log nothing."""


class MetricsServer(Protocol):
    def serve(self) -> None: ...

    def stop(self) -> None: ...


class PrometheusMetricsServer(MetricsServer, Protocol):
    @property
    def registry(self) -> CollectorRegistry: ...


class promServer(PrometheusMetricsServer):
    def __init__(self, addr: str, port: int):
        self.addr = addr
        self.port = port

        self.server_thread = None
        self.server = None
        self._registry = self._create_registry()

    def _create_registry(self) -> CollectorRegistry:
        return CollectorRegistry()

    def _get_best_family(self):
        """Automatically select address family depending on address"""
        infos = socket.getaddrinfo(self.addr, self.port)
        family, _, _, _, sockaddr = next(iter(infos))
        return family, sockaddr[0]

    @property
    def registry(self) -> CollectorRegistry:
        return self._registry

    def serve(self) -> None:
        """Starts a WSGI server for prometheus metrics as a daemon thread."""
        logger.debug("deploying prometheus server")
        app = make_wsgi_app(self._registry)
        logger.info(f"starting server on {self.addr}:{self.port}")
        self.server = make_server(self.addr, self.port, app, handler_class=_SilentHandler)
        self.server_thread = threading.Thread(target=partial(self.server.serve_forever, 0.5))
        self.server_thread.daemon = True
        self.server_thread.start()
        logger.debug("server thread started")

    def stop(self) -> None:
        logger.debug("shutting down prom server")
        logger.debug("server thread exists: %s, server exists: %s", self.server_thread is not None, self.server is not None)
        if self.server_thread is not None and self.server is not None:
            logger.debug("prom server running, stopping...")
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join()
            logger.debug("prom server thread joined")
