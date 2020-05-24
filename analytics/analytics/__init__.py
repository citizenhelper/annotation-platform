import os
from flask import Flask

from analytics.views import page

__all__ = [
    'create_app'
]


def create_app(config_filename):
    app = Flask(__name__, template_folder=os.path.join('..', 'templates'))

    config_path = os.path.join('..', 'instance', config_filename)
    app.config.from_pyfile(config_path)

    app.register_blueprint(page)

    return app
