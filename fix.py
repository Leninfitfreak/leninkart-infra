#!/usr/bin/env python3
"""
Quick fix for LeninKart Ingress - removes annotations and verifies
"""

import subprocess
from pathlib import Path

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.returncode

def check_current_ingress():
    """Check what the current ingress looks like"""
    print("\n" + "="*60)
    print("📋 CURRENT INGRESS CONFIGURATION")
    print("="*60)
    
    output, code = run("kubectl get ingress leninkart-ingress -n dev -o yaml")
    
    if code == 0:
        # Show the important parts
        for line in output.split('\n'):
            if any(x in line for x in ['annotations:', 'path:', 'pathType:', 'backend:', 'serviceName:', 'servicePort:', 'name: leninkart']):
                print(line)
        
        # Check for problematic annotation
        if 'use-regex' in output or 'rewrite-target' in output:
            print("\n⚠️  Found problematic annotations!")
            return True
        else:
            print("\n✅ No problematic annotations found")
            return False
    return False

def apply_fixed_ingress():
    """Apply the correct ingress configuration directly"""
    print("\n" + "="*60)
    print("🔧 APPLYING FIXED INGRESS")
    print("="*60)
    
    # The correct ingress YAML
    ingress_yaml = """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: leninkart-ingress
  namespace: dev
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /api/products
        pathType: Prefix
        backend:
          service:
            name: leninkart-product-service
            port:
              number: 8081
      - path: /api/orders
        pathType: Prefix
        backend:
          service:
            name: leninkart-order-service
            port:
              number: 8080
      - path: /
        pathType: Prefix
        backend:
          service:
            name: leninkart-frontend
            port:
              number: 80
"""
    
    # Write to temp file
    temp_file = Path("temp_ingress.yaml")
    temp_file.write_text(ingress_yaml)
    
    print("Applying configuration...")
    output, code = run("kubectl apply -f temp_ingress.yaml")
    
    if code == 0:
        print("✅ Ingress updated successfully!")
        print(output)
    else:
        print("❌ Failed to update ingress")
        print(output)
    
    # Clean up
    temp_file.unlink()
    
    return code == 0

def verify_ingress():
    """Verify the ingress is now correct"""
    print("\n" + "="*60)
    print("✅ VERIFYING INGRESS")
    print("="*60)
    
    output, code = run("kubectl describe ingress leninkart-ingress -n dev")
    
    if code == 0:
        print("\nIngress Rules:")
        in_rules = False
        for line in output.split('\n'):
            if 'Rules:' in line:
                in_rules = True
            if in_rules:
                if line.strip() and any(x in line for x in ['Path', 'Backend', '/', 'api']):
                    print(f"  {line.strip()}")
                if 'Annotations:' in line and in_rules:
                    break

def test_connection():
    """Provide test commands"""
    print("\n" + "="*60)
    print("🧪 TEST THE FIX")
    print("="*60)
    print("\n1. Wait 10 seconds for ingress controller to update")
    print("\n2. Refresh your browser at http://localhost:8081")
    print("\n3. If still not working, port-forward directly:")
    print("   kubectl port-forward -n dev svc/leninkart-product-service 8082:8081")
    print("   Then visit: http://localhost:8082/api/products")
    print("\n4. Check ingress address:")
    print("   kubectl get ingress -n dev")
    print("\n5. Ensure minikube tunnel is running in another terminal:")
    print("   minikube tunnel")

def main():
    print("\n🚀 LeninKart Ingress Quick Fix")
    
    # Check current state
    has_issue = check_current_ingress()
    
    if has_issue or True:  # Always apply the fix
        # Apply the fix
        success = apply_fixed_ingress()
        
        if success:
            # Verify
            verify_ingress()
            
            # Provide test instructions
            test_connection()
            
            print("\n" + "="*60)
            print("✅ INGRESS FIX COMPLETE!")
            print("="*60)
            print("\nThe ingress has been updated.")
            print("Wait 10 seconds and refresh your browser.")
            print("\nIf the issue persists, the problem might be:")
            print("1. Minikube tunnel not running")
            print("2. ArgoCD overwriting the ingress (disable auto-sync temporarily)")
            print("="*60)
        else:
            print("\n❌ Fix failed. Try manually:")
            print("kubectl edit ingress leninkart-ingress -n dev")
            print("Remove the 'annotations' section")

if __name__ == "__main__":
    main()