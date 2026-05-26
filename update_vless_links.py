#!/usr/bin/env python3
import requests
import re
import subprocess
import time
import os
import json
import tempfile
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_url_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        if len(response.content) > 1 * 1024 * 1024:  # 1 MB limit
            print(f"Skipping large URL content from {url}")
            return None
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_vless_links(content):
    if not content:
        return []
    return re.findall(r'vless://[^\n\r\s]+', content)

def parse_vless_link(link):
    """Parse VLESS link into components for xray config"""
    try:
        # vless://UUID@HOST:PORT?params#remark
        match = re.match(r'vless://([^@]+)@([^:]+):(\d+)\??([^#]*)#?(.*)', link)
        if not match:
            return None
        
        uuid, host, port, params_str, remark = match.groups()
        params = urllib.parse.parse_qs(params_str)
        
        # Extract parameters
        config = {
            'uuid': uuid,
            'address': host,
            'port': int(port),
            'type': params.get('type', ['tcp'])[0],
            'security': params.get('security', ['none'])[0],
            'encryption': params.get('encryption', ['none'])[0],
            'flow': params.get('flow', [''])[0],
            'sni': params.get('sni', [''])[0],
            'fp': params.get('fp', [''])[0],
            'pbk': params.get('pbk', [''])[0],
            'sid': params.get('sid', [''])[0],
            'path': params.get('path', [''])[0],
            'host_header': params.get('host', [''])[0],
            'alpn': params.get('alpn', [''])[0],
            'remark': urllib.parse.unquote(remark) if remark else host
        }
        return config
    except Exception as e:
        print(f"Error parsing VLESS link: {e}")
        return None

def create_xray_config(vless_config, socks_port):
    """Create xray config for testing a VLESS link"""
    outbound = {
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": vless_config['address'],
                "port": vless_config['port'],
                "users": [{
                    "id": vless_config['uuid'],
                    "encryption": vless_config['encryption']
                }]
            }]
        },
        "streamSettings": {
            "network": vless_config['type']
        }
    }
    
    # Add flow if present
    if vless_config['flow']:
        outbound['settings']['vnext'][0]['users'][0]['flow'] = vless_config['flow']
    
    # Configure security
    if vless_config['security'] == 'tls':
        outbound['streamSettings']['security'] = 'tls'
        outbound['streamSettings']['tlsSettings'] = {}
        if vless_config['sni']:
            outbound['streamSettings']['tlsSettings']['serverName'] = vless_config['sni']
        if vless_config['alpn']:
            outbound['streamSettings']['tlsSettings']['alpn'] = vless_config['alpn'].split(',')
        if vless_config['fp']:
            outbound['streamSettings']['tlsSettings']['fingerprint'] = vless_config['fp']
    elif vless_config['security'] == 'reality':
        outbound['streamSettings']['security'] = 'reality'
        outbound['streamSettings']['realitySettings'] = {}
        if vless_config['sni']:
            outbound['streamSettings']['realitySettings']['serverName'] = vless_config['sni']
        if vless_config['pbk']:
            outbound['streamSettings']['realitySettings']['publicKey'] = vless_config['pbk']
        if vless_config['sid']:
            outbound['streamSettings']['realitySettings']['shortId'] = vless_config['sid']
        if vless_config['fp']:
            outbound['streamSettings']['realitySettings']['fingerprint'] = vless_config['fp']
    
    # Configure transport
    if vless_config['type'] == 'ws':
        outbound['streamSettings']['wsSettings'] = {}
        if vless_config['path']:
            outbound['streamSettings']['wsSettings']['path'] = vless_config['path']
        if vless_config['host_header']:
            outbound['streamSettings']['wsSettings']['headers'] = {'Host': vless_config['host_header']}
    elif vless_config['type'] == 'grpc':
        outbound['streamSettings']['grpcSettings'] = {}
        if vless_config['path']:
            outbound['streamSettings']['grpcSettings']['serviceName'] = vless_config['path']
    
    config = {
        "log": {"loglevel": "error"},
        "inbounds": [{
            "port": socks_port,
            "protocol": "socks",
            "settings": {"udp": False}
        }],
        "outbounds": [outbound]
    }
    
    return config

