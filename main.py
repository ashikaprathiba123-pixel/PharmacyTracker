import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from tkcalendar import DateEntry
from graph import show_graph

class PharmacyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("💊 Pharmacy Login")
        self.root.geometry("350x300")
        self.root.configure(bg="#f0f2f5")
        
        # UI Setup
        self.login_frame = tk.Frame(self.root, bg="white", padx=30, pady=30, highlightbackground="#ddd", highlightthickness=1)
        self.login_frame.pack(pady=40)

        tk.Label(self.login_frame, text="PHARMACY LOGIN", font=("Arial", 12, "bold"), bg="white").pack(pady=(0, 15))
        
        tk.Label(self.login_frame, text="Username", bg="white").pack(anchor="w")
        self.user_ent = tk.Entry(self.login_frame, width=25)
        self.user_ent.pack(pady=(0, 10))

        tk.Label(self.login_frame, text="Password", bg="white").pack(anchor="w")
        self.pass_ent = tk.Entry(self.login_frame, show="*", width=25)
        self.pass_ent.pack(pady=(0, 20))

        tk.Button(self.login_frame, text="LOGIN", bg="#007bff", fg="white", width=20, 
                  command=self.login_check, font=("Arial", 10, "bold")).pack()

    def login_check(self):
        u, p = self.user_ent.get().strip(), self.pass_ent.get().strip()
        conn = sqlite3.connect("pharmacy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        if cursor.fetchone():
            conn.close()
            self.login_frame.destroy()
            self.setup_main_app()
            self.auto_notify()
        else:
            messagebox.showerror("Error", "Incorrect Username or Password")

    def setup_main_app(self):
        self.root.geometry("600x800")
        self.root.title("💊 Local Pharmacy Expiry Tracker")
        
        # Header
        header = tk.Frame(self.root, bg="#007bff", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="Pharmacy Dashboard", fg="white", bg="#007bff", font=("Arial", 16, "bold")).pack()

        # Input Area
        input_frame = tk.Frame(self.root, pady=20)
        input_frame.pack()

        tk.Label(input_frame, text="Medicine Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = tk.Entry(input_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(input_frame, text="Quantity:").grid(row=1, column=0, padx=5, pady=5)
        self.qty_entry = tk.Entry(input_frame)
        self.qty_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(input_frame, text="Expiry Date:").grid(row=2, column=0, padx=5, pady=5)
        self.expiry_entry = DateEntry(input_frame, date_pattern='yyyy-mm-dd')
        self.expiry_entry.grid(row=2, column=1, padx=5, pady=5)

        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Add Item", bg="#28a745", fg="white", width=12, command=self.add_medicine).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Show Graph", bg="#6f42c1", fg="white", width=12, command=show_graph).grid(row=0, column=1, padx=5)

        # Table (Treeview)
        self.tree = ttk.Treeview(self.root, columns=("ID", "Name", "Qty", "Expiry"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Medicine")
        self.tree.heading("Qty", text="Qty")
        self.tree.heading("Expiry", text="Expiry Date")
        self.tree.column("ID", width=50)
        self.tree.pack(pady=20, padx=20, fill="both", expand=True)

        # Color Tags
        self.tree.tag_configure('expired', background='#ffcccc') 
        self.tree.tag_configure('soon', background='#fff3cd')    
        self.tree.tag_configure('safe', background='#d4edda')    

        self.view_medicines()

    def add_medicine(self):
        n, q, e = self.name_entry.get(), self.qty_entry.get(), self.expiry_entry.get()
        if not n or not q:
            messagebox.showwarning("Input Error", "Please fill all fields")
            return
        conn = sqlite3.connect("pharmacy.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO medicines (name, quantity, expiry_date) VALUES (?, ?, ?)", (n, q, e))
        conn.commit()
        conn.close()
        self.view_medicines()
        messagebox.showinfo("Success", f"{n} added to inventory")

    def view_medicines(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = sqlite3.connect("pharmacy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medicines")
        today = datetime.today()

        for row in cursor.fetchall():
            try:
                exp_date = datetime.strptime(row[3], "%Y-%m-%d")
                days_left = (exp_date - today).days
                tag = 'expired' if days_left < 0 else 'soon' if days_left <= 30 else 'safe'
                self.tree.insert("", tk.END, values=row, tags=(tag,))
            except: continue
        conn.close()

    def auto_notify(self):
        conn = sqlite3.connect("pharmacy.db")
        cursor = conn.cursor()
        today_str = datetime.today().strftime('%Y-%m-%d')
        cursor.execute("SELECT name FROM medicines WHERE expiry_date <= ?", (today_str,))
        expired = cursor.fetchall()
        if expired:
            names = ", ".join([m[0] for m in expired])
            messagebox.showwarning("URGENT: EXPIRY ALERT", f"Expired items found: {names}\nPlease remove from stock immediately.")
        conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = PharmacyApp(root)
    root.mainloop()