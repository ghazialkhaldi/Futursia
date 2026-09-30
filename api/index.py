# Vercel runs the files in the api/ folder. This one just loads the Flask app
# from app.py (one folder up) so Vercel can use it.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import app  # noqa: E402
