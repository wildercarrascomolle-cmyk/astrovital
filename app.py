"""Punto de entrada. Local: python app.py · Render: gunicorn app:app"""
import os

from astrovital import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  AstroVital -> http://127.0.0.1:{port}\n")
    app.run(debug=True, port=port)
