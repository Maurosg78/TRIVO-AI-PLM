#!/usr/bin/env bash
set -euo pipefail

# Script para crear y poblar el Kanban Next-Gen (Project V2) en GitHub
# Requisitos: gh CLI, yq (https://github.com/mikefarah/yq), jq, y GITHUB_TOKEN en .env

# 1) Cargar token desde .env
export $(grep -v '^#' .env | xargs)

# 2) Obtener owner y repo
FULL_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
OWNER=${FULL_REPO%/*}
REPO=${FULL_REPO#*/}

# 3) Variables de proyecto
title="TRIVO-AI-PLM Development Board"
kanban_file=".github/projects/kanban.yml"

# 4) Crear el project v2
echo "Creando Project Board: $title"
project_id=$(gh project create --owner "$OWNER" --title "$title" --format json --jq .number)
echo "→ Project creado (#$project_id)"

# 5) Linkearlo al repo
echo "Linkeando al repositorio $FULL_REPO"
gh project link "$project_id" --repo "$FULL_REPO"

# 6) Intentar crear el campo Status (SINGLE_SELECT) y, si falla, ignorar el error
echo "Creando campo Status (SINGLE_SELECT) con opciones..."
# Extraer nombres de columnas del kanban.yml y unir con comas
options=$(yq eval '.columns[].name' "$kanban_file" | paste -sd, -)
if gh project field-create "$project_id" --owner "$OWNER" --name "Status" --data-type SINGLE_SELECT --single-select-options "$options" --format json > /dev/null 2>&1; then
  echo "→ Campo 'Status' creado con opciones: $options"
else
  echo "→ Campo 'Status' ya existe, continuando..."
fi

# 7) Leer y crear tarjetas
echo "Procesando tarjetas desde $kanban_file..."
# Itera columnas y sus cards, extrayendo campo column y datos de cada tarjeta
yq eval -o=json '.columns[] | . as $c | $c.cards[] | {column: $c.name, title: .title, description: .description, labels: (.labels // []), assignees: (.assignees // [])}' "$kanban_file" \
  | jq -c . \
  | while IFS= read -r card; do
  title=$(echo "$card" | jq -r .title)
  body=$(echo "$card" | jq -r .description)
  labels=$(echo "$card" | jq -r '.labels | join(",")')
  assignees=$(echo "$card" | jq -r '.assignees | join(",")')
  column=$(echo "$card" | jq -r .column)

  echo "Creando issue: $title"
  # Construir flags de labels y assignees
  label_flags=""
  if [[ -n "$labels" ]]; then
    IFS=',' read -r -a labs <<< "$labels"
    for l in "${labs[@]}"; do
      label_flags+=" --label $l"
    done
  fi
  assignee_flags=""
  if [[ -n "$assignees" ]]; then
    IFS=',' read -r -a asgs <<< "$assignees"
    for a in "${asgs[@]}"; do
      assignee_flags+=" --assignee $a"
    done
  fi
  issue_num=$(eval gh issue create --title "\"$title\"" --body "\"$body\"" $label_flags $assignee_flags --format json --jq .number)
  echo "→ Issue #$issue_num creado"

  echo "Agregando issue al Project Board"
  item_id=$(gh project item-add --project "$project_id" --issue "$REPO#$issue_num" --format json --jq .id)
  echo "→ Item creado ID: $item_id"

  echo "Moviendo a columna '$column'"
  gh project item-edit --project "$project_id" --item "$item_id" --field "Status" --value "$column"
  echo "→ Movido a $column"
done

echo "🎉 Kanban Next-Gen generado con éxito!" 