"""Create a reviewable source archive without user databases, models, or caches."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / 'artifacts/research-desk-source.zip'
output.parent.mkdir(exist_ok=True)
allowed_dirs = {'backend', 'frontend', 'scripts', 'evals', '.github'}
allowed_root = {'README.md', 'PORTFOLIO.md', 'INTERVIEW_GUIDE.md', 'SHOWCASE.md', 'LICENSE', 'Dockerfile', '.dockerignore', '.gitignore', 'requirements.txt', 'requirements-lock.txt'}
allowed_data = {'practice-project-notes.pdf', 'practice-workshop.png'}
excluded = {'node_modules', 'dist', '__pycache__', '.pytest_cache', 'test-results', 'playwright-report'}
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if any(part in excluded for part in relative.parts) or not path.is_file() or path.name.startswith('.env') or path.suffix in {'.pyc', '.tsbuildinfo', '.sqlite3', '.pem', '.key'}:
            continue
        include = relative.parts[0] in allowed_dirs or str(relative) in allowed_root
        if relative.parts[0] == 'data':
            include = len(relative.parts) > 1 and (relative.parts[1] == 'samples' or relative.parts[1] in allowed_data)
        if include:
            archive.write(path, Path('research-desk') / relative)
print(output)
