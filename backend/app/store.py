import csv
import io
import json
import math
import os
import re
import sqlite3
import threading
import uuid
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED = {'.txt', '.md', '.pdf', '.csv', '.png', '.jpg', '.jpeg'}
STOP = set('a an the is are was were be to of in on for and or with what which how does do can my about who whose when where why please tell me s'.split())


def tokens(text):
    return [t for t in re.findall(r'\b\w+\b', text.lower()) if t not in STOP]


def extract(name, content):
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError('Supported formats: TXT, MD, PDF, CSV, PNG, JPEG.')
    if suffix == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise ValueError('Encrypted PDFs are not supported.')
        return [(i + 1, p.extract_text() or '') for i, p in enumerate(reader.pages)], None
    if suffix in {'.png', '.jpg', '.jpeg'}:
        import pytesseract
        from PIL import Image
        try:
            with Image.open(io.BytesIO(content)) as picture:
                picture.load()
                text = pytesseract.image_to_string(picture)
        except pytesseract.TesseractNotFoundError:
            raise ValueError('Image OCR needs Tesseract. Install with: brew install tesseract')
        return [(1, text)], None
    text = content.decode('utf-8-sig')
    if suffix == '.csv':
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('CSV needs a header with unique column names.')
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError('CSV rows must match the header.')
        return [(i + 1, '; '.join(f'{key}: {value}' for key, value in row.items())) for i, row in enumerate(rows)], {'columns': reader.fieldnames, 'rows': rows}
    return [(1, text)], None


def chunks(text, size=180, overlap=35):
    words = text.split()
    for start in range(0, len(words), size - overlap):
        yield ' '.join(words[start:start + size])
        if start + size >= len(words):
            break


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('RESEARCH_DESK_DB') or ROOT / 'data/store.sqlite3')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS documents
                (id TEXT PRIMARY KEY, name TEXT, kind TEXT, table_json TEXT);
                CREATE TABLE IF NOT EXISTS chunks
                (id TEXT PRIMARY KEY, document_id TEXT, page INTEGER, text TEXT);''')

    def connect(self):
        return sqlite3.connect(self.path)

    def ingest(self, name, content):
        name = Path(name.replace('\\', '/')).name
        pages, table = extract(name, content)
        doc_id = uuid.uuid4().hex
        records = [(uuid.uuid4().hex, doc_id, page, part) for page, text in pages for part in chunks(text) if part.strip()]
        if not records:
            raise ValueError('No readable text found. Scanned PDFs need external OCR first.')
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO documents VALUES (?,?,?,?)', (doc_id, name, Path(name).suffix[1:], json.dumps(table) if table else None))
            db.executemany('INSERT INTO chunks VALUES (?,?,?,?)', records)
        return {'id': doc_id, 'name': name, 'kind': Path(name).suffix[1:], 'chunks': len(records)}

    def documents(self):
        with self.connect() as db:
            rows = db.execute('SELECT d.id,d.name,d.kind,COUNT(c.id) FROM documents d LEFT JOIN chunks c ON c.document_id=d.id GROUP BY d.id ORDER BY d.name').fetchall()
        return [dict(zip(('id', 'name', 'kind', 'chunks'), row)) for row in rows]

    def delete(self, doc_id):
        with self.lock, self.connect() as db:
            cursor = db.execute('DELETE FROM documents WHERE id=?', (doc_id,))
            db.execute('DELETE FROM chunks WHERE document_id=?', (doc_id,))
        return cursor.rowcount > 0

    def search(self, query, k=5, document_id=None):
        with self.connect() as db:
            rows = db.execute('SELECT c.id,c.document_id,d.name,c.page,c.text,(SELECT substr(origin.text,1,70) FROM chunks origin WHERE origin.document_id=c.document_id ORDER BY origin.rowid LIMIT 1) FROM chunks c JOIN documents d ON d.id=c.document_id WHERE (? IS NULL OR d.id=?)', (document_id, document_id)).fetchall()
        if not rows or not tokens(query):
            return []
        texts = [row[4] for row in rows]
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r'(?u)\b\w+\b')
        matrix = vectorizer.fit_transform(texts)
        cosine = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
        bags = [Counter(tokens(t)) for t in texts]
        lengths = [sum(bag.values()) for bag in bags]
        average = max(np.mean(lengths), 1)
        terms = set(tokens(query))
        bm25 = np.zeros(len(rows))
        for term in terms:
            df = sum(term in bag for bag in bags)
            idf = math.log(1 + (len(rows) - df + .5) / (df + .5))
            for i, bag in enumerate(bags):
                freq = bag[term]
                bm25[i] += idf * freq * 2.5 / (freq + 1.5 * (.25 + .75 * lengths[i] / average))
        fusion = np.zeros(len(rows))
        for scores in (cosine, bm25):
            for rank, i in enumerate(np.argsort(-scores)):
                if scores[i] > 0:
                    fusion[i] += 1 / (60 + rank + 1)
        candidates = [int(i) for i in np.argsort(-fusion)[:max(k * 3, 20)] if fusion[i] > 0]
        # Small deterministic lexical reranker; no neural reranker or embeddings claimed.
        candidates.sort(key=lambda i: fusion[i] + .01 * len(terms & set(bags[i])) / len(terms), reverse=True)
        return [{'id': rows[i][0], 'document_id': rows[i][1], 'name': rows[i][2], 'page': rows[i][3], 'text': rows[i][4], 'document_title': rows[i][5], 'score': round(float(fusion[i]), 5)} for i in candidates[:k]]

    def csv_columns(self, doc_id):
        with self.connect() as db:
            record = db.execute('SELECT table_json FROM documents WHERE id=?', (doc_id,)).fetchone()
        if not record or not record[0]:
            raise ValueError('Choose an indexed CSV document.')
        table = json.loads(record[0])
        numeric = []
        for column in table['columns']:
            for row in table['rows']:
                try:
                    if math.isfinite(float(row[column])):
                        numeric.append(column)
                        break
                except (ValueError, TypeError):
                    continue
        return {'columns': table['columns'], 'numeric_columns': numeric, 'rows': len(table['rows'])}

    def csv_tool(self, doc_id, operation, column=None):
        with self.connect() as db:
            row = db.execute('SELECT table_json FROM documents WHERE id=?', (doc_id,)).fetchone()
        if not row or not row[0]:
            raise ValueError('Choose an indexed CSV document.')
        table = json.loads(row[0])
        if operation == 'count':
            return {'rows': len(table['rows']), 'columns': table['columns']}
        if column not in table['columns']:
            raise ValueError('Choose a column: ' + ', '.join(table['columns']))
        values = []
        for row in table['rows']:
            try:
                value = float(row[column])
                if math.isfinite(value):
                    values.append(value)
            except (TypeError, ValueError):
                pass
        if not values:
            raise ValueError('The selected column has no finite numeric values.')
        return {'column': column, 'count': len(values), 'skipped': len(table['rows']) - len(values), 'sum': sum(values), 'mean': sum(values) / len(values), 'min': min(values), 'max': max(values)}