def test_vless_link(link, timeout=10):
    """Test a VLESS link using xray and measure response time"""
    vless_config = parse_vless_link(link)
    if not vless_config:
        return link, float('inf'), "Parse failed"
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        socks_port = 10808  # Use a fixed port for simplicity
        config = create_xray_config(vless_config, socks_port)
        json.dump(config, f)
        config_path = f.name
    
    xray_process = None
    try:
        # Start xray
        xray_process = subprocess.Popen(
            ['/usr/local/bin/xray', 'run', '-config', config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait a bit for xray to start
        time.sleep(0.5)
        
        # Test connection through SOCKS proxy
        start_time = time.time()
        try:
            response = requests.get(
                'http://www.gstatic.com/generate_204',
                proxies={'http': f'socks5://127.0.0.1:{socks_port}'},
                timeout=timeout
            )
            end_time = time.time()
            
            if response.status_code == 204:
                latency_ms = (end_time - start_time) * 1000
                return link, latency_ms, "OK"
            else:
                return link, float('inf'), f"HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return link, float('inf'), f"Connection failed: {str(e)[:50]}"
    
    except Exception as e:
        return link, float('inf'), f"Test error: {str(e)[:50]}"
    
    finally:
        # Clean up
        if xray_process:
            xray_process.terminate()
            try:
                xray_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                xray_process.kill()
        
        try:
            os.unlink(config_path)
        except:
            pass

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    urls_file_path = os.path.join(script_dir, "subscription_urls.txt")
    output_file_path = os.path.join(script_dir, "vless_top20.txt")

    if not os.path.exists(urls_file_path):
        print(f"Error: {urls_file_path} not found.")
        return

    with open(urls_file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    all_vless_links = []
    for url in urls:
        print(f"Processing URL: {url}")
        content = get_url_content(url)
        if content:
            vless_links = extract_vless_links(content)
            all_vless_links.extend(vless_links)
            print(f"  Found {len(vless_links)} VLESS links")
        else:
            print(f"  No content or error for {url}")

    if not all_vless_links:
        print("No VLESS links found.")
        return

    # Remove duplicates
    all_vless_links = list(set(all_vless_links))
    print(f"\nTotal unique VLESS links: {len(all_vless_links)}")
    print("Testing links with xray (this may take a while)...\n")

    # Test links in parallel (but not too many at once)
    working_links = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_vless_link, link): link for link in all_vless_links}
        
        for i, future in enumerate(as_completed(futures), 1):
            link, latency, status = future.result()
            if latency != float('inf'):
                working_links.append((link, latency))
                print(f"[{i}/{len(all_vless_links)}] ✓ {latency:.0f}ms - {status}")
            else:
                print(f"[{i}/{len(all_vless_links)}] ✗ {status}")

    if not working_links:
        print("\nNo working VLESS links found after testing.")
        return

    # Sort by latency
    working_links.sort(key=lambda x: x[1])
    top_20_vless_links = working_links[:20]

    print(f"\n{'='*80}")
    print(f"Top {len(top_20_vless_links)} working VLESS links (sorted by latency):")
    print(f"{'='*80}\n")
    
    for i, (link, latency) in enumerate(top_20_vless_links, 1):
        print(f"{i:2d}. {latency:6.0f}ms - {link[:80]}...")

    # Save to file
    with open(output_file_path, 'w') as f:
        for link, _ in top_20_vless_links:
            f.write(link + '\n')
    
    print(f"\n✓ Top {len(top_20_vless_links)} VLESS links saved to {output_file_path}")

if __name__ == "__main__":
    main()
