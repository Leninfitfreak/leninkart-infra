#!/usr/bin/env python3
"""
LeninKart Infrastructure Auto-Fix Script
=========================================
Fixes the following issues:
1. Frontend service selector mismatch
2. Missing frontend _helpers.tpl
3. Missing service.type in order-service values
4. Missing container.port in frontend values.yaml

Author: Claude AI Assistant
Usage: python leninkart_infra_fix.py [path_to_infra_repo]
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

BACKUP_PREFIX = "_backup_"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ============================================================
# FILE CONTENTS - FIXED VERSIONS
# ============================================================

FRONTEND_SERVICE_YAML = '''apiVersion: v1
kind: Service
metadata:
  name: leninkart-frontend
  labels:
    app: frontend
spec:
  type: {{ .Values.service.type | default "ClusterIP" }}
  selector:
    app: frontend
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
'''

FRONTEND_HELPERS_TPL = '''{{/* Chart name */}}
{{- define "frontend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Full name - always prefixed with leninkart- */}}
{{- define "frontend.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "leninkart-%s" (include "frontend.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/* Standard labels */}}
{{- define "frontend.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "frontend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app: frontend
{{- end }}

{{/* Selector labels - MUST match deployment pod labels */}}
{{- define "frontend.selectorLabels" -}}
app: frontend
{{- end }}
'''

FRONTEND_VALUES_YAML = '''replicaCount: 1

image:
  repository: asia-south1-docker.pkg.dev/leninkart-478305/leninkart/frontend
  pullPolicy: IfNotPresent
  tag: latest

service:
  type: ClusterIP
  port: 80

container:
  port: 80

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 300m
    memory: 256Mi

readinessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 20
  periodSeconds: 15
  failureThreshold: 5
'''

FRONTEND_VALUES_DEV_YAML = '''replicaCount: 1

image:
  repository: leninfitfreak/frontend
  tag: '21337825304'
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

container:
  port: 80

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

readinessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 5

livenessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 20
  periodSeconds: 15
  failureThreshold: 5
'''

ORDER_SERVICE_VALUES_DEV_YAML = '''replicaCount: 1

image:
  repository: leninfitfreak/order-service
  tag: "21348365866"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080

startupProbe:
  tcpSocket:
    port: http
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 60

readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 6

livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 60
  periodSeconds: 20
  failureThreshold: 10

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 300m
    memory: 256Mi

env:
  # ---------- DATABASE ----------
  SPRING_DATASOURCE_URL: jdbc:postgresql://postgres.dev.svc.cluster.local:5432/leninkart
  SPRING_DATASOURCE_USERNAME: postgres
  SPRING_DATASOURCE_PASSWORD: postgres
  SPRING_JPA_DATABASE_PLATFORM: org.hibernate.dialect.PostgreSQLDialect
  SPRING_JPA_HIBERNATE_DDL_AUTO: update
  SPRING_DATASOURCE_HIKARI_INITIALIZATION_FAIL_TIMEOUT: "60000"

  # ---------- KAFKA ----------
  SPRING_KAFKA_BOOTSTRAP_SERVERS: kafka-0.kafka.dev.svc.cluster.local:9092

  # ---------- ACTUATOR (CRITICAL FOR K8s PROBES) ----------
  MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE: health,info
  MANAGEMENT_ENDPOINT_HEALTH_PROBES_ENABLED: "true"
'''

PRODUCT_SERVICE_VALUES_DEV_YAML = '''replicaCount: 1

image:
  repository: leninfitfreak/product-service
  tag: '21089937961'
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8081

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 300m
    memory: 256Mi

startupProbe:
  httpGet:
    path: /actuator/health
    port: 8081
  initialDelaySeconds: 60
  periodSeconds: 10
  failureThreshold: 30

readinessProbe:
  httpGet:
    path: /actuator/health
    port: 8081
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 6

livenessProbe:
  httpGet:
    path: /actuator/health
    port: 8081
  initialDelaySeconds: 60
  periodSeconds: 20
  failureThreshold: 10

env:
  SERVER_PORT: "8081"
  SPRING_DATASOURCE_URL: jdbc:postgresql://postgres.dev.svc.cluster.local:5432/leninkart
  SPRING_DATASOURCE_USERNAME: postgres
  SPRING_DATASOURCE_PASSWORD: postgres
  SPRING_DATASOURCE_DRIVER_CLASS_NAME: org.postgresql.Driver
  SPRING_JPA_DATABASE_PLATFORM: org.hibernate.dialect.PostgreSQLDialect
  SPRING_JPA_HIBERNATE_DDL_AUTO: update
  SPRING_JPA_DEFER_DATASOURCE_INITIALIZATION: 'true'
  SPRING_KAFKA_BOOTSTRAP_SERVERS: kafka-0.kafka.dev.svc.cluster.local:9092
'''

# ============================================================
# HELPER FUNCTIONS
# ============================================================

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def log(message: str, level: str = "INFO"):
    """Print colored log message"""
    colors = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "HEADER": Colors.MAGENTA + Colors.BOLD,
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{color}[{level}]{Colors.RESET} {message}")

def header(title: str):
    """Print section header"""
    print()
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title.center(70)}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")

def section(title: str):
    """Print subsection header"""
    print()
    print(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}▶ {title}{Colors.RESET}")
    print(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")

def backup_file(file_path: Path, backup_dir: Path):
    """Backup a file before modifying"""
    if file_path.exists():
        rel_path = file_path.relative_to(file_path.parents[len(file_path.parents)-2])
        backup_path = backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)
        return True
    return False

def write_file(file_path: Path, content: str):
    """Write content to file, creating directories if needed"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')

