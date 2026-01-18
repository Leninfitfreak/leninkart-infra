from pathlib import Path
import shutil

FILE = Path("helm/order-service/templates/service.yaml")

OLD = """  selector:
    app.kubernetes.io/name: order-service
    app.kubernetes.io/instance: {{ .Release.Name }}
"""

NEW = """  selector:
    app.kubernetes.io/name: order-service
    app.kubernetes.io/instance: dev-order-service
"""

def backup():
    bak = FILE.with_suffix(".yaml.bak")
    if not bak.exists():
        shutil.copy(FILE, bak)
        print(f"📦 Backup created: {bak}")

def fix():
    content = FILE.read_text()

    if NEW in content:
        print("✅ order-service selector already fixed")
        return

    if OLD not in content:
        print("❌ Expected selector not found — check manually")
        return

    backup()
    FILE.write_text(content.replace(OLD, NEW))
    print("✅ order-service Service selector FIXED")

if __name__ == "__main__":
    fix()