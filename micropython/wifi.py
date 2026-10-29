"""
Minimal MicroPython WiFi + JSON sender library for the ESP32.

Usage:
    from wifi import WiFi

    wifi = WiFi("MySSID", "MyPassword")
    wifi.connect()
    status = wifi.post_json("192.168.1.50", {"temperature": 21.5}, port=5000, path="/data")
    print(status)  # HTTP status code, e.g. 200
"""

import json
import socket
import time
import network


class WiFi:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.sta = network.WLAN(network.STA_IF)

    def connect(self, timeout=15):
        """Connect to the WiFi network. Raises OSError on timeout."""
        self.sta.active(True)
        if self.sta.isconnected():
            return self.ip

        self.sta.connect(self.ssid, self.password)
        start = time.ticks_ms()
        while not self.sta.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > timeout * 1000:
                self.sta.disconnect()
                raise OSError("WiFi connection timed out")
            time.sleep_ms(200)
        return self.ip

    def disconnect(self):
        self.sta.disconnect()
        self.sta.active(False)

    def is_connected(self):
        return self.sta.isconnected()

    @property
    def ip(self):
        return self.sta.ifconfig()[0]

    def ensure_connected(self):
        """Reconnect if the connection was lost."""
        if not self.sta.isconnected():
            self.connect()

    def post_json(self, host, data, port=80, path="/", timeout=5):
        """
        Send `data` (dict or list) as JSON in an HTTP POST request.
        Returns the HTTP status code of the response.
        """
        self.ensure_connected()

        body = json.dumps(data).encode()
        header = (
            "POST {} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(path, host, len(body)).encode()

        addr = socket.getaddrinfo(host, port)[0][-1]
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect(addr)
            s.sendall(header + body)
            response = s.recv(256)
        finally:
            s.close()

        # First line looks like: b"HTTP/1.1 200 OK"
        try:
            return int(response.split(b" ", 2)[1])
        except (IndexError, ValueError):
            raise OSError("Invalid response from server")

    def send_raw_json(self, host, port, data, timeout=5):
        """
        Send `data` as a plain JSON string over a raw TCP socket
        (no HTTP), followed by a newline.
        """
        self.ensure_connected()

        addr = socket.getaddrinfo(host, port)[0][-1]
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect(addr)
            s.sendall(json.dumps(data).encode() + b"\n")
        finally:
            s.close()