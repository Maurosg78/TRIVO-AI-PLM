#!/usr/bin/env python3
from dotenv import load_dotenv
from github import Github
import os
import yaml

# Cargo variables de entorno
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

gh_token = os.getenv('GITHUB_TOKEN')
if not gh_token:
    print('🚨 No se ha encontrado GITHUB_TOKEN en .env')
    exit(1)

# Conexión a GitHub
g = Github(gh_token)
# Obtener el repositorio: asumir remote origin
remote_url = os.popen('git config --get remote.origin.url').read().strip()
if remote_url.startswith('git@'):
    # git@github.com:owner/repo.git
    path = remote_url.split(':', 1)[1]
elif remote_url.startswith('https://'):
    # https://github.com/owner/repo.git
    path = remote_url.split('github.com/', 1)[1]
else:
    print('URL del remoto no reconocida:', remote_url)
    exit(1)
repo_name = path.removesuffix('.git')
repo = g.get_repo(repo_name)

# 1) Crear milestones para cada sprint
sprints = ['Sprint 1: Infraestructura Base', 'Sprint 2: Sistema de Recomendación', 'Sprint 3: Frontend y UX']
milestones = {}
for title in sprints:
    ms = repo.create_milestone(title=title, state='open')
    milestones[title] = ms
    print(f'✅ Milestone creado: {title}')

# 2) Leer issues de .github/ISSUES.md
def parse_issues(md_path='.github/ISSUES.md'):
    issues = []
    with open(md_path, 'r') as f:
        current = None
        for line in f:
            if line.startswith('### '):
                # new section
                section = line.strip().lstrip('### ').strip()
                current = section
            elif line.strip().startswith('- [ ]') and current:
                title = line.strip().lstrip('- [ ]').strip()
                issues.append((current, title))
    return issues

todo_items = parse_issues()
for section, title in todo_items:
    # Determinar sprint por sección del roadmap (asumimos orden)
    if 'Infraestructura' in section:
        ms = milestones[sprints[0]]
    elif 'Recomendación' in section:
        ms = milestones[sprints[1]]
    else:
        ms = milestones[sprints[2]]
    issue = repo.create_issue(
        title=title,
        body=f'Issue generado automáticamente en sección **{section}**',
        milestone=ms,
    )
    print(f'🟢 Issue creado: {title} ({section})')

# 3) Crear Project Board usando la configuración de kanban.yml
kanban_path = os.path.join(os.path.dirname(__file__), '..', '.github', 'projects', 'kanban.yml')
with open(kanban_path) as f:
    config = yaml.safe_load(f)

proj_name = config.get('name', 'TRIVO-AI-PLM Board')
proj_desc = config.get('description', '')
# Ver si ya existe el proyecto
projects = list(repo.get_projects())
proj = next((p for p in projects if p.name == proj_name), None)
if not proj:
    proj = repo.create_project(name=proj_name, body=proj_desc)
    print(f'📋 Project creado: {proj_name}')
else:
    print(f'📋 Project ya existente: {proj_name}')

# Crear columnas y tarjetas según kanban.yml
existing_columns = {col.name: col for col in proj.get_columns()}
for col_cfg in config.get('columns', []):
    col_name = col_cfg.get('name')
    # Crear o recuperar columna
    if col_name in existing_columns:
        col = existing_columns[col_name]
    else:
        col = proj.create_column(col_name)
        print(f'➕ Columna creada: {col_name}')
    # Crear issues y tarjetas en cada columna
    for card in col_cfg.get('cards', []):
        title = card.get('title')
        desc = card.get('description', '')
        labels = card.get('labels', [])
        assignees = card.get('assignees', [])
        # Crear issue en repo
        try:
            issue = repo.create_issue(title=title, body=desc, labels=labels, assignees=assignees)
            print(f'🟢 Issue creado: {title}')
        except Exception as e:
            print(f'⚠️ No se pudo crear issue {title}: {e}')
            continue
        # Agregar tarjeta referenciando el issue
        try:
            col.create_card(content_id=issue.id, content_type='Issue')
            print(f'🃏 Tarjeta agregada: {title} en {col_name}')
        except Exception as e:
            print(f'⚠️ No se pudo crear tarjeta para {title}: {e}')
print('🎉 Kanban cargado exitosamente!') 