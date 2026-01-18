import os
import shutil

FILE_PATH = "helm/order-service/templates/service.yaml"

WRONG_SELECTOR = """  selector:
    app.kubernetes.io/name: leninkart-order-service
    app.kubernetes.io/instance: {{ .Release.Name }}
"""

CORRECT_SELECTOR = """  selector:
    app.kubernetes.io/name: order-service
    app.kubernetes.io/instance: {{ .Release.Name }}
"""

def backup_file(path):
    backup_path = path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copy(path, backup_path)
        print(f"📦 Backup created: {backup_path}")

def fix_selector():
    if not os.path.exists(FILE_PATH):
        print(f"❌ File not found: {FILE_PATH}")
        return

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if CORRECT_SELECTOR in content:
        print("✅ Selector already correct — nothing to change")
        return

    if WRONG_SELECTOR not in content:
        print("⚠️ Expected selector pattern not found — manual check needed")
        return

    backup_file(FILE_PATH)

    content = content.replace(WRONG_SELECTOR, CORRECT_SELECTOR)

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ order-service selector fixed successfully")

if __name__ == "__main__":
    print("🔧 Fixing order-service Service selector\n")
    fix_selector()