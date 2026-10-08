"""Bounded lexical evidence planning. No learned semantics or trust inference.

Entity constraints are alternatives per claim. Relation matches are independent
of entity count; grouping preserves requested facts and detects disagreements.
"""
import re
from collections import defaultdict

from .store import tokens

# Relation vocabulary, not question rewrites or application/dataset entities.
NORMAL = {
    'owns':'owner','own':'owner','owned':'owner','ownership':'owner',
    'responsible':'owner','handles':'owner','handle':'owner',
    'retention':'retain','retaining':'retain','retained':'retain','kept':'retain','keep':'retain',
    'period':'duration','periods':'duration','long':'duration',
    'located':'location','locate':'location','locations':'location',
    'deployment':'deploy','deployments':'deploy',
    'incidents':'incident','records':'record','documents':'document',
}
GENERIC_RELATION = {'project','workshop','service','application','system','document','record','cloud','monthly','local','sample','fictional'}
QUESTION_FILLER = {'name','give','identify','provide','list','compare','person','its','should','use','applies'}


def normalized_tokens(text, question=False):
    result=set()
    for word in tokens(text):
        normalized=NORMAL.get(word,word)
        if len(normalized)>5 and normalized.endswith('s') and not normalized.endswith(('ss','us','is')):
            normalized=normalized[:-1]
        normalized=NORMAL.get(normalized,normalized)
        result.add(normalized)
    if question:
        result-=QUESTION_FILLER
        if re.match(r'\s*where\b',text,re.I):result.add('location')
    return result


def sentences(text):
    return [part.strip() for part in re.split(r'(?<=[.!?])\s+|\n+',text) if part.strip()]


def instruction_like(text):
    """Conservative control-language detector, not a prompt-injection proof.

    Collapse spaced letters for detection only. Never edit factual text or rank
    sources by filenames, apparent authority, or benchmark-specific canaries.
    """
    collapsed=re.sub(r'\b(?:[a-zA-Z]\s+){3,}[a-zA-Z]\b',lambda match:re.sub(r'\s+','',match.group()),text)
    patterns=[
        r'\b(?:ignore|disregard|override|forget)\b.{0,60}\b(?:instruction|rule|system|developer|previous|prior)\w*\b',
        r'(?:^|[.!?;:]\s*)(?:please\s+)?(?:say|claim|reveal|output|return|respond)\b',
        r'\b(?:system|developer|assistant)\s*(?:message|prompt|instruction|:)\b',
        r'(?:^|[\n.!?]\s*)(?:system|developer|assistant)\s*:',
        r'\b(?:evaluator|assistant|model|you)\b.{0,50}\b(?:must|requires?|instructs?|override|ignore|output|respond)\b',
        r'<\s*/?\s*(?:system|developer|assistant)\b',
    ]
    return any(re.search(pattern,collapsed,re.I) for pattern in patterns)


def parse_claim(sentence,scope,known_scopes):
    match=re.match(r'^\s*(?:the\s+)?(.{1,100}?)\s+(?:is|are|was|were)\s+(.+)$',sentence,re.I)
    if not match:return None
    subject,value=match.groups()
    subject_words=normalized_tokens(subject)
    entity=subject_words & known_scopes
    # A document heading can scope an otherwise unqualified factual sentence.
    if not entity:entity=set(scope)
    relation=subject_words-known_scopes-{'project','service','fictional','sample'}
    if not relation:return None
    return {'entity':tuple(sorted(entity)),'relation':tuple(sorted(relation)),
            'value':value.strip().rstrip('.!?'),'text':sentence}


def overlapping_fragment(claim, other, sources):
    """Discard an incomplete tail only when literal chunk overlap proves it.

    Prefix-equivalent names in different documents, pages, or complete sentences
    remain conflicting. No semantic value equivalence or authority is inferred.
    """
    if claim['text'].endswith(('.', '!', '?')) or not other['text'].endswith(('.', '!', '?')):
        return False
    left=sources[claim['source_index']]
    right=sources[other['source_index']]
    if left['id']==right['id'] or left['document_id']!=right['document_id'] or left['page']!=right['page']:
        return False
    if claim['entity']!=other['entity'] or claim['relation']!=other['relation']:
        return False
    prefix=' '.join(claim['value'].lower().split())
    complete=' '.join(other['value'].lower().split())
    if not complete.startswith(prefix+' '):return False
    if not left['text'].rstrip().endswith(claim['text']):return False
    a,b=left['text'].split(),right['text'].split()
    # Ten shared words require more than a coincidentally matching short fact.
    return any(a[-size:]==b[:size] for size in range(min(len(a),len(b)),9,-1))


