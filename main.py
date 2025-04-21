import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import random
import threading
import sqlite3
import pandas as pd
import customtkinter as ctk
from tkinter import messagebox, filedialog

def init_db():
    conn = sqlite3.connect("retro_vault.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY, title TEXT, price REAL, condition TEXT, link TEXT,
                  source TEXT, category TEXT, search_term TEXT, timestamp TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS favorites
                 (id INTEGER PRIMARY KEY, title TEXT, price REAL, condition TEXT, link TEXT,
                  source TEXT, category TEXT, timestamp TEXT, description TEXT)''')
    conn.commit()
    conn.close()

def clean_price(price):
    cleaned = re.sub(r'[^\d.]', '', price)
    try:
        return float(cleaned)
    except ValueError:
        return None

def find_ebay_items(search_term, max_results=5, sort_by="price", min_price=None, max_price=None):
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
    results = []

    for item in items:
        title_elem = item.find("div", class_="s-item__title")
        price_elem = item.find("span", class_="s-item__price")
        condition_elem = item.find("span", class_="SECONDARY_INFO")
        link_elem = item.find("a", class_="s-item__link")

        title = title_elem.text.strip() if title_elem else "N/A"
        price = clean_price(price_elem.text) if price_elem else None
        condition = condition_elem.text.strip() if condition_elem else "N/A"
        link = link_elem["href"] if link_elem else "N/A"
        description = "No description available"

        if price and title != "N/A":
            if (min_price is None or price >= min_price) and (max_price is None or price <= max_price):
                results.append({
                    "title": title,
                    "price": price,
                    "condition": condition,
                    "link": link,
                    "source": "eBay",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "description": description
                })

    return results

def find_etsy_items(search_term, max_results=5, sort_by="price", min_price=None, max_price=None):
    return []

class RetroVaultApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RetroVault")
        self.root.geometry("1000x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Font
        self.font = ("Roboto", 12)
        self.bold_font = ("Roboto", 12, "bold")

        self.search_categories = {
            "Gaming": ["nintendo nes games", "sega genesis games", "gameboy games", "super nintendo snes", "playstation 1 games"],
            "Consoles": ["nintendo nes console", "sega genesis console", "atari 2600", "gameboy color", "super nintendo console"],
            "Collectibles": ["retro action figures", "vintage comics", "retro toys", "vintage trading cards", "retro lunchboxes"],
            "Vinyl": ["vintage vinyl records", "retro vinyl singles", "classic rock vinyl", "80s vinyl records"],
            "Retro Tech": ["vintage walkman", "retro electronics", "vintage calculators", "old polaroid cameras"],
            "Retro Fashion": ["80s clothing", "vintage t-shirts", "retro sunglasses", "vintage sneakers"],
            "VHS Tapes": ["vhs movies", "retro vhs tapes", "80s vhs", "vintage vhs horror"],
            "Retro Art": ["retro posters", "vintage album art", "80s neon art", "retro movie posters"]
        }
        self.all_search_terms = [term for terms in self.search_categories.values() for term in terms]

        self.main_frame = ctk.CTkFrame(self.root, fg_color="#121212")
        self.main_frame.pack(fill="both", expand=True)

        self.sidebar = ctk.CTkFrame(self.main_frame, fg_color="#1E1E1E", width=250)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="RetroVault", font=("Roboto", 18, "bold"), text_color="#26A69A").pack(pady=10)

        self.search_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Search retro items (e.g., NES)", font=self.font, fg_color="#2D2D2D", text_color="#FFFFFF", border_color="#26A69A")
        self.search_entry.pack(pady=5, padx=10, fill="x")
        self.search_entry.bind("<KeyRelease>", self.show_suggestions)

        self.suggestion_frame = ctk.CTkFrame(self.sidebar, fg_color="#2D2D2D")
        self.suggestion_list = []

        self.category_dropdown = ctk.CTkComboBox(self.sidebar, values=["All"] + list(self.search_categories.keys()), font=self.font, fg_color="#2D2D2D", button_color="#26A69A", text_color="#FFFFFF")
        self.category_dropdown.pack(pady=5, padx=10, fill="x")

        self.min_price_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Min Price", font=self.font, fg_color="#2D2D2D", text_color="#FFFFFF", border_color="#26A69A")
        self.min_price_entry.pack(pady=5, padx=10, fill="x")

        self.max_price_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Max Price", font=self.font, fg_color="#2D2D2D", text_color="#FFFFFF", border_color="#26A69A")
        self.max_price_entry.pack(pady=5, padx=10, fill="x")

        self.sort_dropdown = ctk.CTkComboBox(self.sidebar, values=["Price", "Newest", "Relevance"], font=self.font, fg_color="#2D2D2D", button_color="#26A69A", text_color="#FFFFFF")
        self.sort_dropdown.pack(pady=5, padx=10, fill="x")

        self.sources = {"eBay": ctk.BooleanVar(value=True), "Etsy": ctk.BooleanVar(value=False)}
        source_frame = ctk.CTkFrame(self.sidebar, fg_color="#1E1E1E")
        source_frame.pack(pady=5, padx=10, fill="x")
        for source, var in self.sources.items():
            ctk.CTkCheckBox(source_frame, text=source, variable=var, font=self.font, text_color="#FFFFFF", fg_color="#26A69A", hover_color="#2ECC71").pack(side="left", padx=5)

        self.search_button = ctk.CTkButton(self.sidebar, text="Search", command=self.start_search, font=self.font, fg_color="#26A69A", hover_color="#2ECC71", text_color="#FFFFFF", corner_radius=8)
        self.search_button.pack(pady=10, padx=10, fill="x")

        self.progress_label = ctk.CTkLabel(self.sidebar, text="Ready to search", font=self.font, text_color="#FFFFFF")
        self.progress_label.pack(pady=5)
        self.loading = False

        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="#121212")
        self.content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.tab_view = ctk.CTkTabview(self.content_frame, fg_color="#1E1E1E", segmented_button_fg_color="#2D2D2D", segmented_button_selected_color="#26A69A", text_color="#FFFFFF")
        self.tab_view.pack(fill="both", expand=True)

        self.tab_frames = {}
        for tab in ["Items", "Favorites"]:
            self.tab_view.add(tab)
            tab_frame = ctk.CTkScrollableFrame(self.tab_view.tab(tab), fg_color="#1E1E1E")
            tab_frame.pack(fill="both", expand=True)
            self.tab_frames[tab] = tab_frame

        self.button_frame = ctk.CTkFrame(self.content_frame, fg_color="#121212")
        self.button_frame.pack(fill="x", pady=5)
        ctk.CTkButton(self.button_frame, text="Export to CSV", command=self.export_csv, font=self.font, fg_color="#FF6F61", hover_color="#FF8A65", text_color="#FFFFFF", corner_radius=8).pack(side="left", padx=5)

        init_db()

    def show_suggestions(self, event):
        if self.suggestion_frame.winfo_ismapped():
            self.suggestion_frame.pack_forget()
        for widget in self.suggestion_list:
            widget.destroy()
        self.suggestion_list = []

        term = self.search_entry.get().strip().lower()
        if not term:
            return

        suggestions = [t for t in self.all_search_terms if term in t.lower()][:5]
        if not suggestions:
            return

        self.suggestion_frame.pack(pady=2, padx=10, fill="x")
        for suggestion in suggestions:
            btn = ctk.CTkButton(self.suggestion_frame, text=suggestion, font=self.font, fg_color="#2D2D2D", hover_color="#26A69A", text_color="#FFFFFF", corner_radius=5, command=lambda s=suggestion: self.select_suggestion(s))
            btn.pack(pady=2, fill="x")
            self.suggestion_list.append(btn)

    def select_suggestion(self, suggestion):
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, suggestion)
        self.suggestion_frame.pack_forget()

    def start_search(self):
        self.search_button.configure(state="disabled")
        self.progress_label.configure(text="Searching...")
        self.loading = True
        threading.Thread(target=self.animate_loading, daemon=True).start()

        for frame in self.tab_frames.values():
            for widget in frame.winfo_children():
                widget.destroy()

        threading.Thread(target=self.run_search, daemon=True).start()

    def animate_loading(self):
        while self.loading:
            for char in ["|", "/", "-", "\\"]:
                if not self.loading:
                    break
                self.progress_label.configure(text=f"Searching... {char}")
                self.root.update()
                time.sleep(0.2)
        self.progress_label.configure(text=f"Search completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def run_search(self):
        max_results = 5
        sort_by = self.sort_dropdown.get().lower()
        min_price = float(self.min_price_entry.get()) if self.min_price_entry.get() else None
        max_price = float(self.max_price_entry.get()) if self.max_price_entry.get() else None
        category = self.category_dropdown.get()
        search_term = self.search_entry.get().strip()

        all_items = []
        search_terms = []

        if search_term:
            search_terms.append(search_term)
        elif category == "All":
            for terms in self.search_categories.values():
                search_terms.extend(terms)
        else:
            search_terms = self.search_categories.get(category, [])

        for term in search_terms:
            self.progress_label.configure(text=f"Searching: {term}")
            self.root.update()

            if self.sources["eBay"].get():
                items = find_ebay_items(term, max_results, sort_by, min_price, max_price)
                for item in items:
                    item["category"] = category if category != "All" else "Custom"
                    item["search_term"] = term
                all_items.extend(items)

            if self.sources["Etsy"].get():
                items = find_etsy_items(term, max_results, sort_by, min_price, max_price)
                for item in items:
                    item["category"] = category if category != "All" else "Custom"
                    item["search_term"] = term
                all_items.extend(items)

            time.sleep(random.uniform(2, 5))

        conn = sqlite3.connect("retro_vault.db")
        c = conn.cursor()
        for item in all_items:
            c.execute('''INSERT INTO items (title, price, condition, link, source, category, search_term, timestamp, description)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (item["title"], item["price"], item["condition"], item["link"],
                       item["source"], item["category"], item["search_term"], item["timestamp"], item["description"]))
        conn.commit()
        conn.close()

        items_frame = self.tab_frames["Items"]
        if not all_items:
            ctk.CTkLabel(items_frame, text="No items found.", font=self.font, text_color="#FFFFFF").pack(pady=10)
        else:
            all_items.sort(key=lambda x: x["price"])
            for item in all_items[:20]:
                deal_frame = ctk.CTkFrame(items_frame, corner_radius=10, fg_color="#2D2D2D", border_color="#26A69A", border_width=1)
                deal_frame.pack(pady=5, padx=10, fill="x")
                deal_frame.bind("<Enter>", lambda e, f=deal_frame: f.configure(fg_color="#3A3A3A"))
                deal_frame.bind("<Leave>", lambda e, f=deal_frame: f.configure(fg_color="#2D2D2D"))
                deal_frame.bind("<Button-1>", lambda e, link=item["link"]: self.open_link(link))

                ctk.CTkLabel(deal_frame, text=f"{item['title'][:60]}...", font=self.bold_font, text_color="#FFFFFF").pack(anchor="w", padx=10, pady=5)
                ctk.CTkLabel(deal_frame, text=f"Price: ${item['price']:.2f}", font=self.font, text_color="#FFFFFF").pack(anchor="w", padx=10, pady=2)
                ctk.CTkLabel(deal_frame, text=f"Condition: {item['condition']}", font=self.font, text_color="#FFFFFF").pack(anchor="w", padx=10, pady=2)
                link_label = ctk.CTkLabel(deal_frame, text="Link: Click card to visit", font=self.font, text_color="#26A69A", cursor="hand2")
                link_label.pack(anchor="w", padx=10, pady=2)
                link_label.bind("<Button-1>", lambda e, link=item["link"]: self.open_link(link))

                fav_button = ctk.CTkButton(deal_frame, text="Add to Favorites", font=self.font, fg_color="#FF6F61", hover_color="#FF8A65", text_color="#FFFFFF", corner_radius=8, width=120)
                fav_button.pack(anchor="w", padx=10, pady=5)
                fav_button.configure(command=lambda d=item, b=fav_button: self.add_to_favorites(d, b))
                fav_button.bind("<Enter>", lambda e, b=fav_button: b.configure(fg_color="#FF8A65"))
                fav_button.bind("<Leave>", lambda e, b=fav_button: b.configure(fg_color="#FF6F61"))

        self.display_favorites()

        self.loading = False
        self.search_button.configure(state="normal")

    def animate_button(self, button):
        original_color = "#FF6F61"
        glow_color = "#FF8A65"
        steps = 10
        delay = 50  

        def fade_in(step=0):
            if step <= steps:
                r1, g1, b1 = tuple(int(original_color[i:i+2], 16) for i in (1, 3, 5))
                r2, g2, b2 = tuple(int(glow_color[i:i+2], 16) for i in (1, 3, 5))
                r = int(r1 + (r2 - r1) * step / steps)
                g = int(g1 + (g2 - g1) * step / steps)
                b = int(b1 + (b2 - b1) * step / steps)
                new_color = f"#{r:02x}{g:02x}{b:02x}"
                button.configure(fg_color=new_color)
                self.root.after(delay, fade_in, step + 1)
            else:
                fade_out(steps)

        def fade_out(step=steps):
            if step >= 0:
                r1, g1, b1 = tuple(int(original_color[i:i+2], 16) for i in (1, 3, 5))
                r2, g2, b2 = tuple(int(glow_color[i:i+2], 16) for i in (1, 3, 5))
                r = int(r1 + (r2 - r1) * step / steps)
                g = int(g1 + (g2 - g1) * step / steps)
                b = int(b1 + (b2 - b1) * step / steps)
                new_color = f"#{r:02x}{g:02x}{b:02x}"
                button.configure(fg_color=new_color)
                self.root.after(delay, fade_out, step - 1)

        fade_in()

    def add_to_favorites(self, item, button):
        conn = sqlite3.connect("retro_vault.db")
        c = conn.cursor()
        c.execute('''SELECT 1 FROM favorites WHERE link=?''', (item["link"],))
        exists = c.fetchone()
        
        if exists:
            print(f"Duplicate found: link={item['link']}")
            messagebox.showinfo("Favorites", "Item already in favorites.")
            conn.close()
            return

        print(f"Adding to favorites: title={item['title']}, link={item['link']}")
        c.execute('''INSERT INTO favorites (title, price, condition, link, source, category, timestamp, description)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (item["title"], item["price"], item["condition"], item["link"],
                   item["source"], item["category"], item["timestamp"], item["description"]))
        conn.commit()
        conn.close()

        self.animate_button(button)
        self.display_favorites()

    def display_favorites(self):
        favorites_frame = self.tab_frames["Favorites"]
        for widget in favorites_frame.winfo_children():
            widget.destroy()

        conn = sqlite3.connect("retro_vault.db")
        c = conn.cursor()
        c.execute("SELECT * FROM favorites")
        favorites = c.fetchall()
        conn.close()

        if not favorites:
            ctk.CTkLabel(favorites_frame, text="No favorites yet.", font=self.font, text_color="#FFFFFF").pack(pady=10)
            return

        for fav in favorites:
            deal_frame = ctk.CTkFrame(favorites_frame, corner_radius=10, fg_color="#2D2D2D", border_color="#26A69A", border_width=1)
            deal_frame.pack(pady=5, padx=10, fill="x")
            deal_frame.bind("<Enter>", lambda e, f=deal_frame: f.configure(fg_color="#3A3A3A"))
            deal_frame.bind("<Leave>", lambda e, f=deal_frame: f.configure(fg_color="#2D2D2D"))
            deal_frame.bind("<Button-1>", lambda e, link=fav[4]: self.open_link(link))

            ctk.CTkLabel(deal_frame, text=f"{fav[1][:60]}...", font=self.bold_font, text_color="#FFFFFF").pack(anchor="w", padx=10, pady=5)
            ctk.CTkLabel(deal_frame, text=f"Price: ${fav[2]:.2f}", font=self.font, text_color="#FFFFFF").pack(anchor="w", padx=10, pady=2)
            ctk.CTkLabel(deal_frame, text=f"Condition: {fav[3]}", font=self.font, text_color="#FFFFFF").pack(anchor="w", padx=10, pady=2)
            link_label = ctk.CTkLabel(deal_frame, text="Link: Click card to visit", font=self.font, text_color="#26A69A", cursor="hand2")
            link_label.pack(anchor="w", padx=10, pady=2)
            link_label.bind("<Button-1>", lambda e, link=fav[4]: self.open_link(link))

    def export_csv(self):
        conn = sqlite3.connect("retro_vault.db")
        df = pd.read_sql_query("SELECT * FROM items", conn)
        conn.close()

        if df.empty:
            messagebox.showinfo("Export", "No data to export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            df.to_csv(file_path, index=False)
            messagebox.showinfo("Export", "Data exported successfully.")

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)

def main():
    root = ctk.CTk()
    app = RetroVaultApp(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")