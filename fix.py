#!/usr/bin/env python3
"""
LeninKart One-Shot Fix Script
============================
Fixes:
- Deletes empty kafka-pvc.yaml
- Fixes Kafka StatefulSet PVC storageClass
- Removes merge conflict markers from order-service
- Creates backups before changes

SAFE FOR GITOPS + ARGOCD
"""

import os
import shutil
import re
from datetime import datetime

ROOT = os.getcwd()
BACKUP_DIR = f"_auto_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES_TO_FIX = [
    "k8s/kafka/kafka.yaml",
    "helm/order-service/values-dev.yaml",
]

def log(msg):
    print(f"[FIX] {msg}")

def backup(path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    target = os.path.join(BACKUP_DIR, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(path, target)
    log(f"Backup created: {target}")

# ------------------------------------------------
# 1. DELETE EMPTY kafka-pvc.yaml
# ------------------------------------------------
def fix_kafka_pvc_file():
    pvc_file = "k8s/kafka/kafka-pvc.yaml"
    if os.path.exists(pvc_file):
        if os.path.getsize(pvc_file) == 0:
            backup(pvc_file)
            os.remove(pvc_file)
            log("Deleted empty kafka-pvc.yaml (correct for StatefulSet)")
        else:
            log("kafka-pvc.yaml exists but is not empty – review manually")
    else:
        log("kafka-pvc.yaml not present (OK)")

# ------------------------------------------------
# 2. FIX KAFKA STATEFULSET STORAGECLASS
# ------------------------------------------------
def fix_kafka_statefulset():
    path = "k8s/kafka/kafka.yaml"
    if not os.path.exists(path):
        log("Kafka StatefulSet not found, skipping")
        return

    with open(path, "r") as f:
        content = f.read()

    if "storageClassName:" in content:
        log("Kafka StatefulSet already has storageClassName")
        return

    backup(path)

    fixed = re.sub(
        r"(volumeClaimTemplates:\s*-\s*metadata:\s*name:\s*kafka-data\s*spec:\s*accessModes:\s*-\s*ReadWriteOnce)",
        r"\1\n        storageClassName: standard",
        content,
        flags=re.MULTILINE
    )

    with open(path, "w") as f:
        f.write(fixed)

    log("Added storageClassName: standard to Kafka StatefulSet")

# ------------------------------------------------
# 3. REMOVE MERGE CONFLICTS (ORDER-SERVICE)
# ------------------------------------------------
def fix_merge_conflicts():
    path = "helm/order-service/values-dev.yaml"
    if not os.path.exists(path):
        log("order-service values-dev.yaml not found")
        return

    with open(path, "r") as f:
        lines = f.readlines()

    if not any(line.startswith("<<<<<<<") for line in lines):
        log("No merge conflicts found in order-service")
        return

    backup(path)

    cleaned = []
    skip = False

    for line in lines:
        if line.startswith("<<<<<<<"):
            skip = True
            continue
        if line.startswith("======="):
            continue
        if line.startswith(">>>>>>>"):
            skip = False
            continue
        if not skip:
            cleaned.append(line)

    with open(path, "w") as f:
        f.writelines(cleaned)

    log("Removed merge conflict markers from order-service values")

# ------------------------------------------------
# MAIN
# ------------------------------------------------
def main():
    print("\n=== LENINKART AUTO FIX STARTED ===\n")
    fix_kafka_pvc_file()
    fix_kafka_statefulset()
    fix_merge_conflicts()
    print(f"\n✔ Fix complete. Backup folder: {BACKUP_DIR}\n")
    print("NEXT STEPS:")
    print("  git status")
    print("  git diff")
    print("  git add .")
    print("  git commit -m \"fix: kafka pvc, storageclass, merge conflicts\"")
    print("  git push origin dev")
    print("\nArgoCD will auto-sync 🚀\n")

if __name__ == "__main__":
    main()