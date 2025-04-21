import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import customtkinter as ctk
from tkinter import messagebox

def clean_price(price):
    cleaned = re.sub(r'[^\d.]', '', price)
    try:
        return float(cleaned)
    except ValueError:
        return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.HTTPError)
)
def find_retro_deals(search_term, max_results=5, sort_by="price"):
    url = f"https://www.ebay.com/sch/i.html?_nkw={search_term.replace(' ', '+')}&_sacat=0"
    
    if sort_by == "price":
        url += "&_sop=15"
    elif sort_by == "new":
        url += "&_sop=10"
    else:
        url += "&_sop=12"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.ebay.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {search_term}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.find_all("div", class_="s-item__info")[:max_results]
    deals = []

    for item in items:
        title_elem = item.find("div", class_="s-item__title")
        price_elem = item.find("span", class_="s-item__price")
        condition_elem = item.find("span", class_="SECONDARY_INFO")
        link_elem = item.find("a", class_="s-item__link")

        title = title_elem.text.strip() if title_elem else "N/A"
        price = clean_price(price_elem.text) if price_elem else None
        condition = condition_elem.text.strip() if condition_elem else "N/A"
        link = link_elem["href"] if link_elem else "N/A"

        if price and title != "N/A":
            deals.append({
                "title": title,
                "price": price,
                "condition": condition,
                "link": link,
                "source": "eBay"
            })

    return deals

class RetroDealsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Retro Deals Finder")
        self.root.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.search_categories = {
            "Gaming": ["nintendo nes games", "sega genesis games", "gameboy games", "super nintendo snes"],
            "Consoles": ["vintage console", "nintendo nes console", "sega genesis console", "atari 2600"],
            "Collectibles": ["retro toys", "vintage comics", "retro action figures", "vintage trading cards"],
            "Other": ["retro electronics", "vintage vinyl records", "retro clothing", "vintage posters"]
        }

        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.search_button = ctk.CTkButton(self.main_frame, text="Search for Deals", command=self.start_search)
        self.search_button.pack(pady=10)

        self.progress_label = ctk.CTkLabel(self.main_frame, text="Ready to search", font=("Arial", 12))
        self.progress_label.pack(pady=5)

        self.tab_view = ctk.CTkTabview(self.main_frame)
        self.tab_view.pack(pady=10, fill="both", expand=True)

        self.tab_frames = {}
        for category in self.search_categories:
            self.tab_view.add(category)
            tab_frame = ctk.CTkScrollableFrame(self.tab_view.tab(category))
            tab_frame.pack(fill="both", expand=True)
            self.tab_frames[category] = tab_frame

    def start_search(self):
        self.search_button.configure(state="disabled")
        self.progress_label.configure(text="Searching...")

        for category, frame in self.tab_frames.items():
            for widget in frame.winfo_children():
                widget.destroy()

        self.root.after(100, self.run_search)

    def run_search(self):
        max_results = 5
        sort_by = "price"
        all_deals = {}

        for category, terms in self.search_categories.items():
            all_deals[category] = []
            for term in terms:
                self.progress_label.configure(text=f"Searching {category}: {term}")
                self.root.update()
                deals = find_retro_deals(term, max_results, sort_by)
                all_deals[category].extend(deals)
                time.sleep(random.uniform(2, 5))  

        # Display results
        for category, deals in all_deals.items():
            frame = self.tab_frames[category]
            if not deals:
                label = ctk.CTkLabel(frame, text="No deals found.", font=("Arial", 12))
                label.pack(pady=10)
                continue

            deals.sort(key=lambda x: x["price"])  
            for i, deal in enumerate(deals[:max_results], 1):
                deal_frame = ctk.CTkFrame(frame, corner_radius=5)
                deal_frame.pack(pady=5, padx=5, fill="x")

                title_label = ctk.CTkLabel(deal_frame, text=f"{deal['title'][:60]}...", font=("Arial", 12, "bold"))
                title_label.pack(anchor="w", padx=5)

                price_label = ctk.CTkLabel(deal_frame, text=f"Price: ${deal['price']:.2f}", font=("Arial", 12))
                price_label.pack(anchor="w", padx=5)

                condition_label = ctk.CTkLabel(deal_frame, text=f"Condition: {deal['condition']}", font=("Arial", 12))
                condition_label.pack(anchor="w", padx=5)

                link_label = ctk.CTkLabel(deal_frame, text="Link: Click to visit", font=("Arial", 12), text_color="blue", cursor="hand2")
                link_label.pack(anchor="w", padx=5)
                link_label.bind("<Button-1>", lambda e, link=deal["link"]: self.open_link(link))

        self.progress_label.configure(text=f"Search completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.search_button.configure(state="normal")

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)

def main():
    root = ctk.CTk()
    app = RetroDealsApp(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")