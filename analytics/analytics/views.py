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


# @page.route('/')
# def index_page():
#     return render_template('index.html', title=get_title('Home'), active_page='index')


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


@page.route('/')
def home_page():
    statistics = {
        'annotations': {},
        'documents': {'count': 'N/A'},
        'users': [],
        'agreement': [],
    }
    path = '/Users/yasas/Documents/Docker/data/doccano.db'
    model = Model(path, 'api_document')
    document_stat_q = '''SELECT COUNT(DISTINCT a.document_id) completed, COUNT(DISTINCT d.id) count, (CAST(COUNT(DISTINCT a.document_id) * 100 AS REAL) / CAST(COUNT(DISTINCT d.id) AS REAL)) percentage from api_document d LEFT JOIN api_documentannotation a ON (a.document_id=d.id);'''
    for c in model.execute(document_stat_q):
        statistics['annotations'] = c
        break
    user_progress_q = '''SELECT u.username username, COUNT(DISTINCT d.id) total, COUNT(DISTINCT a.document_id) completed, (CAST(COUNT(DISTINCT a.document_id) * 100 AS REAL) / CAST(COUNT(DISTINCT d.id) AS REAL)) percentage  from
    auth_user u
        JOIN api_project_users q ON (q.user_id=u.id)
        JOIN api_project p ON (q.project_id=p.id)
        JOIN api_document d ON (d.project_id=p.id)
        JOIN api_documentannotation a ON (a.user_id=u.id)
    GROUP BY u.id;'''
    for c in model.execute(user_progress_q):
        statistics['users'].append(c)
    model.close()
    return render_template('statistics.html', title=get_title('Home'), active_page='index', statistics=statistics)
