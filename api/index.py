import os
import sys

# Ensure the project root directory is on sys.path so 'app' can always be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app

flask_env = os.environ.get('FLASK_ENV')
if not flask_env and os.environ.get('VERCEL'):
    flask_env = 'production'
if not flask_env:
    flask_env = 'development'

app = create_app(flask_env)

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port)
