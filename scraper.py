import os
import time
import requests
import subprocess
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
BASE_URL = "https://thenkiri.com"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")

def setup_directories():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"[*] Created directory: {DOWNLOAD_DIR}")

def get_browser():
    """Configures Chrome to download files automatically to the specified folder."""
    chrome_options = Options()
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False # Disabling helps files finalize faster
    }
    chrome_options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def get_folder_size(directory):
    """Calculates the total size of files in the directory for speed estimation."""
    total_size = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


# --- TELEGRAM CONFIG ---
TELEGRAM_TOKEN = "8339557914:AAHODDY9wkNqM9pRiO4Jm4klH-Mlh27Q3cY"
TELEGRAM_CHAT_ID = 5655050326

def send_telegram_notification(message):
    """Sends a notification to your phone via Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🎬 SayXchange MacBook Update:\n\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[!] Telegram failed: {e}")

# ... (setup_directories, get_browser, get_folder_size remain the same) ...


def wait_for_downloads(directory, timeout=3600):
    """Waits for downloads to finish with speed estimation and audio alerts."""
    print(f"\n[*] Monitoring folder: {directory}")
    seconds = 0
    last_size = get_folder_size(directory)
    
    while seconds < timeout:
        all_files = os.listdir(directory)
        dl_files = [f for f in all_files if f.endswith('.crdownload') or f.endswith('.part') or f.startswith('.com.google.Chrome')]
        
        if not dl_files and any(not f.startswith('.') for f in all_files):
            print("\n\n" + "="*40)
            print("[*] ALL DOWNLOADS COMPLETE AND FINALIZED!")
            print("="*40)
            os.system('afplay /System/Library/Sounds/Glass.aiff') 
            os.system('say "Your movies are ready"') 
            subprocess.run(['open', directory]) 
            return True
        
        current_size = get_folder_size(directory)
        speed_mb = ((current_size - last_size) / (1024 * 1024)) / 5 
        print(f"\r    [PROGRESS] {len(dl_files)} files active | Speed: {max(0, speed_mb):.2f} MB/s | Elapsed: {seconds}s    ", end="", flush=True)
        
        last_size = current_size
        time.sleep(5)
        seconds += 5
    return False

def search_thenkiri(query):
    search_url = f"{BASE_URL}/?s={query.replace(' ', '+')}"
    print(f"[*] Searching for '{query}'...")
    try:
        response = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for article in soup.find_all('article'):
            title_tag = article.find('h2', class_='entry-title')
            if title_tag and title_tag.a:
                results.append({'title': title_tag.a.text.strip(), 'url': title_tag.a['href']})
        return results
    except Exception as e:
        print(f"[!] Search error: {e}")
        return []

def extract_all_episode_links(post_url):
    try:
        response = requests.get(post_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if "downloadwella.com" in a['href']]
        return list(dict.fromkeys(links))
    except Exception as e:
        print(f"[!] Extraction error: {e}")
        return []

def automate_bulk_download(link_list):
    if not link_list:
        print("[!] No download links found.")
        return

    driver = get_browser()
    
    try:
        for i, file_url in enumerate(link_list):
            attempts = 0
            success = False
            
            while attempts < 3 and not success:
                attempts += 1
                print(f"\n[Queue {i+1}/{len(link_list)}] Attempt {attempts}/3: {file_url}")
                driver.get(file_url)
                
                try:
                    # --- PHASE 1: FREE BUTTON ---
                    time.sleep(3)
                    driver.execute_script('var b = document.querySelector("input[name=\'method_free\']") || document.querySelector("#method_free"); if(b) b.click();')

                    # --- PHASE 2: TIMER ---
                    for _ in tqdm(range(35), desc="      Waiting", unit="s", leave=False):
                        time.sleep(1)

                    # --- PHASE 3: CREATE LINK ---
                    driver.execute_script("document.getElementById('downloadbtn').click();")
                    
                    # --- PHASE 4: FINAL TRIGGER ---
                    time.sleep(5) 
                    final_script = """
                    var links = document.querySelectorAll('a');
                    for (var i = 0; i < links.length; i++) {
                        if (links[i].href.includes('.mkv') || links[i].innerText.includes('Click here to download')) {
                            links[i].click();
                            return true;
                        }
                    }
                    return false;
                    """
                    if driver.execute_script(final_script):
                        print("    > SUCCESS: Final download triggered!")
                        success = True
                        time.sleep(10) # Wait for download to register in folder
                    else:
                        raise Exception("Final download button not found.")

                except Exception as e:
                    print(f"    [!] Attempt {attempts} failed: {e}")
                    if attempts < 3:
                        print("    [!] Refreshing and retrying...")
                    else:
                        print("    [!] Skipping to next item in queue.")

        # Wait for all files to finish
        wait_for_downloads(DOWNLOAD_DIR)

    finally:
        print("\n[*] Script finishing. Closing browser.")
        driver.quit()

def main():
    setup_directories()
    while True:
        query = input("\nSearch movie/show (or 'q' to quit): ").strip()
        if query.lower() == 'q': break
        
        results = search_thenkiri(query)
        if not results:
            print("[!] No results found.")
            continue
            
        print(f"\n--- Results for '{query}' ---")
        for idx, item in enumerate(results):
            print(f"{idx + 1}. {item['title']}")
            
        choice = input("\nEnter numbers (e.g., 1, 2) or 'all' (or 'c' to cancel): ").strip()
        if choice.lower() == 'c': continue

        selected_indices = []
        if choice.lower() == 'all':
            selected_indices = list(range(len(results)))
        else:
            try:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
            except ValueError:
                print("[!] Invalid input format.")
                continue

        master_queue = []
        for idx in selected_indices:
            if 0 <= idx < len(results):
                print(f"[*] Gathering links from: {results[idx]['title']}")
                links = extract_all_episode_links(results[idx]['url'])
                master_queue.extend(links)
            else:
                print(f"[!] Selection {idx + 1} is out of range.")

        if master_queue:
            master_queue = list(dict.fromkeys(master_queue))
            automate_bulk_download(master_queue)
        else:
            print("[!] No links found.")

if __name__ == "__main__":
    main()