# ============================================================
# FIX FUNCTIONS
# ============================================================

class InfraFixer:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.backup_dir = self.repo_path / f"{BACKUP_PREFIX}{TIMESTAMP}"
        self.fixes_applied = []
        self.errors = []
    
    def validate_repo(self) -> bool:
        """Check if this is a valid leninkart-infra repository"""
        required_dirs = [
            "helm/frontend",
            "helm/order-service",
            "helm/product-service",
            "argocd",
        ]
        
        for dir_path in required_dirs:
            if not (self.repo_path / dir_path).exists():
                log(f"Missing directory: {dir_path}", "ERROR")
                return False
        
        return True
    
    def fix_frontend_service(self):
        """Fix frontend service selector to match deployment labels"""
        section("Fix 1: Frontend Service Selector")
        
        service_file = self.repo_path / "helm/frontend/templates/service.yaml"
        
        if backup_file(service_file, self.backup_dir):
            log(f"Backed up: {service_file.name}")
        
        write_file(service_file, FRONTEND_SERVICE_YAML)
        log("Updated frontend service.yaml with correct selector", "SUCCESS")
        self.fixes_applied.append("Frontend service selector fixed (app: frontend)")
    
    def fix_frontend_helpers(self):
        """Add missing _helpers.tpl to frontend chart"""
        section("Fix 2: Frontend Helm Helpers")
        
        helpers_file = self.repo_path / "helm/frontend/templates/_helpers.tpl"
        
        if helpers_file.exists():
            backup_file(helpers_file, self.backup_dir)
            log(f"Backed up existing: {helpers_file.name}")
        
        write_file(helpers_file, FRONTEND_HELPERS_TPL)
        log("Created frontend _helpers.tpl", "SUCCESS")
        self.fixes_applied.append("Frontend _helpers.tpl created")
    
    def fix_frontend_values(self):
        """Fix frontend values.yaml to include container.port"""
        section("Fix 3: Frontend Values")
        
        # Fix base values.yaml
        values_file = self.repo_path / "helm/frontend/values.yaml"
        if backup_file(values_file, self.backup_dir):
            log(f"Backed up: {values_file.name}")
        write_file(values_file, FRONTEND_VALUES_YAML)
        log("Updated frontend values.yaml", "SUCCESS")
        
        # Fix values-dev.yaml
        values_dev_file = self.repo_path / "helm/frontend/values-dev.yaml"
        if backup_file(values_dev_file, self.backup_dir):
            log(f"Backed up: {values_dev_file.name}")
        write_file(values_dev_file, FRONTEND_VALUES_DEV_YAML)
        log("Updated frontend values-dev.yaml", "SUCCESS")
        
        self.fixes_applied.append("Frontend values.yaml updated with container.port")
    
    def fix_order_service_values(self):
        """Fix order-service values-dev.yaml to include service.type"""
        section("Fix 4: Order Service Values")
        
        values_file = self.repo_path / "helm/order-service/values-dev.yaml"
        
        if backup_file(values_file, self.backup_dir):
            log(f"Backed up: {values_file.name}")
        
        write_file(values_file, ORDER_SERVICE_VALUES_DEV_YAML)
        log("Updated order-service values-dev.yaml with service.type", "SUCCESS")
        self.fixes_applied.append("Order-service values-dev.yaml fixed (service.type: ClusterIP)")
    
    def fix_product_service_values(self):
        """Ensure product-service values are correct"""
        section("Fix 5: Product Service Values")
        
        values_file = self.repo_path / "helm/product-service/values-dev.yaml"
        
        if backup_file(values_file, self.backup_dir):
            log(f"Backed up: {values_file.name}")
        
        write_file(values_file, PRODUCT_SERVICE_VALUES_DEV_YAML)
        log("Updated product-service values-dev.yaml", "SUCCESS")
        self.fixes_applied.append("Product-service values-dev.yaml updated")
    
    def generate_report(self):
        """Generate a markdown report of all fixes"""
        report_content = f"""# LeninKart Infrastructure Fix Report

## Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
- **Fixes Applied:** {len(self.fixes_applied)}
- **Errors:** {len(self.errors)}
- **Backup Location:** `{self.backup_dir.name}/`

## Fixes Applied

"""
        for i, fix in enumerate(self.fixes_applied, 1):
            report_content += f"{i}. ✅ {fix}\n"
        
        if self.errors:
            report_content += "\n## Errors\n\n"
            for error in self.errors:
                report_content += f"- ❌ {error}\n"
        
        report_content += """
## Next Steps

### 1. Review Changes
```bash
git status
git diff
```

### 2. Commit and Push
```bash
git add .
git commit -m "fix: correct service selectors and helm templates"
git push origin dev
```

### 3. Sync ArgoCD
```bash
# Option A: Wait for auto-sync (2-3 minutes)

# Option B: Force sync
argocd app sync leninkart-root --force

# Option C: Via ArgoCD UI
# Go to ArgoCD dashboard and click "Sync" on leninkart-root
```

### 4. Verify Deployment
```bash
# Check all pods are running
kubectl get pods -n dev

# Check services have endpoints (should NOT show <none>)
kubectl get endpoints -n dev

# Check ingress
kubectl get ingress -n dev
kubectl describe ingress leninkart-ingress -n dev
```

### 5. Test Services Directly
```bash
# Test product service
kubectl port-forward -n dev svc/leninkart-product-service 8081:8081
curl http://localhost:8081/api/products

# Test order service
kubectl port-forward -n dev svc/leninkart-order-service 8080:8080
curl http://localhost:8080/api/orders

# Test frontend
kubectl port-forward -n dev svc/leninkart-frontend 8082:80
# Open http://localhost:8082 in browser
```

### 6. Test via Ingress
```bash
# Start minikube tunnel (if using minikube)
minikube tunnel

# Get ingress IP
kubectl get ingress -n dev

# Test endpoints
curl http://<INGRESS_IP>/api/products
curl http://<INGRESS_IP>/api/orders
curl http://<INGRESS_IP>/
```

## Troubleshooting

### If pods are still failing:
```bash
# Check pod logs
kubectl logs -n dev -l app=frontend --tail=50
kubectl logs -n dev -l app=product-service --tail=50
kubectl logs -n dev -l app.kubernetes.io/name=order-service --tail=50

# Describe pods for events
kubectl describe pod -n dev -l app=frontend
```

### If services have no endpoints:
```bash
# Verify labels match
kubectl get pods -n dev --show-labels
kubectl get svc -n dev -o wide

# The service selector must match pod labels exactly
```

### If ingress returns 404/502:
```bash
# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Verify backend services exist
kubectl describe ingress leninkart-ingress -n dev
```
"""
        
        report_file = self.repo_path / f"FIX_REPORT_{TIMESTAMP}.md"
        write_file(report_file, report_content)
        return report_file
    
    def run(self):
        """Execute all fixes"""
        header("LENINKART INFRASTRUCTURE AUTO-FIX")
        
        log(f"Repository: {self.repo_path}")
        log(f"Timestamp: {TIMESTAMP}")
        
        # Validate repository
        section("Validating Repository")
        if not self.validate_repo():
            log("This doesn't appear to be a valid leninkart-infra repository!", "ERROR")
            log("Please run this script from the root of the leninkart-infra repo", "ERROR")
            return False
        log("Repository structure validated", "SUCCESS")
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        log(f"Backup directory: {self.backup_dir.name}", "INFO")
        
        # Apply fixes
        try:
            self.fix_frontend_service()
            self.fix_frontend_helpers()
            self.fix_frontend_values()
            self.fix_order_service_values()
            self.fix_product_service_values()
        except Exception as e:
            log(f"Error during fixes: {str(e)}", "ERROR")
            self.errors.append(str(e))
            return False
        
        # Generate report
        section("Generating Report")
        report_file = self.generate_report()
        log(f"Report saved: {report_file.name}", "SUCCESS")
        
        # Print summary
        header("FIX COMPLETE")
        
        print(f"\n{Colors.GREEN}✅ Applied {len(self.fixes_applied)} fixes:{Colors.RESET}")
        for fix in self.fixes_applied:
            print(f"   • {fix}")
        
        print(f"\n{Colors.CYAN}📁 Backup location: {self.backup_dir.name}/{Colors.RESET}")
        print(f"{Colors.CYAN}📄 Report: {report_file.name}{Colors.RESET}")
        
        print(f"\n{Colors.YELLOW}{'='*70}{Colors.RESET}")
        print(f"{Colors.YELLOW}{Colors.BOLD}NEXT STEPS:{Colors.RESET}")
        print(f"{Colors.YELLOW}{'='*70}{Colors.RESET}")
        
        print(f"""
{Colors.WHITE}1. Review changes:{Colors.RESET}
   git status
   git diff

{Colors.WHITE}2. Commit and push:{Colors.RESET}
   git add .
   git commit -m "fix: correct service selectors and helm templates"
   git push origin dev

{Colors.WHITE}3. Sync ArgoCD:{Colors.RESET}
   argocd app sync leninkart-root --force
   
   OR wait for auto-sync (2-3 minutes)

{Colors.WHITE}4. Verify:{Colors.RESET}
   kubectl get pods -n dev
   kubectl get endpoints -n dev
""")
        
        return True


# ============================================================
# MAIN
# ============================================================

def main():
    """Main entry point"""
    # Get repository path from command line or use current directory
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = "."
    
    # Check if path exists
    if not Path(repo_path).exists():
        log(f"Path does not exist: {repo_path}", "ERROR")
        sys.exit(1)
    
    # Run fixer
    fixer = InfraFixer(repo_path)
    success = fixer.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()