#!/usr/bin/env python3
"""
Fix LeninKart Infrastructure Repository
Removes rewrite-target annotation that's breaking the ingress routing
Author: Lenin Raj
"""

import re
from pathlib import Path
from datetime import datetime
import shutil

class InfraFixer:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)
        self.backup_dir = self.repo_path / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.fixes = []
        
    def log(self, msg, level="INFO"):
        colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "ERROR": "\033[91m", "RESET": "\033[0m"}
        print(f"{colors.get(level, '')}{level}: {msg}{colors['RESET']}")
    
    def backup_file(self, file_path):
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        
        rel_path = file_path.relative_to(self.repo_path)
        backup_path = self.backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
    
    def fix_ingress(self):
        """Remove problematic regex annotation from ingress"""
        ingress_file = self.repo_path / "helm/ingress/templates/ingress.yaml"
        
        if not ingress_file.exists():
            self.log("Ingress file not found!", "ERROR")
            return False
        
        self.backup_file(ingress_file)
        content = ingress_file.read_text(encoding='utf-8')
        
        # Remove the use-regex annotation (keep it simple, no rewrite)
        new_content = re.sub(
            r'\s*annotations:.*\n\s*nginx\.ingress\.kubernetes\.io/use-regex:.*\n',
            '\n',
            content
        )
        
        # Ensure paths are simple Prefix type
        new_content = re.sub(
            r'pathType: ImplementationSpecific',
            'pathType: Prefix',
            new_content
        )
        
        ingress_file.write_text(new_content, encoding='utf-8')
        self.fixes.append("✓ Fixed ingress - removed regex annotation")
        self.log("Fixed ingress.yaml", "SUCCESS")
        return True
    
    def verify_service_names(self):
        """Ensure service names match in product-service"""
        svc_file = self.repo_path / "helm/product-service/templates/service.yaml"
        
        if not svc_file.exists():
            return True
        
        self.backup_file(svc_file)
        content = svc_file.read_text(encoding='utf-8')
        
        # Ensure port has a name
        if 'name: http' not in content:
            content = re.sub(
                r'(\s+ports:\s*\n\s+-)(\s+port:)',
                r'\1 name: http\n\2',
                content
            )
            svc_file.write_text(content, encoding='utf-8')
            self.fixes.append("✓ Added port name to product-service")
            self.log("Fixed product-service port name", "SUCCESS")
        
        return True
    
    def run(self):
        self.log("=" * 60, "INFO")
        self.log("LeninKart Infrastructure Fixer", "INFO")
        self.log("=" * 60, "INFO")
        
        # Verify we're in the right repo
        if not (self.repo_path / "helm").exists():
            self.log("ERROR: Not in leninkart-infra repo!", "ERROR")
            self.log("Run this from the infra repository root", "ERROR")
            return False
        
        self.log("Starting fixes...", "INFO")
        self.fix_ingress()
        self.verify_service_names()
        
        self.log("", "INFO")
        self.log("=" * 60, "SUCCESS")
        self.log(f"Applied {len(self.fixes)} fixes:", "SUCCESS")
        for fix in self.fixes:
            self.log(f"  {fix}", "SUCCESS")
        
        self.log("", "INFO")
        self.log(f"Backup: {self.backup_dir.name}", "INFO")
        self.log("", "INFO")
        self.log("NEXT STEPS:", "INFO")
        self.log("1. git add .", "INFO")
        self.log("2. git commit -m 'fix: remove ingress regex annotation'", "INFO")
        self.log("3. git push origin dev", "INFO")
        self.log("4. Wait for ArgoCD to sync", "INFO")
        self.log("=" * 60, "INFO")
        
        return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = "."
    
    fixer = InfraFixer(repo_path)
    success = fixer.run()
    sys.exit(0 if success else 1)