# noinspection SpellCheckingInspection
import sqlite3


class F:
    @staticmethod
    def equals(key, value):
        return f' {key}={value} '


class Query:
    def __init__(self, model):
        self.conn = model.conn
        self.table = model.table
        self.filters = []
        self.sorted = False
        self.order_by_lst = []

    def filter(self, **kwargs):
        for k, v in kwargs.items():
            self.filters.append(F.equals(k, v))
        return self

    def order_by(self, **kwargs):
        self.sorted = True
        for k, v in kwargs.items():
            self.order_by_lst.append(f'{k} {v}')
        return self

    def build(self, offset=None, limit=None, project='*'):
        query = f'SELECT {project} FROM {self.table}'
        if len(self.filters) > 0:
            query += ' WHERE '
            query += ' AND '.join(self.filters)
        if self.sorted:
            query += ' ORDER BY '
            query += ' ,'.join(self.order_by_lst)
        if limit is not None:
            query += f' LIMIT {limit}'
        if offset is not None:
            query += f' OFFSET {offset}'
        return query

    def one(self):
        query = self.build()
        c = self.conn.cursor()
        c.execute(query)
        header = [h[0].lower() for h in c.description]
        for o in c:
            return dict(zip(header, o))

    def all(self, offset=None, limit=None):
        query = self.build(offset, limit)
        c = self.conn.cursor()
        c.execute(query)
        operations = []
        header = [h[0].lower() for h in c.description]
        for o in c:
            operations.append(dict(zip(header, o)))
        return operations

    def count(self):
        query = self.build(project='count(*)')
        c = self.conn.cursor()
        c.execute(query)
        return c.fetchone()[0]

    def pagination(self, offset=1, limit=10):
        pc = self.count()
        ip = []
        mp = max(1, offset - limit * 5)
        for i, o in enumerate(range(mp, min(mp + limit * 5, pc + 1), limit)):
            ip += [(o, mp + i)]
        return {
            'items': self.all(offset - 1, limit),
            'iter_pages': ip,
            'offset': offset,
            'page_count': pc,
            'has_next': (offset + limit - 1) < pc,
            'next': offset + limit,
            'has_prev': offset > 1,
            'prev': offset - limit,
        }


# noinspection SpellCheckingInspection
class Model:
    def __init__(self, host='/data/datastore.db', table='document_annotations', conn=None):
        self.host = host
        self.table = table
        if not conn:
            self.conn = sqlite3.connect(self.host)
        else:
            self.conn = conn
        self.query = Query(self)

    def execute(self, query):
        c = self.conn.cursor()
        c.execute(query)
        header = [h[0].lower() for h in c.description]
        for o in c:
            yield dict(zip(header, o))

    def close(self):
        self.conn.close()
