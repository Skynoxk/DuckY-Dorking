import subprocess
import sys
import json
import time
import re
import urllib.parse
from pathlib import Path

def run_universal_google_dork(dork_query: str, max_pages: int = 999) -> list:
    output_dir = Path("./dork_results")
    output_dir.mkdir(exist_ok=True)
    
    safe_name = "".join([c if c.isalnum() else "_" for c in dork_query]).strip("_")[:50]
    json_path = output_dir / f"{safe_name}_results.json"

    print(f"[*] Starting Universal Dork: {dork_query}")
    print(f"[*] Max pages: {max_pages}")
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    evasion_args = "--args '--disable-blink-features=AutomationControlled,--no-sandbox'"
    session_name = "googledork_session"
    base_cmd = f"agent-browser --session-name {session_name} --user-agent \"{user_agent}\" {evasion_args}"

    # Step 1: Initial Search
    print("[*] Navigating to Google...")
    subprocess.run("agent-browser close", shell=True, capture_output=True)
    subprocess.run(f"{base_cmd} set viewport 1920 1080", shell=True, capture_output=True)
    
    encoded_query = urllib.parse.quote(dork_query)
    search_url = f"https://www.google.com/search?q={encoded_query}&hl=en&num=100"
    
    subprocess.run(f"{base_cmd} open \"{search_url}\"", shell=True, capture_output=True)
    subprocess.run(f"{base_cmd} wait --load networkidle", shell=True, capture_output=True)
    time.sleep(3)

    all_results = []
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    page = 1
    while page <= max_pages:
        print(f"[*] Extracting Page {page}...")
        
        # Take screenshot
        screenshot_path = output_dir / f"{safe_name}_page_{page}.png"
        subprocess.run(f"{base_cmd} screenshot \"{screenshot_path}\"", shell=True, capture_output=True)

        extract_js = r"""
        (() => {
            const results = [];
            // Broad search for anything that looks like a result link
            document.querySelectorAll('a').forEach(a => {
                const href = a.href;
                if (href && href.startsWith('http')) {
                    const isInternal = /(google\.com|gstatic\.com|youtube\.com|googleadservices\.com|google\.co\.th)/i.test(href);
                    const h3 = a.querySelector('h3') || a.closest('div')?.querySelector('h3');
                    const title = h3 ? h3.innerText.trim() : a.innerText.trim();
                    
                    if (title && !isInternal && title.length > 5 && !results.some(r => r.url === href)) {
                        results.push({title: title.replace(/\n/g, ' '), url: href});
                    }
                }
            });
            return results;
        })()
        """
        
        eval_args = ["agent-browser", "--session-name", session_name, "eval", extract_js]
        result = subprocess.run(eval_args, capture_output=True, text=True)
        
        try:
            raw_output = result.stdout.strip()
            clean_output = ansi_escape.sub('', raw_output)
            
            if "[" in clean_output and "]" in clean_output:
                json_str = clean_output[clean_output.find("["):clean_output.rfind("]")+1]
                page_items = json.loads(json_str)
                all_results.extend(page_items)
                print(f"[+] Successfully extracted {len(page_items)} links from page {page}.")
                
                if not page_items:
                    # Check for CAPTCHA
                    check_text = subprocess.run(f"{base_cmd} get text \"body\"", shell=True, capture_output=True, text=True).stdout
                    if "unusual traffic" in check_text or "not a robot" in check_text:
                        print("[!] CAPTCHA detected. Please solve it manually or try again later.")
                        break
                    else:
                        print("[*] No more results found.")
                        break
            else:
                print(f"[*] End of results or unexpected layout on page {page}.")
                break
                
        except Exception as e:
            print(f"[-] Error on page {page}: {e}")
            break

        # Pagination
        print(f"[*] Clicking 'Next' for Page {page+1}...")
        subprocess.run(f"{base_cmd} scroll down 2000", shell=True, capture_output=True)
        time.sleep(1)
        
        next_selectors = ["a#pnnext", "a:has-text('Next')", "a[aria-label='Next page']"]
        success = False
        for selector in next_selectors:
            next_run = subprocess.run(f"{base_cmd} click \"{selector}\"", shell=True, capture_output=True)
            if next_run.returncode == 0:
                success = True
                break
        
        if not success:
            print("[*] No more pages.")
            break
        
        time.sleep(4)
        page += 1

    # Save Results
    if all_results:
        unique_all = []
        seen_urls = set()
        for item in all_results:
            if item['url'] not in seen_urls:
                unique_all.append(item)
                seen_urls.add(item['url'])
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(unique_all, f, indent=4, ensure_ascii=False)
        print(f"\n[+] TOTAL UNIQUE RESULTS: {len(unique_all)}")
        print(f"[+] Data saved to: {json_path}")
    else:
        print("\n[-] No results found.")

    return all_results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python googledork.py \"<query>\" [max_pages]")
        sys.exit(1)
    
    query_str = sys.argv[1]
    pages_count = int(sys.argv[2]) if len(sys.argv) > 2 else 999
    
    try:
        run_universal_google_dork(query_str, pages_count)
    finally:
        subprocess.run("agent-browser close", shell=True, capture_output=True)
