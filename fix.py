#!/usr/bin/env python3
"""
LeninKart Kubernetes Diagnostic Script
======================================
This script helps diagnose why /api/products returns 404

Run this on a machine with kubectl access to your cluster.

Usage: python leninkart_diagnose.py
"""

import subprocess
import sys
import re

NAMESPACE = "dev"

# ============================================================
# COLORS
# ============================================================

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def log(msg, level="INFO"):
    colors = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "HEADER": Colors.MAGENTA + Colors.BOLD,
    }
    color = colors.get(level, Colors.WHITE)
    print(f"{color}[{level}]{Colors.RESET} {msg}")

def header(title):
    print()
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title.center(70)}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")

def section(title):
    print()
    print(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")
    print(f"{Colors.YELLOW}▶ {title}{Colors.RESET}")
    print(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")

# ============================================================
# KUBECTL HELPERS
# ============================================================

def run_kubectl(cmd, capture=True):
    """Run kubectl command and return output"""
    full_cmd = f"kubectl {cmd}"
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=capture,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def kubectl_get(resource, namespace=NAMESPACE, output="wide"):
    """Get kubernetes resources"""
    cmd = f"get {resource} -n {namespace}"
    if output:
        cmd += f" -o {output}"
    return run_kubectl(cmd)

# ============================================================
# DIAGNOSTIC CHECKS
# ============================================================

def check_pods():
    """Check if all pods are running"""
    section("1. POD STATUS")
    
    code, out, err = kubectl_get("pods")
    if code != 0:
        log(f"Failed to get pods: {err}", "ERROR")
        return False
    
    print(out)
    
    # Check for issues
    issues = []
    if "CrashLoopBackOff" in out:
        issues.append("Some pods are in CrashLoopBackOff")
    if "ImagePullBackOff" in out:
        issues.append("Some pods have image pull issues")
    if "Pending" in out:
        issues.append("Some pods are pending")
    if "0/1" in out or "0/2" in out:
        issues.append("Some pods are not ready")
    
    if issues:
        for issue in issues:
            log(issue, "WARNING")
        return False
    
    log("All pods appear healthy", "SUCCESS")
    return True

def check_services():
    """Check services configuration"""
    section("2. SERVICES")
    
    code, out, err = kubectl_get("services")
    if code != 0:
        log(f"Failed to get services: {err}", "ERROR")
        return False
    
    print(out)
    
    # Check for required services
    required = ["leninkart-frontend", "leninkart-product-service", "leninkart-order-service"]
    missing = []
    
    for svc in required:
        if svc not in out:
            missing.append(svc)
    
    if missing:
        log(f"Missing services: {', '.join(missing)}", "ERROR")
        return False
    
    log("All required services exist", "SUCCESS")
    return True

def check_endpoints():
    """Check if services have endpoints (CRITICAL)"""
    section("3. ENDPOINTS (CRITICAL)")
    
    code, out, err = kubectl_get("endpoints")
    if code != 0:
        log(f"Failed to get endpoints: {err}", "ERROR")
        return False
    
    print(out)
    
    # Check for <none> endpoints
    issues = []
    lines = out.strip().split('\n')
    
    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 2:
            svc_name = parts[0]
            endpoints = parts[1] if len(parts) > 1 else ""
            
            if endpoints == "<none>" or not endpoints:
                issues.append(f"{svc_name} has NO endpoints (selector mismatch!)")
    
    if issues:
        for issue in issues:
            log(issue, "ERROR")
        log("Services with <none> endpoints cannot route traffic!", "ERROR")
        return False
    
    log("All services have endpoints", "SUCCESS")
    return True

def check_ingress():
    """Check ingress configuration"""
    section("4. INGRESS")
    
    code, out, err = kubectl_get("ingress")
    if code != 0:
        log(f"Failed to get ingress: {err}", "ERROR")
        return False
    
    print(out)
    
    # Get detailed ingress info
    code, out, err = run_kubectl(f"describe ingress leninkart-ingress -n {NAMESPACE}")
    if code == 0:
        print("\nIngress Details:")
        print(out)
    
    return True

def check_service_selectors():
    """Check if service selectors match pod labels"""
    section("5. SELECTOR MATCHING (ROOT CAUSE CHECK)")
    
    services_to_check = [
        ("leninkart-product-service", "product-service"),
        ("leninkart-order-service", "order-service"),
        ("leninkart-frontend", "frontend"),
    ]
    
    all_good = True
    
    for svc_name, expected_app in services_to_check:
        print(f"\n{Colors.CYAN}Checking {svc_name}:{Colors.RESET}")
        
        # Get service selector
        code, out, err = run_kubectl(
            f"get svc {svc_name} -n {NAMESPACE} -o jsonpath='{{.spec.selector}}'"
        )
        
        if code != 0:
            log(f"  Service {svc_name} not found", "ERROR")
            all_good = False
            continue
        
        print(f"  Service selector: {out}")
        
        # Get pods with matching labels
        # Try to extract the selector key-value
        selector_str = out.strip().strip("'")
        
        # Get pods
        code, pods_out, err = run_kubectl(
            f"get pods -n {NAMESPACE} -o wide --show-labels"
        )
        
        if code == 0:
            # Check if any pod matches
            matching_pods = []
            for line in pods_out.split('\n'):
                if expected_app in line.lower() or f"app={expected_app}" in line:
                    matching_pods.append(line.split()[0] if line.split() else "")
            
            if matching_pods:
                log(f"  Found matching pods: {', '.join(matching_pods)}", "SUCCESS")
            else:
                log(f"  NO PODS MATCH the service selector!", "ERROR")
                all_good = False
    
    return all_good

def check_product_service_directly():
    """Test product service directly via port-forward"""
    section("6. DIRECT SERVICE TEST")
    
    log("To test product-service directly, run:", "INFO")
    print(f"""
{Colors.WHITE}# In terminal 1 - Start port-forward:{Colors.RESET}
kubectl port-forward -n {NAMESPACE} svc/leninkart-product-service 8081:8081

{Colors.WHITE}# In terminal 2 - Test the endpoint:{Colors.RESET}
curl http://localhost:8081/api/products

{Colors.WHITE}# Expected: [] (empty array) or list of products{Colors.RESET}
{Colors.WHITE}# If you get connection refused, the pod isn't running or service is misconfigured{Colors.RESET}
""")

def check_pod_labels():
    """Show all pod labels for debugging"""
    section("7. POD LABELS (for selector matching)")
    
    code, out, err = run_kubectl(f"get pods -n {NAMESPACE} --show-labels")
    if code == 0:
        print(out)
    else:
        log(f"Failed: {err}", "ERROR")

def check_deployment_labels():
    """Check deployment and pod template labels"""
    section("8. DEPLOYMENT POD TEMPLATE LABELS")
    
    deployments = ["product-service", "frontend"]
    
    for deploy in deployments:
        code, out, err = run_kubectl(
            f"get deployment -n {NAMESPACE} -l app={deploy} -o jsonpath='{{.items[*].spec.template.metadata.labels}}'"
        )
        if code == 0 and out:
            print(f"{deploy}: {out}")
        else:
            # Try without label filter
            code, out, err = run_kubectl(
                f"get deployment {deploy} -n {NAMESPACE} -o jsonpath='{{.spec.template.metadata.labels}}'"
            )
            if code == 0:
                print(f"{deploy}: {out}")
            else:
                log(f"Could not get labels for {deploy}", "WARNING")

def generate_fix_commands():
    """Generate commands to fix common issues"""
    section("9. QUICK FIX COMMANDS")
    
    print(f"""
{Colors.YELLOW}If endpoints show <none>, the service selector doesn't match pod labels.{Colors.RESET}

{Colors.WHITE}Option 1: Patch the service selector (quick fix):{Colors.RESET}

# For product-service (if pods have label app=product-service):
kubectl patch svc leninkart-product-service -n {NAMESPACE} -p '{{"spec":{{"selector":{{"app":"product-service"}}}}}}'

# For order-service (if pods have labels app.kubernetes.io/name=order-service):
kubectl patch svc leninkart-order-service -n {NAMESPACE} -p '{{"spec":{{"selector":{{"app.kubernetes.io/name":"order-service"}}}}}}'

# For frontend:
kubectl patch svc leninkart-frontend -n {NAMESPACE} -p '{{"spec":{{"selector":{{"app":"frontend"}}}}}}'

{Colors.WHITE}Option 2: Force ArgoCD to resync:{Colors.RESET}
argocd app sync leninkart-root --force --prune

{Colors.WHITE}Option 3: Delete and let ArgoCD recreate:{Colors.RESET}
kubectl delete svc leninkart-product-service leninkart-order-service leninkart-frontend -n {NAMESPACE}
# Wait for ArgoCD to recreate them

{Colors.WHITE}Verify endpoints after fix:{Colors.RESET}
kubectl get endpoints -n {NAMESPACE}
""")

# ============================================================
# MAIN
# ============================================================

def main():
    header("LENINKART KUBERNETES DIAGNOSTICS")
    
    log(f"Namespace: {NAMESPACE}")
    
    # Run all checks
    results = {
        "pods": check_pods(),
        "services": check_services(),
        "endpoints": check_endpoints(),
        "selectors": check_service_selectors(),
    }
    
    check_ingress()
    check_pod_labels()
    check_deployment_labels()
    check_product_service_directly()
    generate_fix_commands()
    
    # Summary
    header("DIAGNOSIS SUMMARY")
    
    if not results["endpoints"]:
        log("ROOT CAUSE: Service endpoints are empty!", "ERROR")
        log("The service selector does not match any pod labels.", "ERROR")
        log("Run the patch commands above to fix.", "INFO")
    elif not results["pods"]:
        log("ROOT CAUSE: Pods are not healthy!", "ERROR")
        log("Check pod logs: kubectl logs -n dev <pod-name>", "INFO")
    elif not results["services"]:
        log("ROOT CAUSE: Services are missing!", "ERROR")
        log("Check ArgoCD sync status", "INFO")
    else:
        log("Basic checks passed. Issue may be in ingress routing.", "WARNING")
        log("Try testing services directly via port-forward.", "INFO")
    
    print()

if __name__ == "__main__":
    main()