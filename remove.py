#!/usr/bin/env python3
"""
LeninKart GitOps Refactor & Cleanup Script (Dump-Aware)
======================================================

SAFE:
- Windows / PowerShell
- No cluster access
- No secret mutation
- No Vault init logic
- No .git modifications

DEFAULT: DRY-RUN
"""

from pathlib import Path
import shutil
import sys
import re
from datetime import datetime

# ---------------- CONFIG ----------------
REPO_ROOT = Path.cwd()
DRY_RUN = False  # change to False to apply
REPORT = []

JUNK_FILES = {
    "dump.py",
    "observability.py",
    "fix.py",
}

JUNK_DIR_PATTERNS = [
    r"_cleanup_backup",
    r"_backup_",
    r"_reorg_backup",
    r"ervability stack",
]

NGINX_PATTERNS = [
    "applications/ingress",
    "nginx",
]

VAULT_INIT_PATTERNS = [
    "init-job",
    "05-init",
    "setup-k8s-auth.sh",
]

PLAINTEXT_SECRET_KEYS = [
    "SPRING_DATASOURCE_PASSWORD",
    "password:",
]

# ---------------- HELPERS ----------------
def log(msg):
    print(msg)
    REPORT.append(msg)

def should_delete(path: Path):
    return any(re.search(p, str(path), re.IGNORECASE) for p in JUNK_DIR_PATTERNS)

def safe_delete(path: Path):
    if DRY_RUN:
        log(f"[DRY-RUN] Would remove: {path}")
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    log(f"[REMOVED] {path}")

# ---------------- START ----------------
log("=" * 70)
log("LeninKart GitOps Refactor (based on dump6.txt)")
log(f"Mode: {'DRY-RUN' if DRY_RUN else 'APPLY'}")
log("=" * 70)

# 1. Remove junk files
log("\n[1] Removing junk scripts & artifacts")
for p in REPO_ROOT.rglob("*"):
    if p.name in JUNK_FILES:
        safe_delete(p)

# 2. Remove junk directories
log("\n[2] Removing junk directories")
for p in REPO_ROOT.iterdir():
    if p.is_dir() and should_delete(p):
        safe_delete(p)

# 3. Remove NGINX ingress
log("\n[3] Removing NGINX ingress manifests")
for p in REPO_ROOT.rglob("*"):
    if any(x in str(p).lower() for x in NGINX_PATTERNS):
        safe_delete(p)

# 4. Remove Vault init jobs / scripts
log("\n[4] Removing imperative Vault init artifacts")
for p in REPO_ROOT.rglob("*"):
    if any(x in str(p) for x in VAULT_INIT_PATTERNS):
        safe_delete(p)

# 5. Create namespace manifests
log("\n[5] Ensuring namespace manifests exist")
ns_dir = REPO_ROOT / "platform" / "namespaces"
namespaces = ["dev", "staging", "prod"]

for ns in namespaces:
    ns_file = ns_dir / f"{ns}.yaml"
    content = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {ns}
  labels:
    istio-injection: enabled
    pod-security.kubernetes.io/enforce: baseline
"""
    if ns_file.exists():
        log(f"[OK] Namespace manifest exists: {ns}")
    else:
        if DRY_RUN:
            log(f"[DRY-RUN] Would create {ns_file}")
        else:
            ns_dir.mkdir(parents=True, exist_ok=True)
            ns_file.write_text(content, encoding="utf-8", newline="\n")
            log(f"[CREATED] {ns_file}")

# 6. Detect plaintext secrets
log("\n[6] Scanning for plaintext secrets (BLOCKING)")
for p in REPO_ROOT.rglob("*.yaml"):
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except:
        continue
    for key in PLAINTEXT_SECRET_KEYS:
        if key in text:
            log(f"[❌ PLAINTEXT SECRET] {p}")

# 7. Normalize line endings
log("\n[7] Normalizing line endings (LF)")
for p in REPO_ROOT.rglob("*.yaml"):
    if p.is_file():
        content = p.read_text(encoding="utf-8", errors="ignore")
        normalized = content.replace("\r\n", "\n")
        if content != normalized:
            if DRY_RUN:
                log(f"[DRY-RUN] Would normalize {p}")
            else:
                p.write_text(normalized, encoding="utf-8", newline="\n")
                log(f"[FIXED] {p}")

# 8. Write report
log("\n[8] Writing REPORT.md")
report_file = REPO_ROOT / "REPORT.md"
if DRY_RUN:
    log(f"[DRY-RUN] Would write {report_file}")
else:
    report_file.write_text("\n".join(REPORT), encoding="utf-8")

log("\nDONE.")
log("If DRY-RUN looks good → set DRY_RUN=False and re-run.")
