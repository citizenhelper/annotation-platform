import os

from flask import Blueprint, send_from_directory, render_template, redirect, url_for

__all__ = [
    'page'
]

from analytics.models import Model

page = Blueprint('page', __name__)


def get_title(suffix=None):
    title = page.config.get('TITLE', 'CitizenHelper')
    if suffix is None:
        return title
    return f'{title} - {suffix}'


@page.record
def record_params(setup_state):
    app = setup_state.app
    page.config = dict([(key, value) for (key, value) in app.config.items()])


@page.route('/favicon.ico')
def favicon():
    static_path = os.path.join(page.root_path, 'static')
    return send_from_directory(static_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@page.route('/')
def index_page():
    return render_template('index.html', title=get_title('Home'), active_page='index')


@page.route('/actions')
def actions_page_redirect():
    return redirect(url_for('page.actions_page', offset=1))


@page.route('/actions/<int:offset>')
def actions_page(offset=1):
    path = page.config['SQLITE_PATH']
    model = Model(path)
    pagination = model.query.order_by(timestamp='DESC').pagination(offset)
    model.close()
    return render_template('actions.html', title=get_title('Home'), active_page='actions', pagination=pagination)


@page.route('/documents')
def documents_page_redirect():
    return redirect(url_for('page.documents_page', offset=1))


@page.route('/documents/<int:offset>')
def documents_page(offset=1):
    path = '/Users/yasas/Documents/Docker/data/doccano.db'
    model = Model(path, 'api_document')
    pagination = model.query.pagination(offset)
    model.close()
    return render_template('documents.html', title=get_title('Home'), active_page='documents', pagination=pagination)


@page.route('/statistics')
def statistics_page():
    statistics = {
        'annotations': {
            'count': 0,
            'percentage': 0,
        },
        'documents': {
            'count': 0
        },
        'users': []
    }
    path = '/Users/yasas/Documents/Docker/data/doccano.db'
    model = Model(path, 'api_documentannotation')
    statistics['annotations']['count'] = model.query.count()
    user_model = Model(table='auth_user', conn=model.conn)
    documents_model = Model(table='api_document', conn=model.conn)
    statistics['documents']['count'] = documents_model.query.count()
    try:
        statistics['annotations']['percentage'] = statistics['annotations']['count'] * 100 / statistics['documents']['count']
    except:
        pass
    for u in user_model.query.all():
        user_id = u['id']
        username = u['username']
        statistics['users'].append({
            'username': username,
            'annotations': {
                'count': model.query.filter(user_id=user_id).count()
            }
        })
    model.close()
    return render_template('statistics.html', title=get_title('Home'), active_page='annotations', statistics=statistics)
