from flask import Flask
from app import app

def handler(request):
    """Handle incoming requests."""
    return app(request)
