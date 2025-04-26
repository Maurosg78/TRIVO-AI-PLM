#!/usr/bin/env bash
# Define aquí tu usuario GH sin "@"
ASSIGNEE=Maurosg78

# Issue | Título | Body | Labels (coma separada)
declare -A ISSUES=(
  [2]="Setup del entorno de desarrollo|Crear y documentar el entorno local con Python 3.11, virtualenv, dependencias y estructura de directorios.|infra,backend"
  [3]="Configuración de pre-commit, linters y formatters|Integrar pre-commit hooks, black, isort, flake8 y ruff en CI.|tooling,infra"
  [4]="CI/CD con GitHub Actions|Pipeline: tests, lint, build y push de Docker Images a Docker Hub.|ci/cd,infra"
  # … continúa para cada issue de Sprint 1 …
)

for NUM in "${!ISSUES[@]}"; do
  IFS="|" read -r TITLE BODY LABELS <<< "${ISSUES[$NUM]}"
  # convierte "a,b" en múltiples flags --add-label
  CMD="gh issue edit $NUM --title \"$TITLE\" --body \"$BODY\""
  for L in ${LABELS//,/ }; do
    CMD="$CMD --add-label $L"
  done
  CMD="$CMD --add-assignee $ASSIGNEE"
  echo "$CMD"
  eval $CMD
done
