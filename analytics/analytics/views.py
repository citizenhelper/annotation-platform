import os
import io
import json

from flask import Blueprint, send_from_directory, render_template, redirect, url_for, jsonify, request, Response

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import base64

from analytics.models import Model
from analytics.shared import auth

sns.set()

__all__ = [
    'page'
]

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


@page.route('/actions')
@auth.login_required
def actions_page_redirect():
    return redirect(url_for('page.actions_page', offset=1))


def build_plot(x, y):
    img = io.BytesIO()
    plt.plot(x, y)
    plt.xticks(fontsize=8, rotation=45)
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    return plot_url


@page.route('/actions/<int:offset>')
@auth.login_required
def actions_page(offset=1):
    path = page.config['SQLITE_PATH']
    model = Model(path)
    pagination = model.query \
        .order_by(timestamp='DESC').pagination(offset)
    actions = model.query.filter(username='"stevepeterson2@gmail.com"') \
        .order_by(timestamp='ASC').all()
    actions = pd.DataFrame(actions)
    actions.index = pd.to_datetime(actions.timestamp)
    actions = actions[actions.index < '2020-05-31']
    data = actions[actions.operation == 'CREATE'].resample('5T').agg({'operation': 'size'})
    plot_url = build_plot(data.index, data.operation)
    return render_template('actions.html', title=get_title('Home'), active_page='actions', pagination=pagination,
                           plot_url=plot_url)


@page.route('/documents')
@auth.login_required
def documents_page_redirect():
    return redirect(url_for('page.documents_page', offset=1))


@page.route('/dataset')
@auth.login_required
def dataset_page():
    dataset = {}
    path = '/home/ywijesu/annotation_data/doccano.db'
    model = Model(path, 'api_annotations')
    expert_username = request.args.get('expert', None)
    dataset_q = '''SELECT d.text text, d.meta meta, l.text label, u.username user FROM api_documentannotation a 
        JOIN api_document d ON (a.document_id=d.id)
        JOIN api_label l ON (a.label_id=l.id)
        JOIN auth_user u ON (a.user_id=u.id)
        JOIN api_project p ON (d.project_id=p.id)
        WHERE p.name LIKE 'Annotations - Activation #1%' AND a.user_id != 1 AND a.user_id != 22
        '''
    for ix, c in enumerate(model.execute(dataset_q)):
        metadata = json.loads(c['meta'])
        tweet_id = metadata['id']
        created_at = metadata['created_at']
        label = c['label']
        username = c['user']
        annotations = {}
        if username not in annotations:
            annotations[username] = {
                'Risks': False,
                'Prevention': False,
                'Negative Sentiment': False,
                'Positive Sentiment': False,
                'Irrelevant': False,
            }
        assert label in annotations[username], f'Invalid Label Type. Found {label}.'
        annotations[username].update({label: True})
        if tweet_id not in dataset:
            dataset[tweet_id] = {
                'annotations': {},
                'text': c['text'],
            }
        dataset[tweet_id]['annotations'].update(annotations)
    results = []
    invalid = 0
    skipped = 0
    for tweet_id, data in dataset.items():
        total_voters = len(data['annotations'].items())
        label_vote = {
            'Risks': 0,
            'Prevention': 0,
            'Irrelevant': 0,
        }
        sentiment_vote = {
            'Negative Sentiment': 0,
            'Positive Sentiment': 0,
        }
        annotated_by_expert = False
        for user_id, annotation in data['annotations'].items():
            if user_id == expert_username:
                annotated_by_expert = True
            for key, value in annotation.items():
                if value and key in label_vote:
                    label_vote[key] += 1
                if value and key in sentiment_vote:
                    sentiment_vote[key] += 1
        if annotated_by_expert:
            # Document is annotated by an expert - ignore this document
            continue
        if total_voters < 3:
            # skip documents that are annotated by only 2
            skipped += 1
            continue
        labels = []  # Cant decide based on the data available (undetermined)
        if label_vote['Irrelevant'] > 1:
            # if majority agrees that it is irrelevant then mark as irrelevant
            labels.append('Irrelevant')
        else:
            # else it should be relevant (-> ether Risk or Prevention or Both) (/ undetermined see next code scope)
            if label_vote['Risks'] > 1:
                labels.append('Risks')
            if label_vote['Prevention'] > 1:
                labels.append('Prevention')
        if len(labels) == 0:
            # Skip undetermined tweet
            invalid += 1
            continue
        # Add sentiment labels if they are at least annotated by two annotators
        if sentiment_vote['Negative Sentiment'] > 1:
            labels.append('Negative Sentiment')
        if sentiment_vote['Positive Sentiment'] > 1:
            labels.append('Positive Sentiment')
        label_vote.update(sentiment_vote)
        result = {
            'tweet_id': tweet_id,
            'votes': label_vote,
            'labels': labels,
        }
        result.update(data)
        results.append(result)
    print(f'We found {invalid} invalid annotations. Additionally, '
          f'we skipped {skipped} annotations to improve the dataset quality.')
    return_type = request.args.get('type', None)
    if return_type == 'json':
        return jsonify(results)
    if return_type == 'jsonl':
        json_lines = []
        for result in results:
            json_lines.append(json.dumps(result))
        return Response('\n'.join(json_lines), mimetype='text/json')
    if return_type == 'csv':
        payload = pd.DataFrame(results).to_csv()
        return Response(payload, mimetype='text/csv')
    else:
        payload = 'Please specify the return type parameter. \n Example: /dataset?type=(jsonl|csv|json)'
        return Response(payload, mimetype='text/plain; charset=utf-8')


