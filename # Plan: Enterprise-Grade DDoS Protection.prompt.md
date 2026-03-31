# Plan: Enterprise-Grade DDoS Protection Roadmap for Frappe CRM

## Executive Summary

**Objective:** Implement comprehensive multi-layer DDoS protection for self-hosted Frappe/ERPNext CRM system supporting 100-1k concurrent users with 99.9% uptime SLA and GDPR compliance.

**Recommended Approach:** Three-layer defense strategy combining:
1. **Network/Transport Layer (L3/L4):** nginx reverse proxy + HAProxy load balancing + IP reputation filtering
2. **Application Layer (L7):** API rate limiting + bot detection + request validation
3. **Monitoring/Response Layer:** Real-time traffic analysis + automated mitigation + alerting

**Key Infrastructure Changes:**
- Replace direct Gunicorn exposure with nginx reverse proxy
- Implement HAProxy load balancer for horizontal scaling
- Add Redis-based rate limiting middleware
- Deploy ELK stack for traffic analysis
- Containerize services with Docker Compose (production)
- Implement automated failover and health checks

**Timeline:** 6 phases over 6-8 weeks with parallel workstreams
**Resource Commitment:** 2 senior engineers (infrastructure/security) + 1 DevOps + 1 monitoring specialist

---

## Phase 1: Foundation & Architecture (Week 1-2) — SEQUENTIAL

### 1.1 Network Architecture Assessment & Design
- **Action:** Map current network topology, document all exposed ports/services
  - Current: Port 8000 (Gunicorn), 9000 (Socket.IO), 6787 (watcher) directly exposed
  - Gaps: No reverse proxy, no load balancer, no WAF, unencrypted traffic
- **Deliverable:** Network diagram showing proposed architecture with protection layers
- **Owner:** Infrastructure Lead

### 1.2 Deployment Infrastructure Containerization
- **Action:** Build production-ready Docker Compose configuration with:
  - nginx reverse proxy service (port 80/443 only exposed)
  - HAProxy load balancer (internal routing)
  - MariaDB client (pooling layer via ProxySQL)
  - Redis cache/queue/socket.io (existing, add persistence)
  - Frappe gunicorn workers (scaled to 3-5 instances)
  - Socket.IO service (Node.js with clustering)
  - ELK stack (Elasticsearch, Logstash, Kibana)
  - Prometheus + Grafana (metrics collection)
  - Filebeat + Auditbeat (log shipping)
- **Scope:** Use existing `docker_compose.prod.yml` as base; add orchestration for 10+ services
- **Owner:** DevOps Engineer
- *Depends on: 1.1*

### 1.3 HTTPS/TLS Foundation Setup
- **Action:** Generate Let's Encrypt certificates (auto-renewal with certbot)
  - Domain mapping: `your-crm.domain.com` (replace localhost:8000)
  - SSL/TLS 1.2+ enforced, HTTP→HTTPS redirect
  - CSR signing and certificate chain validation
- **Config files to create:**
  - `/etc/nginx/ssl/` (cert storage)
  - `/opt/certbot/` (renewal automation)
- **Owner:** Infrastructure Lead
- *Depends on: 1.1*

---

## Phase 2: Reverse Proxy & L3/L4 DDoS Protection (Week 2-3) — PARALLEL with Phase 1

### 2.1 nginx Reverse Proxy Implementation
- **Action:** Deploy nginx as primary reverse proxy + SSL termination
- **Configuration highlights:**
  - Upstream: Round-robin to 3-5 Frappe Gunicorn Workers (port 8000)
  - WebSocket upgrade: Pass Socket.IO (port 9000) with proper headers
  - Connection timeout: 30s read, 60s write
  - Keepalive: 32 idle connections per upstream server
  - Buffer sizes: 4MB client max body size, 16MB buffer for proxying
- **File:** `/etc/nginx/conf.d/frappe-crm.conf`
- **Security layers in nginx:**
  - Rate limiting (Phase 2.3 below)
  - Client validation (Host header, User-Agent)
  - Compression disabled for sensitive data
  - Security headers: X-Frame-Options, X-Content-Type-Options, CSP
- **Owner:** Infrastructure Lead
- *Parallel with: 2.2, 2.3*

