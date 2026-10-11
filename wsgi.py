# Entry point for hosting (Render / PythonAnywhere / gunicorn).
from app import app, initialise
initialise()
