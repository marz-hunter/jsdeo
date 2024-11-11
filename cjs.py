import os
import re
import requests
import threading
import argparse
from urllib.parse import quote
import subprocess
import string

def is_obfuscated(js_content):
    obfuscation_pattern = re.compile(
        r'('
        r'eval\((?!\s*function)'  
        r'|Function\(\s*[\'"]'    
        r'|obfuscator'            
        r'|while\s*\(true\)\s*{'  
        r'|!function\(\)\s*{'     
        r'|function\(p,a,c,k,e,d\)'  
        r'|setTimeout\(.*?0x'     
        r'|\\x[0-9A-Fa-f]{2}'     
        r'|\\u[0-9A-Fa-f]{4}'     
        r'|Array\(\s*\d+\s*\)\.join'  
        r'|atob\('                
        r'|fromCharCode'          
        r'|charCodeAt'            
        r'|document\['            
        r'|window\[.*?\]'         
        r')', re.IGNORECASE | re.DOTALL
    )
    return bool(obfuscation_pattern.search(js_content))

def sanitize_filename(filename):
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    sanitized = ''.join(c if c in valid_chars else '_' for c in filename)
    return sanitized

def download_and_process_js(url, proxy):
    try:
        print(f"Processing: {url}")
        # Encode URL path sepenuhnya, termasuk "/"
        encoded_url = quote(url, safe='')

        # Sanitize the encoded URL for the output filename
        sanitized_encoded_url = sanitize_filename(encoded_url)

        # Buat path folder untuk menyimpan file JS
        folder = "obfuscateJS"
        full_path = os.path.join(folder, f"{sanitized_encoded_url}.OBFUSCATED.js")

        # Buat folder jika belum ada
        os.makedirs(folder, exist_ok=True)

        # Setup proxy jika diperlukan
        proxies = {"http": proxy, "https": proxy} if proxy else None

        # Download file JS
        response = requests.get(url, proxies=proxies, verify=False)
        response.raise_for_status()

        # Check if JS is obfuscated
        if is_obfuscated(response.text):

            obfuscated_js_path = full_path
            with open(obfuscated_js_path, 'w', encoding='utf-8') as js_file:
                js_file.write(response.text)

            print(f"Downloaded obfuscated JS: {obfuscated_js_path}")


            deobfuscator_folder = "jsdeobfuscator"
            os.makedirs(deobfuscator_folder, exist_ok=True)


            deobfuscated_js_path = os.path.join(deobfuscator_folder, f"{sanitized_encoded_url}_deobfuscated.js")


            print(f"js-deobfuscator -i {obfuscated_js_path} -o {deobfuscated_js_path}")


            result = subprocess.run(
                ["js-deobfuscator", "-i", obfuscated_js_path, "-o", deobfuscated_js_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )


            if result.returncode != 0:
                print(f"Error during deobfuscation: {result.stderr}")
            else:
                print(f"Deobfuscated JS saved as: {deobfuscated_js_path}")
        else:
            print(f"JS file at {url} is not obfuscated.")
    
    except requests.exceptions.RequestException as e:
        print(f"Error processing {url}: {e}")


def process_js_list(file_path, threads, proxy):
    with open(file_path, 'r') as f:
        urls = f.read().splitlines()


    thread_list = []
    for url in urls:
        thread = threading.Thread(target=download_and_process_js, args=(url, proxy))
        thread_list.append(thread)
        thread.start()


        if len(thread_list) >= threads:
            for t in thread_list:
                t.join()
            thread_list = []


    for t in thread_list:
        t.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto JS Obfuscation Checker and Downloader")
    parser.add_argument("-f", "--file", required=True, help="Path to file containing JS URLs")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads to use")
    parser.add_argument("-proxy", "--proxy", help="Proxy to use (format: http://127.0.0.1:8080)")
    args = parser.parse_args()

    process_js_list(args.file, args.threads, args.proxy)
