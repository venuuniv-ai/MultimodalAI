"""Summarize preserved baseline versus the latest synthetic development runs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    reports = [json.loads((ROOT / 'evals' / name).read_text()) for name in ('baseline-extractive.json', 'expanded-extractive.json', 'baseline-ollama.json', 'expanded-ollama.json')]
    lines = ['# Evaluation comparison', '', 'Recorded October 7, 2026. Baselines are preserved from before the field/year checks, clarification routing, explicit query aliases, document-title scoping, and instruction-like sentence filtering. All runs use the same 62 authored synthetic development cases in temporary databases.', '', '| Measure | Excerpts before | Excerpts after | Local AI before | Local AI after |', '|---|---:|---:|---:|---:|']
    for label, key in [('Evidence hit rate at 10', 'retrieval_evidence_hit_rate_at_10'), ('Expected answer string present (49 factual cases)', 'expected_span_answer_rate'), ('Exact standard refusal (8 missing facts)', 'unanswerable_abstention_rate'), ('Valid source IDs on answered factual cases', 'citation_valid_rate_on_answered_factual_questions'), ('CSV expected values (2 cases)', 'tool_value_pass_rate')]:
        lines.append('| ' + label + ' | ' + ' | '.join(f'{100 * report[key]:.1f}%' for report in reports) + ' |')
    for label, key in [('Sequential median full-response latency', 'latency_p50_ms'), ('Sequential P95 full-response latency', 'latency_p95_ms')]:
        lines.append('| ' + label + ' | ' + ' | '.join(f'{report[key]:.2f} ms' for report in reports) + ' |')
    lines += ['', 'Expected-string presence is a proxy, not semantic faithfulness. Exact refusal undercounts valid alternative refusals in the baseline. The known test set guided these changes, so improvements are development-set results, not independent validation. Latency is full sequential response time, not TTFT or concurrent capacity.', '', '## Targeted checks in the latest local AI run', '']
    latest = reports[-1]
    by_id = {row['id']: row for row in latest['results']}
    for ids, description in [(['q049', 'q050', 'q051', 'q052', 'q053', 'q054', 'q055', 'q056'], 'Requested facts absent from evidence'), (['q057', 'q058', 'q059'], 'Unscoped project questions'), (['q044', 'q046', 'q048'], 'Explicit role, launch, and escalation aliases')]:
        lines += [f'**{description}:**', '']
        for case_id in ids:
            row = by_id[case_id]
            lines.append(f'- {case_id}: {row["question"]} → {row["answer"].replace(chr(10), " ")}')
        lines.append('')
    lines += ['## Remaining limitations', '', '- Alias expansion covers a few explicit phrasings; it is not a semantic retrieval model. Document-title scoping addresses the known cross-project manager example but is a heuristic: missing or misleading headings, unrelated capitalized words, and complex references still need independent review.', '- Requested-attribute checks cover known fields and explicit years, not arbitrary relations or full entity resolution.', '- Instruction filtering recognizes a narrow set of imperative patterns. Obfuscated attacks, deceptive factual assertions, cross-document contamination, and arbitrary prompt injection still need independent adversarial review.', '- Clarification is conservative for three generic project-question forms. Other ambiguous questions and conflicting facts within one chunk can remain unresolved.', '- The literal expected-string metric can reject correct paraphrases. Full answer/evidence records and blank review worksheets remain available for independent review.', '', 'Latest local AI misses by the automatic answer-string measure:', '']
    for row in latest['results']:
        if row['answerable'] and row['category'] != 'tool' and not row['expected_span_present']:
            lines.append(f'- {row["id"]}: {row["question"]} → {row["answer"].replace(chr(10), " ")}')
    lines += ['', 'Thirty-two backend/evaluation tests and two isolated browser tests passed. The production frontend build passed. Browser checks verified the clarification label, unsupported-year refusal, and filtering of the known malicious budget command. These checks do not establish general safety or production readiness.', '', '## Portfolio wording', '', '“Built and evaluated a local document research prototype across 62 synthetic development cases, added targeted evidence checks and clarification routing, preserved baseline comparisons, and documented remaining limitations in paraphrase retrieval and untrusted evidence.”']
    (ROOT / 'evals/RESULTS.md').write_text('\n'.join(lines) + '\n')
    print('Updated evals/RESULTS.md')


if __name__ == '__main__':
    main()