@page.route('/documents/<int:offset>')
@auth.login_required
def documents_page(offset=1):
    path = '/home/ywijesu/annotation_data/doccano.db'
    model = Model(path, 'api_document')
    pagination = model.query.pagination(offset)
    model.close()
    return render_template('documents.html', title=get_title('Home'), active_page='documents', pagination=pagination)


@page.route('/')
@auth.login_required
def home_page():
    statistics = {
        'annotations': [],
        'documents': {'count': 'N/A'},
        'users': [],
        'agreement': [],
    }
    path = '/home/ywijesu/annotation_data/doccano.db'
    model = Model(path, 'api_document')
    user_progress_q = '''SELECT u.username username, u.id id, COUNT(DISTINCT d.id) total, COUNT(DISTINCT a.document_id) completed, (CAST(COUNT(DISTINCT a.document_id) * 100 AS REAL) / CAST(COUNT(DISTINCT d.id) AS REAL)) percentage  from
    auth_user u
        JOIN api_project_users q ON (q.user_id=u.id)
        JOIN api_project p ON (q.project_id=p.id)
        JOIN api_document d ON (d.project_id=p.id)
        JOIN api_documentannotation a ON (a.user_id=u.id)
    WHERE p.name LIKE 'Annotations - Activation #1%' AND a.user_id != 1 AND a.user_id != 22
    GROUP BY u.id;'''
    for c in model.execute(user_progress_q):
        statistics['users'].append(c)
    document_progress_q = '''SELECT a.document_id, COUNT(DISTINCT a.user_id) num_annotators from
     api_project p
        JOIN api_document d ON (d.project_id=p.id)
        JOIN api_documentannotation a ON (a.document_id=d.id)
    WHERE p.name LIKE 'Annotations - Activation #1%' AND a.user_id != 1 AND a.user_id != 22
    GROUP BY a.document_id
    '''
    annotations = {}
    for ix, c in enumerate(model.execute(document_progress_q)):
        num_ = c['num_annotators']
        if num_ not in annotations:
            annotations[num_] = 0
        annotations[num_] += 1
    for x, y in annotations.items():
        statistics['annotations'].append({
            'annotation_count': x,
            'frequency': y,
        })
    model.close()
    return render_template('statistics.html', title=get_title('Home'), active_page='index', statistics=statistics)