def plan_evidence(question,sources,guard,scope_getter):
    scopes=[scope_getter(source) for source in sources]
    known=set().union(*scopes) if scopes else set()
    terms=normalized_tokens(question,question=True)
    requested=terms & known
    relation_terms=terms-known
    clauses=re.split(r'\band\b', question, flags=re.I)
    clause_terms=[normalized_tokens(clause, question=True)-known for clause in clauses]
    candidates=[]
    for index,(source,scope) in enumerate(zip(sources,scopes)):
        # A control-bearing chunk is quarantined, not passed as model context.
        if instruction_like(source['text']):continue
        for sentence in sentences(source['text']):
            claim=parse_claim(sentence,scope,known)
            if not claim:continue
            if requested and not requested & set(claim['entity']):continue
            matched=relation_terms & set(claim['relation'])
            if not matched-GENERIC_RELATION:continue
            applicable=[clause for clause,words in zip(clauses,clause_terms)
                        if words & set(claim['relation'])-GENERIC_RELATION]
            if not any(guard(clause,sentence) for clause in applicable):continue
            # Explicit temporal qualifiers remain conservative across all slots.
            if any(year not in sentence for year in re.findall(r'\b(?:19|20)\d{2}\b',question)):continue
            claim.update(source_index=index,matched=matched)
            candidates.append(claim)
    if not candidates:return None  # Conservative legacy fallback for non-copular prose/CSV.
    # A field-bearing conjunct must have evidence; entity-only conjuncts inherit
    # the shared relation (e.g. one property requested for two named entities).
    if any(words-GENERIC_RELATION and not any(words & set(claim['relation'])-GENERIC_RELATION for claim in candidates)
           for words in clause_terms):
        return []
    # Suppress topical-only matches when a strictly more specific relation fits.
    # Independent requested fields have non-subset matches and survive together.
    candidates=[claim for claim in candidates if not any(claim['matched'] < other['matched'] for other in candidates)]
    candidates=[claim for claim in candidates
                if not any(overlapping_fragment(claim,other,sources) for other in candidates)]
    conflicts=defaultdict(set)
    entities=defaultdict(set)
    for claim in candidates:
        key=(claim['entity'],claim['relation'])
        conflicts[key].add(' '.join(claim['value'].lower().split()))
        entities[claim['relation']].add((claim['entity'],' '.join(claim['value'].lower().split())))
    conflict=any(len(values)>1 for values in conflicts.values())
    ambiguous=not requested and any(len({value for _,value in values})>1 and len({entity for entity,_ in values})>1 for values in entities.values())
    # Keep distinct entity/relation/value units, deduplicating overlapping text.
    by_source=defaultdict(list)
    seen=set()
    for claim in candidates:
        key=(claim['entity'],claim['relation'],' '.join(claim['value'].lower().split()))
        if key in seen:continue
        seen.add(key)
        by_source[claim['source_index']].append(claim)
    selected=[]
    covered=set()
    remaining=set(by_source)
    while remaining and len(selected)<5:
        index=max(remaining,key=lambda i:(len({(c['entity'],c['relation']) for c in by_source[i]}-covered),-i))
        remaining.remove(index)
        units=by_source[index]
        covered|={(c['entity'],c['relation']) for c in units}
        selected.append({**sources[index], 'evidence_text':' '.join(c['text'] for c in units),
                         'evidence_units':[{key:claim[key] for key in ['entity','relation','value','text']} for claim in units],
                         'evidence_conflict':conflict,'evidence_ambiguous':ambiguous,
                         'requested_entities':sorted(requested)})
    return selected


def needs_clarification(sources):
    return any(source.get('evidence_conflict') or source.get('evidence_ambiguous') for source in sources)


def extract_units(sources,limit=3):
    options=[]
    for index,source in enumerate(sources,1):
        for unit in source.get('evidence_units',[]):
            options.append((unit,index))
    if not options:return None
    # Slots, not whole-query overlap: two entities need two independent facts.
    chosen=[]
    seen=set()
    for unit,index in options:
        key=(tuple(unit['entity']),tuple(unit['relation']))
        if key in seen:continue
        seen.add(key)
        chosen.append(f'{unit["text"]} [S{index}]')
        if len(chosen)==limit:break
    return '\n\n'.join(chosen)
