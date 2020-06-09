export FLASK_APP="analytics:create_app('config.py')"

export FLASK_ENV=development

flask run --host=0.0.0.0 --port=5001
