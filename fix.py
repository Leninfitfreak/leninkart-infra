from pathlib import Path
import shutil

INGRESS = Path("leninkart-ingress.yaml")

OLD = """      - path: /
        pathType: Prefix
        backend:
          service:
            name: leninkart-frontend
            port:
              number: 3000
"""

NEW = """      - path: /
        pathType: Prefix
        backend:
          service:
            name: leninkart-frontend
            port:
              number: 80
"""

def backup():
    bak = INGRESS.with_suffix(".yaml.bak2")
    if not bak.exists():
        shutil.copy(INGRESS, bak)
        print(f"📦 Backup created: {bak}")

def fix():
    content = INGRESS.read_text()

    if NEW in content:
        print("✅ Ingress frontend port already correct")
        return

    if OLD not in content:
        print("❌ Expected ingress block not found — check manually")
        return

    backup()
    INGRESS.write_text(content.replace(OLD, NEW))
    print("✅ Ingress frontend port FIXED (3000 → 80)")

if __name__ == "__main__":
    fix()