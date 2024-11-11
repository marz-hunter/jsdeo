import os
import argparse
import subprocess
import threading
import random
import socket

def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed: {command}")
    return result.returncode == 0

def set_proxy(proxy):
    if proxy:
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy
        print(f"Proxy set to {proxy}")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def get_random_port():
    while True:
        port = random.randint(8000, 9000)
        if not is_port_in_use(port):
            return port

def process_domain(domain, proxy):
    print(f"Processing domain: {domain}")
    
    # 1. Set proxy jika diperlukan
    set_proxy(proxy)
    
    # 2. Buat direktori untuk domain
    current_dir = subprocess.getoutput('pwd').strip()
    domain_dir = os.path.join(current_dir, domain)
    os.makedirs(domain_dir, exist_ok=True)
    
    # 3. Jalankan waymore
    waymore_cmd = f"waymore -i {domain} -ko '\.js(\?|$)' -mode U -oU {domain_dir}/waymore.txt"
    run_command(waymore_cmd)
    
    # 4. Parse file waymore.txt untuk menemukan URL .js
    js_cmd = f"cat {domain_dir}/waymore.txt | grep -Eo 'https?://[^ /]+(:[0-9]+)?/[^ ]*\\.js([?][^ ]*)?' | tee {domain_dir}/js.txt"
    run_command(js_cmd)
    
    # 5. Jalankan uro dan httpx
    uro_cmd = f"uro -i {domain_dir}/js.txt -o {domain_dir}/urojs.txt"
    run_command(uro_cmd)
    
    httpx_cmd = f"httpx -l {domain_dir}/urojs.txt -mc 200 -nc -o {domain_dir}/urohttpx.txt"
    run_command(httpx_cmd)
    
    # 6. Jalankan script cekjs.py
    cekjs_cmd = f"python3 cjs.py -f {domain_dir}/urohttpx.txt -t 10"
    run_command(cekjs_cmd, cwd=domain_dir)
    
    LinkFinderhtml_cmd= f"python3 linkfinder.py -i '{domain_dir}/jsdeobfuscator/*.js' -o {domain_dir}/linkfinder.html"
    run_command(LinkFinderhtml_cmd)

    LinkFindercli_cmd= f"python3 linkfinder.py -i '{domain_dir}/jsdeobfuscator/*.js' -o cli | tee {domain_dir}/linkfinder.txt"
    run_command(LinkFindercli_cmd)
    
    # 8. Pilih port acak untuk HTTP server
    port = get_random_port()
    print(f"Starting HTTP server on port {port}")
    
    server_thread = threading.Thread(target=run_command, args=(f"python3 -m http.server {port} --bind 127.0.0.1", f"{domain_dir}/jsdeobfuscator"))
    server_thread.start()
    
    # 9. Buka shell baru dan jalankan katana dengan port yang dipilih
    katana_cmd = f"katana -u http://127.0.0.1:{port}/ -jc -d 19 -o {domain_dir}/katana -proxy http://127.0.0.1:8082"
    run_command(katana_cmd, cwd=domain_dir)


    # 10. Stop HTTP server setelah katana selesai
    killhttpserver_cmd = f"kill -9 $(pgrep -f 'python3 -m http.server')"
    run_command(killhttpserver_cmd)

     # 11. Jalankan perintah untuk menyimpan output dari katana
    katana_no_js_cmd = f"cat {domain_dir}/katana | grep -v 'deobfuscated.js' | tee {domain_dir}/katananojs"
    run_command(katana_no_js_cmd, cwd=domain_dir)

def main():
    parser = argparse.ArgumentParser(description="Automated workflow script.")
    parser.add_argument('-d', '--domain', help="Single domain to process")
    parser.add_argument('-l', '--list', help="File with list of domains to process")
    parser.add_argument('-proxy', '--proxy', help="Set proxy (e.g., http://127.0.0.1:8080)", default=None)
    
    args = parser.parse_args()
    
    if args.domain:
        process_domain(args.domain, args.proxy)
    
    elif args.list:
        with open(args.list, 'r') as f:
            domains = [line.strip() for line in f]
        for domain in domains:
            process_domain(domain, args.proxy)

if __name__ == "__main__":
    main()