### 2.2 HAProxy Load Balancer & Failover
- **Action:** Deploy HAProxy for internal load balancing and health checks
- **Configuration highlights:**
  - Frontend: Listen on port 8080 (upstream from nginx)
  - Backend: 3-5 Frappe Gunicorn workers (round-robin with health checks)
  - Health checks: HTTP GET /api/method/frappe.client.get_count every 5s, 3 failures to mark down
  - Session persistence: Source IP hashing (stick-table) for WebSocket clients
  - Connection limits per backend: 100 max concurrent
  - Timeout: client 30s, server 30s, connect 5s
  - Stats page: `/stats` (restricted to localhost for monitoring)
- **File:** `/etc/haproxy/haproxy.cfg`
- **Owner:** DevOps Engineer
- *Parallel with: 2.1, 2.3*

### 2.3 L3/L4 DDoS Mitigation Filters
- **Action:** Implement SYN flood, UDP flood, and connection exhaustion protections
- **Techniques:**
  - nginx rate limiting: 10 req/sec per IP, burst 20 (configurable per endpoint class)
  - nginx connection limiting: 10 concurrent connections per IP
  - TCP SYN cookies: Enable in kernel (`net.ipv4.tcp_syncookies = 1`)
  - IP reputation filtering: Block known malicious IPs (using blacklist)
  - GeoIP filtering: Optional blocking of traffic outside service regions (GDPR-safe)
  - Slow-read attack protection: Increase client body timeout to 60s (vs default 12s)
- **File:** `/etc/nginx/nginx.conf` + kernel params in `/etc/sysctl.conf`
- **Owner:** Infrastructure Lead
- *Parallel with: 2.1, 2.2*

### 2.4 Validation: Load Balance Testing
- **Action:** Automated load testing to confirm 99.9% uptime under normal + stress load
  - Test tool: Apache JMeter or locust against HAProxy
  - Scenarios: 500 req/sec sustained, 2000 req/sec burst, 50% packet loss simulation
  - Validation: All requests served within SLA, no worker crashes
- **Owner:** QA / Infrastructure Lead
- *Depends on: 2.1, 2.2, 2.3*

---

## Phase 3: Application Layer (L7) DDoS Protection (Week 3-4) — SEQUENTIAL

### 3.1 Frappe API Rate Limiting Middleware
- **Action:** Implement request validation and rate limiting at Frappe application level
- **Approach:**
  - Create custom Frappe middleware hook (in `/apps/assistant_crm/` or new `ddos_protection` app)
  - Use Redis for distributed rate limiting (existing Redis instances available)
  - Rate limits by API endpoint class:
    * Authentication endpoints (login): 5 req/min per IP
    * Data read (GET): 100 req/min per user, 500 req/min per IP
    * Data write (POST/PUT): 20 req/min per user, 100 req/min per IP
    * Report generation: 2 req/min per user
    * File upload: 10 files/hour per user, 100 MB/hour per user
- **Implementation files:**
  - Create `frappe-bench/apps/ddos_protection/ddos_protection/middleware.py`
  - Hook in `hooks.py`: `before_request` handler
  - Config in site_config.json: `ddos_rate_limits = {...}`
- **Fallback:** Cache-friendly 429 response prevents cascading failures
- **Owner:** Senior Python/Frappe Developer
- *Depends on: Phase 2 completion*

### 3.2 Request Validation & Bot Detection
- **Action:** Implement CAPTCHA challenge + behavioral analysis for suspicious requests
- **Techniques:**
  - Validate request patterns:
    * Missing/invalid User-Agent header → challenge
    * Unusual header combinations (tools/scrapers) → challenge
    * Rapid sequential endpoint calls from same IP → throttle
    * Requests without proper Frappe CSRF token → reject
  - Optional: reCAPTCHA v3 integration for high-risk endpoints
  - Log suspicious patterns to monitoring system
- **Tools:** Use Frappe hooks + custom middleware
- **Owner:** Senior Python/Frappe Developer
- *Depends on: 3.1*

