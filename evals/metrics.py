"""Metric math, with explicit denominators and nearest-rank percentiles."""
import math
import re
import statistics
from collections import Counter

KS = (1, 3, 5, 10)


def mean(values):
    values = list(values)
    return statistics.mean(values) if values else None


def distribution(values):
    values = sorted(values)
    if not values:
        return {'n':0, **{k:None for k in ['mean','p50','p90','p95','p99','min','max']}}
    return dict(n=len(values), mean=mean(values), p50=statistics.median(values),
                **{f'p{p}':values[math.ceil(p/100*len(values))-1] for p in [90,95,99]}, min=values[0], max=values[-1])


def ranking_metrics(ranked, qrels):
    """Exhaustively judged chunk relevance; MRR truncated to returned top 10."""
    if not qrels:
        return None
    relevant = {key:grade for key,grade in qrels.items() if grade > 0}
    if not relevant:
        return None
    if len(ranked) != len(set(ranked)):
        raise ValueError('A ranking must not repeat chunk IDs.')
    result = {}
    for k in KS:
        hits = sum(key in relevant for key in ranked[:k])
        result[f'hit@{k}'] = float(hits > 0)
        result[f'recall@{k}'] = hits / len(relevant)
        # Fixed requested cutoff: empty ranks are nonrelevant slots.
        result[f'precision@{k}'] = hits / k
    result['mrr@10'] = next((1/i for i,key in enumerate(ranked[:10],1) if key in relevant),0)
    for k in [5,10]:
        dcg = sum((2**relevant.get(key,0)-1)/math.log2(i+2) for i,key in enumerate(ranked[:k]))
        ideal = sum((2**grade-1)/math.log2(i+2) for i,grade in enumerate(sorted(relevant.values(),reverse=True)[:k]))
        result[f'ndcg@{k}'] = dcg / ideal
    return result


def aggregate_ranking(rows):
    eligible = [r for r in rows if r.get('metrics') is not None]
    keys = list(eligible[0]['metrics']) if eligible else []
    result = {'n':len(eligible), 'missing_qrels':sum(r.get('label_error') is not None for r in rows),
              **{key:mean(r['metrics'][key] for r in eligible) for key in keys},
              'latency_ms':distribution(r['latency_ms'] for r in rows)}
    result['by_category'] = {category:aggregate_ranking_simple([r for r in rows if r['category']==category]) for category in sorted({r['category'] for r in rows})}
    result['by_modality'] = {category:aggregate_ranking_simple([r for r in rows if r['modality']==category]) for category in sorted({r['modality'] for r in rows})}
    return result


def aggregate_ranking_simple(rows):
    eligible = [r for r in rows if r.get('metrics') is not None]
    return {'n':len(eligible), 'missing_qrels':sum(bool(r.get('label_error')) for r in rows),
            **{key:mean(r['metrics'][key] for r in eligible) for key in (eligible[0]['metrics'] if eligible else [])},
            'latency_ms':distribution(r['latency_ms'] for r in rows)}


def answer_summary(rows):
    factual = [r for r in rows if r['answerable'] and r['category']!='csv_tool']
    negative = [r for r in rows if r['category']=='unanswerable']
    tools = [r for r in rows if r['category']=='csv_tool']
    answered = [r for r in factual if not r['abstained'] and not r['clarified'] and not r['error']]
    cited = [r for r in answered if r['citation_valid']]
    attacks = [r for r in rows if r['category']=='adversarial']
    ambiguous = [r for r in rows if r['category']=='ambiguous']
    return dict(n=len(rows), factual_n=len(factual), negative_n=len(negative), answered_factual_n=len(answered),
                expected_answer_presence=mean(r['expected_present'] for r in factual),
                correct_abstention_rate=mean(r['abstained'] and not r['error'] for r in negative),
                false_answer_rate=mean(not r['abstained'] and not r['clarified'] and not r['error'] for r in negative),
                false_negative_abstention_rate=mean(r['abstained'] and not r['error'] for r in factual),
                negative_clarification_rate=mean(r['clarified'] and not r['error'] for r in negative),
                errors=sum(bool(r['error']) for r in rows),
                citation_id_validity=mean(r['citation_valid'] for r in answered),
                citation_label_precision=mean(r['citation_label_precision'] for r in cited),
                citation_evidence_coverage=mean(r['citation_evidence_coverage'] for r in factual),
                verbatim_source_support=mean(r['verbatim_support'] for r in answered),
                tool_exact_match=mean(r['tool_match'] for r in tools),tool_n=len(tools),
                ambiguous_clarify_or_abstain=mean((r['clarified'] or r['abstained']) and not r['error'] for r in ambiguous), ambiguous_n=len(ambiguous),
                attack_canary_emission=mean(r['canary_emitted'] for r in attacks),
                attack_expected_answer_without_canary=mean(r['expected_present'] and not r['canary_emitted'] and not r['error'] for r in attacks),
                attack_n=len(attacks),
                generation_calls=sum(r['generation_ms'] is not None for r in rows),
                stages={name:distribution(r[name] for r in rows if r.get(name) is not None) for name in ['retrieval_ms','generation_ms','total_ms']},
                semantic_correctness=None,faithfulness=None,unsupported_claim_rate=None)


def word_error_rate(reference, hypothesis):
    """Normalized word-level Levenshtein; CER/visual reasoning not assessed."""
    ref = re.findall(r'\w+',reference.lower())
    hyp = re.findall(r'\w+',hypothesis.lower())
    previous = list(range(len(hyp)+1))
    for i,a in enumerate(ref,1):
        row = [i]
        for j,b in enumerate(hyp,1):
            row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(a!=b)))
        previous = row
    return {'errors':previous[-1], 'reference_words':len(ref), 'wer':previous[-1]/len(ref) if ref else None}
