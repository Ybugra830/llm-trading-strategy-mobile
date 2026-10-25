#!/usr/bin/env bash
# Read-only metadata discovery. Do not print units, environment, logs or nginx config.
set -u
printf 'SERVICES\n'
for unit in llm-strategy.service llm-strategy-candidate.service; do
  printf '%s\n' "$unit"
  systemctl show "$unit" --no-pager \
    --property=LoadState,ActiveState,SubState,MainPID,User,WorkingDirectory,FragmentPath,EnvironmentFiles,ExecMainStartTimestamp
  pid=$(systemctl show "$unit" --property=MainPID --value 2>/dev/null)
  if [[ "$pid" =~ ^[1-9][0-9]*$ ]]; then
    printf 'process cwd=%s exe=%s\n' "$(readlink -f "/proc/$pid/cwd")" "$(readlink -f "/proc/$pid/exe")"
  fi
done
printf 'PORTS\n'
ss -ltnp '( sport = :8000 or sport = :8001 )' 2>/dev/null || true
printf 'KNOWN PATHS AND RELEASES\n'
for dir in /opt/llm-trading-strategy-mobile /opt/strategy-lab-releases /var/www/strategy-lab; do
  if [ -e "$dir" ]; then
    printf '%s -> %s\n' "$dir" "$(readlink -f "$dir")"
  else
    printf '%s: absent\n' "$dir"
  fi
done
for dir in /opt/llm-trading-strategy-mobile /opt/strategy-lab-releases/*; do
  [ -d "$dir" ] || continue
  printf 'release %s\n' "$dir"
  if [ -e "$dir/.git" ]; then
    git -c safe.directory="$dir" -C "$dir" rev-parse HEAD 2>/dev/null || true
  fi
  if [ -f "$dir/backend/sandbox/worker.py" ]; then
    sha256sum "$dir/backend/sandbox/worker.py"
  fi
done
printf 'SANDBOX IMAGES\n'
if command -v docker >/dev/null; then
  docker image ls --no-trunc --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.CreatedSince}}' 2>/dev/null \
    | awk '/llm.*strategy|strategy.*sandbox/' | head -n 8
else
  printf 'docker unavailable\n'
fi
printf 'BACKUP PATHS ONLY (bounded search; not proof of completeness)\n'
for dir in /opt /home/azureuser /var/backups; do
  [ -d "$dir" ] || continue
  find "$dir" -maxdepth 3 \( -iname '*backup*' -o -iname '*rollback*' \) \
    -printf '%y %p\n' 2>/dev/null | head -n 8
done