### 3.3 API Endpoint Segmentation
- **Action:** Separate API traffic from UI traffic for independent rate limiting
- **Configuration:** nginx upstream groups
  - Group 1: UI endpoints (login, dashboard, forms) - relaxed limits
  - Group 2: Core APIs (CRUD operations) - strict limits  
  - Group 3: Report/Bulk APIs (batch operations) - very strict limits
  - Group 4: Public endpoints (if any) - separate pool
- **File:** `/etc/nginx/conf.d/frappe-crm.conf` (location blocks per group)
- **Owner:** Infrastructure Lead
- *Depends on: 2.1*

### 3.4 Request Size & Content Validation
- **Action:** Prevent slowloris and payload-based attacks
- **Configuration:**
  - Max upload size: 100 MB (site-wide), 50 MB (individual files)
  - Max request body size in nginx: 100 MB
  - Max form fields: 1000
  - Max form field size: 10 MB
  - Reject oversized requests with 413 error
  - Timeout unfinished uploads after 30 minutes
- **Files:** nginx config + Frappe site_config.json
- **Owner:** Infrastructure Lead
- *Parallel with: 3.1, 3.2*

### 3.5 Validation: L7 Attack Simulation
- **Action:** Test application-layer defenses
  - Scenarios: 
    * HTTP flood (1000+ req/sec from single IP)
    * Slowloris (slow headers, connections held open)
    * Binary attack (malformed payloads)
    * Bot patterns (automated crawling/scraping)
  - Validation: Rate limits enforce, no database exhaustion, minimal latency jitter
- **Tools:** Custom Python script or WireShark simulation
- **Owner:** Security Engineer
- *Depends on: 3.1, 3.2, 3.3, 3.4*

---

## Phase 4: Monitoring, Alerting & Auto-Response (Week 4-5) — SEQUENTIAL

### 4.1 Traffic Analysis & Anomaly Detection
- **Action:** Deploy ELK stack (Elasticsearch, Logstash, Kibana) for real-time traffic monitoring
- **Configuration:**
  - Logstash: Ingest nginx access logs, HAProxy logs, Frappe logs
  - Parse fields: source IP, endpoint, response time, status code, payload size, User-Agent
  - Elasticsearch: Index traffic with 7-day retention (GDPR-compliant)
  - Kibana: Dashboards for
    * Traffic volume over time (requests/sec, bytes/sec)
    * Top IPs, endpoints, user agents
    * Response time distribution (p50, p95, p99)
    * Error rate by type (4xx, 5xx)
    * Geographic origin (if GeoIP enabled)
  - Anomaly detection: Statistical baselines for "normal" traffic; alert on >2σ deviation
- **Files:** 
  - `/etc/logstash/conf.d/nginx-frappe.conf`
  - Kibana dashboards (JSON export)
- **Owner:** Monitoring Specialist + DevOps
- *Depends on: Phase 2 & 3 completion*

### 4.2 Real-Time Alerting System
- **Action:** Configure automated alerts for DDoS indicators
- **Alert rules:**
  - Requests/sec > 5x baseline (e.g., >1000 req/sec) → P1 alert
  - Any IP with >100 failed auth attempts in 5 min → auto-block
  - Response time p99 > 5 seconds sustained → P2 alert
  - Error rate > 5% sustained → P2 alert
  - Single IP generating > 50% of traffic → P1 investigation alert
  - Unusual geographic spike → P2 alert
  - Slowloris pattern detected (slow client connections) → auto-challenge/block
- **Tools:** Prometheus rules + Alertmanager or ELK Watcher
- **Notification channels:** Slack, email, PagerDuty (for critical)
- **Owner:** Monitoring Specialist
- *Depends on: 4.1*

### 4.3 Automated Mitigation Engine
- **Action:** Implement auto-response to detected attacks
- **Responses:**
  - Tier 1 (100-500 req/min from IP): Serve stale cache if available, increase timeout
  - Tier 2 (500-1000 req/min): Rate limit to 10 req/sec, serve static responses
  - Tier 3 (>1000 req/min): IP temporary block (in nginx ngx_http_geo_module), 15-min auto-unblock
  - Tier 4 (sustained attack): Manual review + ops team escalation
- **Implementation:** Custom Python script polling Prometheus/ELK, modifying nginx geo.conf dynamically
- **Fallback:** Manual override via admin dashboard/API
- **Owner:** DevOps Engineer + Monitoring Specialist
- *Depends on: 4.2*

