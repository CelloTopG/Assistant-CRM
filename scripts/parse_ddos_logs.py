#!/usr/bin/env python3
"""
Parse Frappe logs for DDoS violations and generate summary report
Usage: python parse_ddos_logs.py [logfile] [--from-time HH:MM] [--to-time HH:MM]

Examples:
  python parse_ddos_logs.py /path/to/bench.log
  python parse_ddos_logs.py --from-time 14:00 --to-time 16:00
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from collections import Counter, defaultdict

def parse_logs(logfile, from_time=None, to_time=None):
    """Extract and analyze DDoS violations from Frappe logs"""
    violations = {
        "rate_limit_exceeded": [],
        "bot_detected": [],
    }
    ips = Counter()
    users = Counter()
    endpoints = Counter()
    violation_types = Counter()
    hourly_violations = defaultdict(int)
    
    try:
        with open(logfile, 'r') as f:
            for line in f:
                if "DDOS_VIOLATION" in line:
                    try:
                        # Extract JSON from log line
                        json_start = line.find('{')
                        json_end = line.rfind('}') + 1
                        json_str = line[json_start:json_end]
                        entry = json.loads(json_str)
                        
                        timestamp = entry.get("timestamp", "")
                        violation_type = entry.get("violation_type", "unknown")
                        
                        # Filter by time range if specified
                        if from_time or to_time:
                            try:
                                entry_time = datetime.fromisoformat(timestamp).time()
                                if from_time and entry_time < from_time:
                                    continue
                                if to_time and entry_time > to_time:
                                    continue
                            except:
                                pass
                        
                        violations[violation_type].append(entry)
                        ips[entry.get("ip", "unknown")] += 1
                        users[entry.get("user", "anonymous")] += 1
                        endpoints[entry.get("path", "unknown")] += 1
                        violation_types[violation_type] += 1
                        
                        # Track hourly distribution
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            hour_key = dt.strftime("%H:00")
                            hourly_violations[hour_key] += 1
                        except:
                            pass
                            
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        print(f"Error: Log file '{logfile}' not found")
        sys.exit(1)
    
    return violations, ips, users, endpoints, violation_types, hourly_violations


def print_report(violations, ips, users, endpoints, violation_types, hourly_violations):
    """Print summary report"""
    total_violations = sum(len(v) for v in violations.values())
    
    print("\n" + "="*80)
    print("ASSISTANT CRM DDoS PROTECTION REPORT")
    print("="*80)
    
    print(f"\n📊 SUMMARY")
    print(f"  Total Violations: {total_violations}")
    print(f"  Rate Limit: {len(violations['rate_limit_exceeded'])}")
    print(f"  Bot Detected: {len(violations['bot_detected'])}")
    print(f"  Unique IPs: {len(ips)}")
    print(f"  Unique Users: {len(users)}")
    print(f"  Targeted Endpoints: {len(endpoints)}")
    
    if violation_types:
        print(f"\n📈 VIOLATION BREAKDOWN")
        for vtype, count in violation_types.most_common():
            print(f"  {vtype}: {count}")
    
    if hourly_violations:
        print(f"\n⏱️  HOURLY DISTRIBUTION")
        for hour in sorted(hourly_violations.keys()):
            count = hourly_violations[hour]
            bar = "█" * min(count // 5, 40)
            print(f"  {hour}: {count:4d} {bar}")
    
    if ips:
        print(f"\n🚨 TOP ATTACKING IPs (Top 15)")
        for i, (ip, count) in enumerate(ips.most_common(15), 1):
            print(f"  {i:2d}. {ip:20s} {count:5d} violations")
    
    if endpoints:
        print(f"\n🎯 MOST TARGETED ENDPOINTS (Top 10)")
        for i, (endpoint, count) in enumerate(endpoints.most_common(10), 1):
            print(f"  {i:2d}. {endpoint:50s} {count:4d} hits")
    
    if users:
        print(f"\n👤 AFFECTED USERS (Top 10)")
        for i, (user, count) in enumerate(users.most_common(10), 1):
            print(f"  {i:2d}. {user:30s} {count:4d} violations")
    
    # Recent violations
    all_violations = []
    for v_list in violations.values():
        all_violations.extend(v_list)
    
    if all_violations:
        print(f"\n📝 RECENT VIOLATIONS (Last 10)")
        sorted_violations = sorted(all_violations, key=lambda x: x.get("timestamp", ""), reverse=True)
        for i, v in enumerate(sorted_violations[:10], 1):
            ts = v.get("timestamp", "N/A")
            vtype = v.get("violation_type", "unknown")
            ip = v.get("ip", "N/A")
            path = v.get("path", "N/A")
            user = v.get("user", "anonymous")
            print(f"  {i:2d}. [{ts}] {vtype:20s} IP:{ip:15s} User:{user:15s} Path:{path}")
    
    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Parse Frappe logs for DDoS violations and generate report"
    )
    parser.add_argument(
        "logfile",
        nargs="?",
        default="/workspace/development/frappe-bench/logs/bench.log",
        help="Path to Frappe bench.log file (default: {default})"
    )
    parser.add_argument(
        "--from-time",
        type=lambda s: datetime.strptime(s, "%H:%M").time(),
        help="Filter violations from this time (HH:MM format)"
    )
    parser.add_argument(
        "--to-time",
        type=lambda s: datetime.strptime(s, "%H:%M").time(),
        help="Filter violations until this time (HH:MM format)"
    )
    
    args = parser.parse_args()
    
    violations, ips, users, endpoints, violation_types, hourly_violations = parse_logs(
        args.logfile,
        from_time=args.from_time,
        to_time=args.to_time
    )
    
    print_report(violations, ips, users, endpoints, violation_types, hourly_violations)


if __name__ == "__main__":
    main()
