# Private Connectivity Options for Bedrock AgentCore

## Option 1: AWS PrivateLink with NLB ⭐ (Best for True Private Access)

### Architecture Changes Required:
1. **Replace ALB with NLB** (Network Load Balancer)
   - NLB required for VPC Endpoint Service
   - Maintains IP-based routing to Fargate tasks

2. **Create VPC Endpoint Service**
   ```bash
   aws ec2 create-vpc-endpoint-service-configuration \
     --network-load-balancer-arns arn:aws:elasticloadbalancing:us-east-1:057716757052:loadbalancer/net/your-nlb/xxx \
     --acceptance-required
   ```

3. **Configure Bedrock AgentCore to Use VPC Endpoint**
   - Check if Bedrock AgentCore supports VPC Endpoint Service names
   - May require AWS Support to enable
   - Endpoint format: `com.amazonaws.vpce.us-east-1.vpce-svc-xxxxx`

### Pros:
- ✅ True private connectivity (no internet traversal)
- ✅ No public IP required
- ✅ Enhanced security

### Cons:
- ❌ Requires NLB instead of ALB (loses Layer 7 features)
- ❌ Bedrock may not support custom VPC Endpoint Services yet
- ❌ Significant architecture change
- ❌ Additional costs (NLB + VPC Endpoint Service)

### Implementation Steps:
```bash
# 1. Create NLB
aws elbv2 create-load-balancer \
  --name fargate-nlb \
  --type network \
  --scheme internal \
  --subnets subnet-xxx subnet-yyy

# 2. Create Target Group (IP type)
aws elbv2 create-target-group \
  --name fargate-nlb-tg \
  --protocol TCP \
  --port 80 \
  --vpc-id vpc-xxx \
  --target-type ip

# 3. Update Fargate task registration logic
# (Similar to current ALB registration but for NLB)

# 4. Create VPC Endpoint Service
aws ec2 create-vpc-endpoint-service-configuration \
  --network-load-balancer-arns arn:aws:elasticloadbalancing:...:loadbalancer/net/fargate-nlb/xxx \
  --acceptance-required

# 5. Get service name and configure in Bedrock (if supported)
```

---

## Option 2: Internal ALB with VPC Peering (If Bedrock Supports)

### Requirements:
1. **Make ALB Internal** (scheme: internal)
2. **VPC Peering** between Bedrock's VPC and your VPC
   - Requires AWS Support/PrivateLink team involvement
   - May not be supported for managed services

### Pros:
- ✅ Keep ALB (Layer 7 features)
- ✅ No public IP

### Cons:
- ❌ Likely NOT supported (Bedrock is fully managed)
- ❌ Would require AWS to peer their VPC with yours

---

## Option 3: Secure Current Architecture (Recommended for Now) ⭐

Keep internet-facing ALB but enhance security:

### 1. Security Group Restrictions
```bash
# Get AWS service IP ranges for us-east-1
# Restrict ALB to only Bedrock service IPs
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 80 \
  --cidr 54.0.0.0/8  # Example: Adjust to Bedrock IP ranges
```

### 2. API Authentication
Add authentication tokens in tool requests:
```python
# In global_fargate_coordinator.py
headers = {
    'Authorization': f'Bearer {SECRET_TOKEN}',
    'X-Request-ID': request_id
}
```

### 3. Use HTTPS with Certificate
```bash
# Add ACM certificate to ALB
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:...:loadbalancer/app/fargate-alb/xxx \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:xxx:certificate/xxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:...
```

### 4. AWS WAF Integration
```bash
# Add WAF to ALB for additional protection
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:xxx:regional/webacl/xxx \
  --resource-arn arn:aws:elasticloadbalancing:...:loadbalancer/app/fargate-alb/xxx
```

### Pros:
- ✅ Works with current architecture
- ✅ No code changes to core logic
- ✅ Significantly improves security
- ✅ Traffic still uses AWS backbone (not public internet)
- ✅ Cost-effective

### Cons:
- ⚠️ Still uses public IP (but secured)
- ⚠️ Not "true" private connectivity

---

## Option 4: Investigate Bedrock VPC Configuration (Future)

### Check if Bedrock AgentCore Supports:
1. **VPC Configuration**: Can you configure AgentCore runtime in your VPC?
2. **VPC Endpoint Service Support**: Can AgentCore connect to VPC Endpoint Services?

### Contact AWS Support:
```
Subject: Bedrock AgentCore VPC Endpoint / PrivateLink Support

Questions:
1. Can Bedrock AgentCore runtime be configured to run in customer VPC?
2. Does AgentCore support connecting to tools via AWS PrivateLink/VPC Endpoint Services?
3. What are recommended architectures for private connectivity between AgentCore and customer resources?
```

---

## Recommendation

### Immediate (Production): Option 3 - Secure Current Architecture
- Implement Security Groups, HTTPS, and authentication
- Traffic already uses AWS backbone (minimal internet exposure)
- Quick to implement, cost-effective

### Future Investigation: Option 1 or 4
- Contact AWS Support about PrivateLink support
- If supported, migrate to NLB + VPC Endpoint Service
- True private connectivity without public IPs

---

## Security Note

**Important**: Even with "public IP", traffic between AWS services typically stays on AWS backbone:
- Bedrock (us-east-1) → ALB (us-east-1) = AWS internal network
- Not true "internet" traversal
- Already reasonably secure

**True Private Access** via PrivateLink provides:
- No public IP exposure
- VPC-level isolation
- Compliance benefits (some regulations require private-only)

---

## Next Steps

1. **Quick Win**: Implement Option 3 security enhancements
2. **Contact AWS Support**: Ask about Bedrock AgentCore PrivateLink support
3. **If Supported**: Plan migration to NLB + VPC Endpoint Service (Option 1)
4. **If Not Supported**: Current architecture with Option 3 is acceptable for most use cases