### 4.4 Logging & Compliance Audit Trail
- **Action:** Implement queryable audit logs for GDPR compliance
- **Requirements:**
  - Log all authentication attempts (success/failure), IP, timestamp
  - Log all data access (who accessed what, when)
  - Log all mitigation events (blocked IPs, rate limits enforced)
  - Retention: 90 days (configurable per GDPR requirements)
  - Anonymize IPs after 60 days in Kibana (GDPR safe-harbor)
  - Exportable reports: Monthly security summary + attack incidents
- **Files:** Logstash filters + Kibana saved searches
- **Owner:** Security Engineer + Compliance Officer
- *Depends on: 4.1*

---

## Phase 5: Horizontal Scaling & Redundancy (Week 5-6) — PARALLEL

### 5.1 Worker Scaling & Auto-Recovery
- **Action:** Configure Frappe to run multiple worker instances with automatic restart
- **Setup:**
  - Scale from 1 Gunicorn worker to 3-5 workers (CPU-dependent: 1 worker per 2 CPU cores)
  - HAProxy health checks every 5s; remove unhealthy workers within 15s
  - Automatic restart policy: Restart failed workers within 30s (systemd or Docker)
  - Monitor: Worker memory usage, crash rates
- **Files:** `frappe-bench/Procfile` + systemd service files
- **Owner:** DevOps Engineer
- *Parallel with: 5.2, 5.3*

### 5.2 Redis Redundancy & Persistence
- **Action:** Upgrade Redis from single instances to HA configuration
- **Current architecture:** 3 separate Redis instances (cache, queue, socket.io)
- **Improvements:**
  - Add Redis persistence: RDB snapshots + AOF (append-only file)
  - Redis Sentinel for automatic failover (master-slave replication)
  - Redis cluster (optional, for very high load): Partition across multiple Redis nodes
  - Backup strategy: Daily snapshots to S3/NAS, 7-day retention
- **Files:** Redis configuration files + Sentinel config
- **Owner:** DevOps Engineer
- *Parallel with: 5.1, 5.3*

### 5.3 Database Connection Pooling
- **Action:** Add ProxySQL as connection pool layer for MariaDB
- **Current issue:** Direct Gunicorn → MariaDB connection exhaustion under load
- **Solution:** ProxySQL middleman
  - Max connections to MariaDB: 100 (vs direct: unlimited risk)
  - ProxySQL max clients: 1000
  - Connection reuse: Reduce connection overhead by 70%
  - Query caching: Cache frequent queries (e.g., site config lookups)
  - Load balancing: Distribute across multiple MariaDB replicas (if available)
- **File:** `/etc/proxysql/proxysql.cnf`
- **Owner:** DevOps Engineer + DBA
- *Parallel with: 5.1, 5.2*

### 5.4 DNS Failover & Geographic Load Balancing
- **Action:** Configure DNS-level failover for high availability
- **Implementation:**
  - Primary: DNS A record pointing to main server
  - Secondary: A record pointing to standby server (optional, for enterprise HA)
  - Health check: External monitoring service pings both servers every 30s
  - Failover: DNS updates within 60s of primary failure (TTL = 60)
- **Tool:** Route53 (AWS) or equivalent self-hosted DNS with dynamic updates
- **Owner:** Infrastructure Lead
- *Parallel with: 5.1, 5.2, 5.3*

---

## Phase 6: Testing, Hardening & Go-Live (Week 6-8) — SEQUENTIAL

### 6.1 End-to-End Integration Testing
- **Action:** Validate entire stack before production deployment
- **Test scenarios:**
  1. **Functional:** Login, CRUD operations, report generation, file uploads all work through nginx
  2. **Load:** 500 concurrent users, 2000 req/sec sustained for 1 hour
  3. **Failover:** Kill one worker → requests route to others, no downtime
  4. **SSL:** HTTPS endpoints work, certificate auto-renewal doesn't break service
  5. **Caching:** Rate limiting kicks in at threshold, doesn't block legitimate users
  6. **Logging:** All requests logged in ELK, audit trail complete
  7. **Monitoring:** Alerts trigger correctly, thresholds sensible
  8. **Compliance:** No IP leaks in logs beyond anon window, GDPR Data Subject Access Request works
