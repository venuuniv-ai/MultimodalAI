"""Evaluation-only ablations of existing lexical scorers; production stays intact."""
import math
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.app.agent import focus_evidence, search_question
from backend.app.store import tokens

CONFIGS = ('tfidf', 'bm25', 'hybrid_score_sum', 'hybrid_rrf', 'production_search', 'full_pipeline')
SQL = '''SELECT c.id,c.document_id,d.name,c.page,c.text,
(SELECT substr(origin.text,1,70) FROM chunks origin WHERE origin.document_id=c.document_id ORDER BY origin.rowid LIMIT 1)
FROM chunks c JOIN documents d ON d.id=c.document_id WHERE (? IS NULL OR d.id=?)'''


def ablated_search(store, query, config, k=10, document_id=None):
    """Same formulas/order as Store.search, computing only enabled components.

    hybrid_score_sum is an experimental max-normalized 50/50 score sum, NOT
    an existing production stage. Production hybrid is intrinsically RRF.
    """
    with store.connect() as db:
        rows = db.execute(SQL,(document_id,document_id)).fetchall()
    if not rows or not tokens(query):
        return []
    scores = {}
    if config != 'bm25':
        vectorizer = TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True,token_pattern=r'(?u)\b\w+\b')
        matrix = vectorizer.fit_transform([row[4] for row in rows])
        scores['tfidf'] = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
    bags = [Counter(tokens(row[4])) for row in rows]
    terms = set(tokens(query))
    if config != 'tfidf':
        lengths = [sum(bag.values()) for bag in bags]
        average = max(np.mean(lengths),1)
        bm25 = np.zeros(len(rows))
        for term in terms:
            df = sum(term in bag for bag in bags)
            idf = math.log(1+(len(rows)-df+.5)/(df+.5))
            for i,bag in enumerate(bags):
                freq = bag[term]
                bm25[i] += idf*freq*2.5/(freq+1.5*(.25+.75*lengths[i]/average))
        scores['bm25'] = bm25
    if config in {'tfidf','bm25'}:
        combined = scores[config]
    elif config=='hybrid_score_sum':
        combined = sum(.5*s/max(float(s.max()),1e-12) for s in scores.values())
    else:
        combined = np.zeros(len(rows))
        for score in scores.values():
            for rank,i in enumerate(np.argsort(-score)):
                if score[i]>0:
                    combined[i] += 1/(60+rank+1)
    candidates = [int(i) for i in np.argsort(-combined)[:max(k*3,20)] if combined[i]>0]
    if config=='production_replica':
        candidates.sort(key=lambda i:combined[i]+.01*len(terms & set(bags[i]))/len(terms),reverse=True)
    return [dict(zip(('id','document_id','name','page','text','document_title'),rows[i]),score=round(float(combined[i]),5)) for i in candidates[:k]]


def retrieve(store, question, config, document_id=None):
    if config=='production_search':
        return store.search(question,k=10,document_id=document_id)
    if config=='full_pipeline':
        query = search_question(question)
        return focus_evidence(query,store.search(query,k=10,document_id=document_id))[:5]
    return ablated_search(store,question,config,document_id=document_id)
