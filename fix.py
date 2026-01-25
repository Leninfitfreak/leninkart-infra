#!/usr/bin/env python3
"""
LeninKart Infrastructure Auto-Fix Script
Fixes all Kubernetes deployment issues automatically
Author: Lenin Raj (with Claude assistance)
"""

import os
import re
import sys
from pathlib import Path
import shutil
from datetime import datetime

class LeninKartFixer:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)
        self.backup_dir = self.repo_path / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.fixes_applied = []
        self.errors = []
        
    def log(self, message, level="INFO"):
        """Print colored log messages"""
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "RESET": "\033[0m"
        }
        print(f"{colors.get(level, '')}{level}: {message}{colors['RESET']}")
    
    def backup_file(self, file_path):
        """Create backup of file before modification"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        
        rel_path = file_path.relative_to(self.repo_path)
        backup_path = self.backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        self.log(f"Backed up: {rel_path}", "INFO")
    
    def fix_ingress_rewrite(self):
        """Fix #1: Remove problematic rewrite-target annotation from ingress"""
        ingress_file = self.repo_path / "helm/ingress/templates/ingress.yaml"
        
        if not ingress_file.exists():
            self.errors.append("Ingress file not found")
            return False
        
        try:
            self.backup_file(ingress_file)
            content = ingress_file.read_text()
            
            # Remove rewrite-target and use-regex annotations
            new_content = re.sub(
                r'  annotations:\s*\n\s*nginx\.ingress\.kubernetes\.io/use-regex:.*\n\s*nginx\.ingress\.kubernetes\.io/rewrite-target:.*\n',
                '',
                content
            )
            
            # Also fix path patterns - remove regex patterns
            new_content = re.sub(
                r'path: /api/products\(/\|\$\)\(\.\*\)',
                'path: /api/products',
                new_content
            )
            new_content = re.sub(
                r'path: /api/orders\(/\|\$\)\(\.\*\)',
                'path: /api/orders',
                new_content
            )
            
            # Change pathType to Prefix for API paths
            new_content = re.sub(
                r'pathType: ImplementationSpecific',
                'pathType: Prefix',
                new_content
            )
            
            ingress_file.write_text(new_content)
            self.fixes_applied.append("✓ Fixed ingress rewrite-target issue")
            self.log("Fixed ingress rewrite-target annotation", "SUCCESS")
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to fix ingress: {str(e)}")
            self.log(f"Error fixing ingress: {str(e)}", "ERROR")
            return False
    
    def fix_order_service_port(self):
        """Fix #2: Ensure order-service uses consistent port 8080"""
        values_file = self.repo_path / "helm/order-service/values-dev.yaml"
        
        if not values_file.exists():
            self.errors.append("Order service values file not found")
            return False
        
        try:
            self.backup_file(values_file)
            content = values_file.read_text()
            
            # Ensure port is 8080 (already correct in your config)
            if 'port: 8080' in content:
                self.log("Order service port already correct (8080)", "INFO")
                return True
            
            # If port is different, fix it
            content = re.sub(r'port: \d+', 'port: 8080', content)
            values_file.write_text(content)
            
            self.fixes_applied.append("✓ Fixed order-service port to 8080")
            self.log("Fixed order-service port", "SUCCESS")
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to fix order service port: {str(e)}")
            self.log(f"Error fixing order service port: {str(e)}", "ERROR")
            return False
    
    def fix_frontend_service_port(self):
        """Fix #3: Ensure frontend service targets correct container port"""
        service_file = self.repo_path / "helm/frontend/templates/service.yaml"
        
        if not service_file.exists():
            self.errors.append("Frontend service file not found")
            return False
        
        try:
            self.backup_file(service_file)
            content = service_file.read_text()
            
            # Ensure targetPort is 'http' (named port)
            if 'targetPort: http' in content:
                self.log("Frontend service targetPort already correct", "INFO")
                return True
            
            content = re.sub(
                r'targetPort: \{\{ \.Values\.service\.port \}\}',
                'targetPort: http',
                content
            )
            
            service_file.write_text(content)
            self.fixes_applied.append("✓ Fixed frontend service targetPort")
            self.log("Fixed frontend service targetPort", "SUCCESS")
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to fix frontend service: {str(e)}")
            self.log(f"Error fixing frontend service: {str(e)}", "ERROR")
            return False
    
    def add_service_port_names(self):
        """Fix #4: Add named ports to all services"""
        services = {
            "order-service": self.repo_path / "helm/order-service/templates/service.yaml",
            "product-service": self.repo_path / "helm/product-service/templates/service.yaml"
        }
        
        for svc_name, svc_file in services.items():
            if not svc_file.exists():
                self.log(f"{svc_name} service file not found", "WARNING")
                continue
            
            try:
                self.backup_file(svc_file)
                content = svc_file.read_text()
                
                # Check if port already has name
                if 'name: http' in content:
                    self.log(f"{svc_name} port name already exists", "INFO")
                    continue
                
                # Add name to port
                content = re.sub(
                    r'(\s+)- port:',
                    r'\1- name: http\n\1  port:',
                    content,
                    count=1
                )
                
                svc_file.write_text(content)
                self.fixes_applied.append(f"✓ Added port name to {svc_name}")
                self.log(f"Added port name to {svc_name}", "SUCCESS")
                
            except Exception as e:
                self.errors.append(f"Failed to add port name to {svc_name}: {str(e)}")
                self.log(f"Error fixing {svc_name}: {str(e)}", "ERROR")
    
    def fix_actuator_endpoints(self):
        """Fix #5: Ensure actuator endpoints are enabled in order-service"""
        values_file = self.repo_path / "helm/order-service/values-dev.yaml"
        
        if not values_file.exists():
            return False
        
        try:
            content = values_file.read_text()
            
            # Check if actuator settings already exist
            if 'MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE' in content:
                self.log("Actuator endpoints already configured", "INFO")
                return True
            
            self.backup_file(values_file)
            
            # Add actuator configuration to env section
            actuator_config = """
  # ---------- ACTUATOR (HEALTH ENDPOINTS) ----------
  MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE: health,info
  MANAGEMENT_ENDPOINT_HEALTH_PROBES_ENABLED: "true"
"""
            
            # Insert before the last line (if env section exists)
            if 'env:' in content:
                content = content.rstrip() + actuator_config
                values_file.write_text(content)
                self.fixes_applied.append("✓ Added actuator endpoint configuration")
                self.log("Added actuator endpoint configuration", "SUCCESS")
                return True
                
        except Exception as e:
            self.errors.append(f"Failed to add actuator config: {str(e)}")
            self.log(f"Error adding actuator config: {str(e)}", "ERROR")
            return False
    
    def verify_kafka_config(self):
        """Fix #6: Verify Kafka configuration is correct"""
        order_values = self.repo_path / "helm/order-service/values-dev.yaml"
        
        if not order_values.exists():
            return False
        
        try:
            content = order_values.read_text()
            
            # Check for correct Kafka bootstrap server
            correct_server = "kafka-0.kafka.dev.svc.cluster.local:9092"
            
            if correct_server not in content:
                self.backup_file(order_values)
                content = re.sub(
                    r'SPRING_KAFKA_BOOTSTRAP_SERVERS: .*',
                    f'SPRING_KAFKA_BOOTSTRAP_SERVERS: {correct_server}',
                    content
                )
                order_values.write_text(content)
                self.fixes_applied.append("✓ Fixed Kafka bootstrap server address")
                self.log("Fixed Kafka bootstrap server", "SUCCESS")
            else:
                self.log("Kafka configuration already correct", "INFO")
            
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to verify Kafka config: {str(e)}")
            self.log(f"Error verifying Kafka config: {str(e)}", "ERROR")
            return False
    
    def create_readme(self):
        """Create a README with manual steps"""
        readme_content = """# LeninKart Infrastructure - Auto-Fix Applied

## Fixes Applied by Script
{}

## Manual Steps Required

### 1. Commit and Push Changes
```bash
git add .
git commit -m "fix: resolve Kubernetes routing and service issues"
git push origin dev
```

### 2. Sync ArgoCD
Either wait for auto-sync or manually sync:
```bash
# Option A: ArgoCD CLI
argocd app sync leninkart-root

# Option B: ArgoCD UI
# Go to ArgoCD dashboard and click "Sync" on leninkart-root app
```

### 3. Access the Application
```bash
# Start minikube tunnel (required for LoadBalancer)
minikube tunnel

# In another terminal, get the service URL
minikube service leninkart-frontend -n dev --url

# Or use port-forward
kubectl port-forward -n dev svc/leninkart-frontend 8080:80
# Then access: http://localhost:8080
```

### 4. Verify Services
```bash
# Check all pods are running
kubectl get pods -n dev

# Check services
kubectl get svc -n dev

# Check ingress
kubectl get ingress -n dev

# Test backend directly
kubectl port-forward -n dev svc/leninkart-product-service 8081:8081
curl http://localhost:8081/api/products
```

### 5. Troubleshooting
If issues persist:

```bash
# Check product service logs
kubectl logs -n dev -l app=product-service --tail=100

# Check order service logs
kubectl logs -n dev -l app.kubernetes.io/name=order-service --tail=100

# Check frontend logs
kubectl logs -n dev -l app=frontend --tail=100

# Describe ingress for routing rules
kubectl describe ingress leninkart-ingress -n dev
```

## Errors Encountered
{}

## Backup Location
All original files backed up to: {}

## Need Help?
Check the interactive debugger for detailed guidance.
"""
        
        readme_file = self.repo_path / "FIX_APPLIED.md"
        
        fixes_text = "\n".join(f"- {fix}" for fix in self.fixes_applied) if self.fixes_applied else "- No fixes applied"
        errors_text = "\n".join(f"- {err}" for err in self.errors) if self.errors else "- No errors"
        
        readme_file.write_text(
            readme_content.format(fixes_text, errors_text, self.backup_dir.name),
            encoding='utf-8'
        )
        
        self.log(f"Created FIX_APPLIED.md with manual steps", "SUCCESS")
    
    def run_all_fixes(self):
        """Execute all fixes"""
        self.log("=" * 60, "INFO")
        self.log("LeninKart Infrastructure Auto-Fix Script", "INFO")
        self.log("=" * 60, "INFO")
        self.log(f"Working directory: {self.repo_path.absolute()}", "INFO")
        self.log("", "INFO")
        
        # Run all fixes
        self.log("Starting fixes...", "INFO")
        self.log("", "INFO")
        
        self.fix_ingress_rewrite()
        self.fix_order_service_port()
        self.fix_frontend_service_port()
        self.add_service_port_names()
        self.fix_actuator_endpoints()
        self.verify_kafka_config()
        
        # Generate summary
        self.log("", "INFO")
        self.log("=" * 60, "INFO")
        self.log("SUMMARY", "INFO")
        self.log("=" * 60, "INFO")
        
        if self.fixes_applied:
            self.log(f"✓ Applied {len(self.fixes_applied)} fixes:", "SUCCESS")
            for fix in self.fixes_applied:
                self.log(f"  {fix}", "SUCCESS")
        else:
            self.log("No fixes were needed or applied", "WARNING")
        
        if self.errors:
            self.log(f"✗ {len(self.errors)} errors occurred:", "ERROR")
            for error in self.errors:
                self.log(f"  - {error}", "ERROR")
        
        self.log("", "INFO")
        self.log(f"Backup created at: {self.backup_dir}", "INFO")
        
        # Create README
        self.create_readme()
        
        self.log("", "INFO")
        self.log("=" * 60, "INFO")
        self.log("NEXT STEPS", "INFO")
        self.log("=" * 60, "INFO")
        self.log("1. Review changes: git diff", "INFO")
        self.log("2. Commit and push: git add . && git commit -m 'fix: K8s issues' && git push", "INFO")
        self.log("3. Sync ArgoCD or wait for auto-sync", "INFO")
        self.log("4. Run: minikube tunnel", "INFO")
        self.log("5. Access: minikube service leninkart-frontend -n dev", "INFO")
        self.log("", "INFO")
        self.log("Read FIX_APPLIED.md for detailed instructions!", "SUCCESS")
        self.log("=" * 60, "INFO")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Auto-fix LeninKart Kubernetes infrastructure issues"
    )
    parser.add_argument(
        "-p", "--path",
        default=".",
        help="Path to leninkart-infra repository (default: current directory)"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes"
    )
    
    args = parser.parse_args()
    
    # Verify we're in the right directory
    repo_path = Path(args.path)
    if not (repo_path / "helm").exists():
        print("ERROR: This doesn't look like the leninkart-infra repository.")
        print("Please run this script from the repository root or use -p flag.")
        sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print()
    
    # Run fixer
    fixer = LeninKartFixer(repo_path)
    
    if not args.dry_run:
        fixer.run_all_fixes()
    else:
        print("Would apply the following fixes:")
        print("1. Remove ingress rewrite-target annotation")
        print("2. Fix order-service port consistency")
        print("3. Fix frontend service targetPort")
        print("4. Add named ports to services")
        print("5. Add actuator endpoint configuration")
        print("6. Verify Kafka configuration")
        print()
        print("Run without --dry-run to apply fixes")


if __name__ == "__main__":
    main()