- **Owner:** QA Lead + Senior Engineer
- *Depends on: Phases 1-5 complete*

### 6.2 Attack Simulation & Defense Validation
- **Action:** Conduct authorized penetration testing to validate DDoS mitigations
- **Test attacks:**
  1. **SYN Flood:** 100k pps → Kubernetes ingress blocks, no service impact
  2. **UDP Flood:** Similar, validated at kernel level
  3. **HTTP Flood:** 10k req/sec from 100 IPs → Rate limiting enforces, response time stable
  4. **Slowloris:** 1000 slow clients → Time-out handled, workers freed
  5. **API Abuse:** Rapid endpoint cycling → CAPTCHA challenges triggered, logs suspicious
  6. **Mixed attack:** Multi-vector DDoS → Graceful degradation, no crash
- **Tool:** Custom Python script or commercial tool (Imperva, Radware simulation)
- **Validation criteria:** 99.9% uptime maintained, no data loss, no service crashes
- **Owner:** Security Engineer + Penetration Tester
- *Depends on: Phase 6.1 pass*

### 6.3 Documentation & Runbooks
- **Action:** Create operational documentation for incident response
- **Deliverables:**
  1. **Architecture diagram:** Network topology, all services, data flow
  2. **Security controls summary:** What protections are in place, how they work
  3. **Rate limit tuning guide:** How to adjust limits per scenario
  4. **Incident response runbook:**
     - Detection: How to identify attack in Kibana/Prometheus
     - Immediate action: Manual IP blocks, cache purging, worker restart
     - Escalation: When to page on-call, who to contact
     - Post-incident: Analysis, tuning, lessons learned
  5. **Maintenance procedures:** Certificate renewal, log rotation, Redis backup/restore, database dump
  6. **Disaster recovery plan:** RPO/RTO targets, backup restore procedures
- **Owner:** Technical Writer + Senior Engineer
- *Parallel with: 6.2*

### 6.4 Phased Production Rollout
- **Action:** Deploy to production with minimal downtime
- **Timeline:**
  - **Day 1 (Prep):** Stage all changes, validate in staging environment mirrors production
  - **Day 2 (Cutover, 10 PM - 6 AM low-traffic window):**
    1. Enable nginx reverse proxy (but keep direct connections as fallback)
    2. Route 10% traffic through nginx for 1 hour (monitor error rates)
    3. Route 50% traffic for 2 hours
    4. Route 100% traffic, monitor for 3 hours
    5. Disable direct connections, finalize cutover
  - **Day 3 onwards:** Monitor 24/7, stand by to rollback if issues
- **Rollback plan:** Revert DNS, restore previous nginx config, 5-min restore time
- **Owner:** DevOps Lead + On-Call Team
- *Depends on: 6.1, 6.2, 6.3*

### 6.5 Post-Go-Live Hardening (Week 8+, Ongoing)
- **Action:** Fine-tune limits, patch vulnerabilities, optimize performance
- **Tasks:**
  - **Week 1:** Review actual traffic patterns, adjust rate limits to real baseline
  - **Week 2:** Patch any CVEs in nginx, Frappe, dependencies
  - **Week 4:** Performance review - optimize worker count, cache hit rates, connection pooling
  - **Week 8:** Full security audit, penetration test with real DDoS attack simulation service
  - **Ongoing:** Monthly reviews, quarterly disaster recovery drills
- **Owner:** DevOps Lead + Security Team
- *Parallel with: Production operations*

---

## Technology Stack & Configuration Summary

