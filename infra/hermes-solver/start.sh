#!/bin/sh
set -eu
test -n "${DEEPSEEK_API_KEY:-}"
test -n "${API_SERVER_KEY:-}"
test -n "${HERMES_HOME:-}"
test -n "${HERMES_SOLVER_MODEL_ID:-}"
mkdir -p "$HERMES_HOME"
python - <<'PY'
import os
import yaml
with open('/etc/hermes-solver/config.yaml', encoding='utf-8') as source:
    config = yaml.safe_load(source)
config['model']['default'] = os.environ['HERMES_SOLVER_MODEL_ID']
with open(os.path.join(os.environ['HERMES_HOME'], 'config.yaml'), 'w', encoding='utf-8') as target:
    yaml.safe_dump(config, target)
PY
exec hermes gateway run
