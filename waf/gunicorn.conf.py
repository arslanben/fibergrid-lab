"""Gunicorn configuration for the appliance emulation layer.

The Server response header is written by gunicorn itself (WSGI-level Server
headers are discarded), so patch the module constant before workers fork.
"""
import gunicorn.http.wsgi

gunicorn.http.wsgi.SERVER = "BIG-IP"