| Layer | Technology | Purpose | Configuration |
|-------|-----------|---------|----------------|
| **Entry Point** | nginx 1.24+ | Reverse proxy, TLS termination, rate limiting | `/etc/nginx/conf.d/frappe-crm.conf` |
| **Load Balancing** | HAProxy 2.8+ | Internal request distribution, health checks | `/etc/haproxy/haproxy.cfg` |
| **DDoS Filtering** | Linux kernel + iptables | SYN cookies, connection tracking | `/etc/sysctl.conf` |
| **Application** | Frappe 15 + custom middleware | API rate limiting, bot detection | `/apps/ddos_protection/` |
| **Caching/Rate Limit State** | Redis (3 instances) | Distributed rate limit counters | Existing, add Sentinel |
| **Connection Pooling** | ProxySQL 2.5+ | Database connection management | `/etc/proxysql/proxysql.cnf` |
| **Metrics** | Prometheus + Grafana | Traffic metrics, performance monitoring | `/etc/prometheus/` + dashboards |
| **Logs** | ELK Stack (7.17+) | Traffic analysis, audit logs, anomaly detection | `/etc/logstash/conf.d/` + Kibana |
| **Auto-Response** | Custom Python script | Automated mitigation trigger | `/opt/ddos_mitigator/` |
| **Certificates** | Let's Encrypt + certbot | HTTPS automation, renewal | `/etc/letsencrypt/` |

---

## Relevant Files to Create/Modify

### Docker & Orchestration
- `docker-compose.prod.yml` — **NEW** (currently empty, now production-ready with all services)
- `frappe_bench/Procfile` — Modify to scale workers, add new services

### nginx Configuration
- `/etc/nginx/nginx.conf` — Modify: L3/L4 protections, worker processes
- `/etc/nginx/conf.d/frappe-crm.conf` — **NEW** (full reverse proxy config)
- `/etc/nginx/geo.conf` — **NEW** (IP reputation blacklist, auto-populated by mitigation engine)
- `/etc/nginx/cert/` — Store Let's Encrypt certificates

### HAProxy Configuration
- `/etc/haproxy/haproxy.cfg` — **NEW** (load balancer config with health checks)
- `/opt/haproxy/stats.sh` — **NEW** (HAProxy stats scraper for monitoring)

### Frappe DDoS Middleware
- `frappe_bench/apps/ddos_protection/ddos_protection/__init__.py` — **NEW** (app initialization)
- `frappe_bench/apps/ddos_protection/ddos_protection/middleware.py` — **NEW** (rate limiting logic)
- `frappe_bench/apps/ddos_protection/hooks.py` — **NEW** (Frappe integration points)
- `frappe_bench/sites/wcfcb/site_config.json` — Modify: Add `ddos_rate_limits` config

### Monitoring & Alerting
- `/etc/prometheus/prometheus.yml` — **NEW** (metrics scraping)
- `/etc/prometheus/rules/ddos.yml` — **NEW** (alert rules)
- `/opt/alertmanager/config.yml` — **NEW** (routing, Slack/email)
- `/etc/logstash/conf.d/nginx-frappe.conf` — **NEW** (log parsing)
- `/opt/kibana/dashboards/` — **NEW** (traffic analysis dashboards)

### Auto-Response Engine
- `/opt/ddos_mitigator/mitigator.py` — **NEW** (Prometheus-to-nginx sync)
- `/opt/ddos_mitigator/systemd/ddos-mitigator.service` — **NEW** (systemd unit)

### ProxySQL
- `/etc/proxysql/proxysql.cnf` — **NEW** (connection pooling config)
- `/etc/proxysql/mysql_users.cnf` — **NEW** (database credentials)

### System Configuration
- `/etc/sysctl.conf` — Modify: Add TCP SYN cookie, connection limits
- `/etc/security/limits.conf` — Modify: File descriptor limits for nginx/HAProxy

### Certificates & TLS
- `/etc/letsencrypt/live/your-domain.com/` — Auto-generated by certbot
- `/opt/certbot/renewal-hook.sh` — **NEW** (nginx reload on cert renewal)

### Documentation
- `/opt/docs/ARCHITECTURE.md` — Overall design
- `/opt/docs/DEPLOYMENT.md` — Step-by-step deployment guide
- `/opt/docs/INCIDENT_RESPONSE.md` — Attack response runbook
- `/opt/docs/TUNING_GUIDE.md` — Rate limit adjustment procedures

---

## Verification Checklist

### Phase 1 (Foundation)
- [ ] Docker Compose production config supports all services
- [ ] HTTPS certificates generated and auto-renewal configured
- [ ] Test: HTTPS endpoint responds with valid cert

### Phase 2 (L3/L4)
- [ ] nginx responds on ports 80/443, forwards to HAProxy internally
- [ ] HAProxy distributes to 3+ Frappe workers, health checks working
- [ ] SYN cookies enabled, tested with SYN flood simulation
- [ ] Test: Kill one worker → requests route to others

### Phase 3 (L7)
- [ ] Frappe rate limiting middleware initialized
- [ ] Redis counters increment on requests
- [ ] Rate limit violations return 429, not crash
- [ ] Test: Rack 1000 req/sec → limited to 100 req/min, no data loss

### Phase 4 (Monitoring)
- [ ] ELK stack ingesting nginx + HAProxy logs in real-time
- [ ] Kibana dashboards show traffic, response times, error rates
- [ ] Prometheus scraping metrics, rules evaluating
- [ ] Alertmanager sends test alert to Slack
- [ ] Test: Threshold exceeded → alert within 60s

### Phase 5 (Scaling)
- [ ] 5 Frappe workers running, auto-restart on failure
- [ ] Redis Sentinel elected, failover tested
- [ ] ProxySQL pooling database connections, max 100 to MariaDB
- [ ] Test: MariaDB connection exhaustion → ProxySQL handles gracefully

### Phase 6 (Production)
- [ ] Load test: 2000 req/sec for 1 hour → 99.9% success, <5s p99 latency
- [ ] Attack simulation: HTTP flood → auto-mitigated, service stable
- [ ] Audit logs queryable in Kibana, GDPR compliant (IPs anon after 60d)
- [ ] Runbooks published, on-call team trained
- [ ] Go-live scheduled, rollback plan ready

---

## Resource & Timeline Summary

| Phase | Duration | Owner | Dependencies |
|-------|----------|-------|--------------|
| 1. Foundation | 1-2 weeks | Infra Lead, DevOps | None |
| 2. L3/L4 Protection | 1-2 weeks (parallel) | Infra Lead, DevOps | Phase 1 |
| 3. L7 Protection | 1-2 weeks | Senior Dev + Security | Phase 2 |
| 4. Monitoring | 1-2 weeks | Monitoring Spec + DevOps | Phases 1-3 |
| 5. Scaling | 1 week (parallel) | DevOps + DBA | Phases 1-3 |
| 6. Testing & Go-Live | 2 weeks | QA, Security, DevOps | Phases 1-5 |
| **Total** | **6-8 weeks** | **Multi-team** | **Sequential/overlapped** |

---

## Cost & Operational Impact Estimate

**Infrastructure costs (monthly):**
- Additional compute (3 more Gunicorn workers): +$50-100
- ELK stack (Elasticsearch, Logstash, Kibana): +$100-200
- Prometheus + Grafana: +$20-50
- **Total deltaOperatingCost:** ~$170-350/month (self-hosted, shared hardware)
- Alternative: Managed DDoS service (Cloudflare, AWS Shield): +$200-1000/month (not used per "self-hosted" preference)

**Operational overhead:**
- Week 1-8: 2 FTE engineers (dedicated implementation)
- Week 8+: 0.5 FTE for ongoing tuning, monitoring

---

## GDPR & Compliance Alignment

✅ **Encryption in transit:** HTTPS forced (nginx TLS termination)
✅ **Audit logs:** All requests logged, queryable for 90 days
✅ **Data minimization:** IP addresses anonymized after 60 days in logs
✅ **Right to deletion:** Automated purge job for logs >90 days
✅ **Incident response:** Alerts enable fast response to suspicious access
✅ **Documentation:** All controls documented for DPA audits
⚠️ **Third-party services:** If you add Cloudflare/AWS Shield later, require EU DPA compliance

---

## Next Steps for Approval

1. **Confirm timeline:** Can your team commit 2 FTE for weeks 1-8?
2. **Staging environment:** Do you have a production-like staging environment to test?
3. **Domain & DNS:** Do you control the DNS for your CRM domain? (for HTTPS/failover setup)
4. **Funding:** Budget approved for ~$200-400/month infrastructure delta + $10-20k implementation time?

Once approved, I can provide:
- Detailed nginx/HAProxy configuration files (ready to deploy)
- Frappe middleware source code (copy-paste ready)
- ELK/Prometheus setup scripts (Docker Compose templates)
- Attack simulation test procedures (for Phase 6 validation)
- Incident response runbooks (for ops team)
