import os
import csv
import calendar
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime, date, timedelta

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    plt = None
    FigureCanvasTkAgg = None


# ============================================================
# CONFIG
# ============================================================

APP_TITLE = "Local Pharmacy"
APP_NAME = "LOCAL PHARMACY INVENTORY AND EXPIRY MANAGEMENT SYSTEM"
DB_FILE = "local_pharmacy_pro.db"
RESET_FLAG_FILE = "mixed_15_medicines_loaded.flag"
LOGO_FILE = "logo8.png"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

LOW_STOCK_LIMIT = 5
NEAR_EXPIRY_DAYS = 30
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================
# THEME
# ============================================================

class Theme:
    # Premium professional theme: navy, white, grey, soft alert colours
    NAVY = "#102A43"
    NAVY_DARK = "#0B1F33"
    BLUE = "#486581"
    SKY = "#627D98"
    BG = "#F5F7FA"
    WHITE = "#FFFFFF"
    CARD = "#FFFFFF"
    TEXT = "#243B53"
    MUTED = "#6B7C93"
    BORDER = "#D9E2EC"

    # Soft highlight colours
    GREEN = "#5B8A72"
    GREEN_DARK = "#4A735F"
    RED = "#B56576"
    RED_DARK = "#9D4E60"
    ORANGE = "#C39A5B"
    ORANGE_DARK = "#A98043"
    TEAL = "#6C8A96"
    GRAY = "#7B8794"
    PURPLE = "#7B8794"

    # Soft table row colours
    RED_ROW = "#F9ECEF"
    ORANGE_ROW = "#FAF2E7"
    YELLOW_ROW = "#FBF7EC"
    GREEN_ROW = "#EFF5F1"
    BLUE_ROW = "#EEF3F7"


# ============================================================
# HELPERS
# ============================================================

def today_str():
    return date.today().strftime(DATE_FORMAT)


def now_str():
    return datetime.now().strftime(DATETIME_FORMAT)


def parse_date(value):
    try:
        return datetime.strptime(str(value), DATE_FORMAT).date()
    except Exception:
        return None


def money(value):
    try:
        return f"₹{float(value):,.2f}"
    except Exception:
        return "₹0.00"


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def center_window(win, width, height):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = int((sw - width) / 2)
    y = int((sh - height) / 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


# ============================================================
# DATABASE
# ============================================================

class Database:
    def __init__(self):
        self.db_file = DB_FILE

    def connect(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'Admin'
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS medicines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    batch_no TEXT DEFAULT '',
                    company TEXT DEFAULT '',
                    supplier TEXT DEFAULT '',
                    quantity INTEGER NOT NULL DEFAULT 0,
                    cost_price REAL NOT NULL DEFAULT 0,
                    selling_price REAL NOT NULL DEFAULT 0,
                    expiry_date TEXT NOT NULL,
                    added_date TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medicine_id INTEGER,
                    medicine_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    selling_price REAL NOT NULL,
                    total REAL NOT NULL,
                    sale_date TEXT NOT NULL,
                    customer_name TEXT DEFAULT '',
                    payment_method TEXT DEFAULT 'Cash',
                    transaction_id TEXT DEFAULT ''
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medicine_id INTEGER,
                    medicine_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    cost_price REAL NOT NULL,
                    total REAL NOT NULL,
                    supplier TEXT DEFAULT '',
                    purchase_date TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            # Migration for existing databases: add transaction/reference number for UPI/Card payments
            cur.execute("PRAGMA table_info(sales)")
            sales_columns = [col[1] for col in cur.fetchall()]
            if "transaction_id" not in sales_columns:
                cur.execute("ALTER TABLE sales ADD COLUMN transaction_id TEXT DEFAULT ''")

            cur.execute(
                "INSERT OR IGNORE INTO users(username, password, role) VALUES (?, ?, ?)",
                (ADMIN_USERNAME, ADMIN_PASSWORD, "Admin")
            )

            # Clear old/sample medicines only once for this final mixed output,
            # then keep future medicines safe.
            self.clear_existing_data_once(conn)
            conn.commit()

            # Final project output: add 15 mixed medicines
            # Safe + Near Expiry + Expired are mixed naturally, not grouped.
            self.seed_mixed_medicines(conn)

    def clear_existing_data_once(self, conn):
        """Erase all existing medicine, sales, purchase, and audit data one time only.
        After first run, a small flag file is created, so newly added medicines
        will not be deleted again when the project is opened next time.
        """
        if os.path.exists(RESET_FLAG_FILE):
            return

        cur = conn.cursor()
        cur.execute("DELETE FROM sales")
        cur.execute("DELETE FROM purchases")
        cur.execute("DELETE FROM medicines")
        cur.execute("DELETE FROM audit_log")

        # Reset auto-increment IDs for clean output.
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('medicines', 'sales', 'purchases', 'audit_log')")
        conn.commit()

        with open(RESET_FLAG_FILE, "w", encoding="utf-8") as f:
            f.write("Medicine data cleared once. Delete this file only if you want to clear again.")

    def seed_mixed_medicines(self, conn):
        """Add 15 mixed medicines for final project output.
        The list is intentionally mixed: Safe, Near Expiry, and Expired medicines
        are inserted in a natural order instead of grouping them together.
        Existing medicine name + batch number combinations are not duplicated.
        """
        cur = conn.cursor()

        mixed_medicines = [
            ("Dolo 650", "Tablet", "DOL101", "Micro Labs", "Metro Pharma", 25, 1.50, 3.00, "2026-10-15"),
            ("Cough Syrup", "Syrup", "COU202", "Sun Pharma", "City Medicos", 8, 55.00, 85.00, "2026-06-10"),
            ("Expired Vitamin B", "Tablet", "EVB303", "HealthCare", "Old Supplier", 12, 2.00, 5.00, "2026-04-20"),

            ("Paracetamol", "Tablet", "PAR404", "Cipla", "HealthPlus Supplier", 40, 1.00, 2.50, "2026-12-25"),
            ("Eye Drops", "Drops", "EYE505", "Allergan", "Local Supplier", 6, 45.00, 75.00, "2026-06-18"),
            ("Expired Pain Balm", "Ointment", "EPB606", "Demo Pharma", "Old Supplier", 5, 30.00, 55.00, "2026-03-15"),

            ("Amoxicillin", "Capsule", "AMX707", "Mankind", "Metro Pharma", 18, 6.00, 12.00, "2026-11-30"),
            ("ORS Sachet", "Other", "ORS808", "Electral", "City Medicos", 10, 8.00, 15.00, "2026-06-22"),
            ("Expired Syrup", "Syrup", "EXS909", "Demo Pharma", "Old Supplier", 7, 40.00, 70.00, "2026-02-10"),

            ("Pantoprazole", "Tablet", "PNT111", "Alkem", "HealthPlus Supplier", 30, 3.00, 7.00, "2027-01-12"),
            ("Azithromycin", "Tablet", "AZM222", "Cipla", "Metro Pharma", 9, 12.00, 22.00, "2026-06-25"),
            ("Expired Capsule", "Capsule", "EXC333", "Demo Pharma", "Old Supplier", 4, 5.00, 10.00, "2026-01-05"),

            ("Betadine Ointment", "Ointment", "BTD444", "Win Medicare", "City Medicos", 14, 55.00, 85.00, "2027-02-14"),
            ("Insulin Injection", "Injection", "INS555", "Novo Nordisk", "HealthPlus Supplier", 3, 210.00, 280.00, "2026-06-15"),
            ("Expired Antibiotic", "Tablet", "EAB666", "Old Pharma", "Old Supplier", 6, 10.00, 18.00, "2026-04-01"),
        ]

        for item in mixed_medicines:
            name, category, batch_no, company, supplier, quantity, cost_price, selling_price, expiry_date = item

            exists = cur.execute(
                "SELECT id FROM medicines WHERE name=? AND batch_no=?",
                (name, batch_no)
            ).fetchone()

            if exists:
                continue

            cur.execute("""
                INSERT INTO medicines
                (name, category, batch_no, company, supplier, quantity, cost_price,
                 selling_price, expiry_date, added_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, category, batch_no, company, supplier, quantity, cost_price,
                selling_price, expiry_date, now_str(), now_str()
            ))

            med_id = cur.lastrowid
            cur.execute("""
                INSERT INTO purchases
                (medicine_id, medicine_name, quantity, cost_price, total, supplier, purchase_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                med_id, name, quantity, cost_price, quantity * cost_price, supplier, now_str()
            ))

        conn.commit()

    def seed_demo_data(self, conn):
        cur = conn.cursor()
        count = cur.execute("SELECT COUNT(*) AS c FROM medicines").fetchone()["c"]
        if count > 0:
            return

        sample = [
            ("Dolo 650", "Tablet", "B102", "Micro Labs", "HealthPlus Supplier", 4, 1.30, 2.50, date.today() + timedelta(days=20)),
            ("Paracetamol", "Tablet", "P201", "Cipla", "Metro Pharma", 25, 1.00, 3.00, date.today() + timedelta(days=150)),
            ("Cough Syrup", "Syrup", "S909", "Sun Pharma", "City Medicos", 8, 65.00, 95.00, date.today() + timedelta(days=60)),
            ("Vitamin C", "Capsule", "V707", "HealthCare", "Goodwill Supplier", 3, 4.50, 8.00, date.today() + timedelta(days=15)),
            ("Expired Test Med", "Tablet", "E001", "Demo Pharma", "Old Supplier", 6, 2.50, 5.00, date.today() - timedelta(days=7)),
        ]

        for item in sample:
            cur.execute("""
                INSERT INTO medicines
                (name, category, batch_no, company, supplier, quantity, cost_price, selling_price, expiry_date, added_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7],
                item[8].strftime(DATE_FORMAT), now_str(), now_str()
            ))

        conn.commit()

    def seed_extra_medicines(self, conn):
        """Add 9 extra medicines automatically for final project output.
        Existing records are not duplicated because medicine name + batch number is checked.
        """
        cur = conn.cursor()

        extra_medicines = [
            ("Azithromycin", "Tablet", "AZM112", "Cipla", "Metro Pharma", 12, 12.00, 22.00, "2026-06-05"),
            ("Pantoprazole", "Tablet", "PNT320", "Alkem", "HealthPlus Supplier", 16, 3.00, 7.00, "2026-06-12"),
            ("ORS Sachet", "Other", "ORS778", "Electral", "City Medicos", 20, 8.00, 15.00, "2026-06-20"),
            ("Eye Drops", "Drops", "EYD501", "Allergan", "Local Supplier", 10, 45.00, 75.00, "2026-06-22"),
            ("Amoxicillin", "Capsule", "AMX101", "Mankind", "Metro Pharma", 3, 6.00, 12.00, "2026-12-30"),
            ("Betadine Ointment", "Ointment", "BTD909", "Win Medicare", "City Medicos", 4, 55.00, 85.00, "2027-02-14"),
            ("Insulin Injection", "Injection", "INS432", "Novo Nordisk", "HealthPlus Supplier", 2, 210.00, 280.00, "2026-08-18"),
            ("Expired Syrup", "Syrup", "EXS002", "Demo Pharma", "Old Supplier", 6, 40.00, 70.00, "2026-01-15"),
            ("Expired Capsule", "Capsule", "EXC003", "Demo Pharma", "Old Supplier", 5, 5.00, 10.00, "2026-02-20"),
        ]

        for item in extra_medicines:
            name, category, batch_no, company, supplier, quantity, cost_price, selling_price, expiry_date = item

            exists = cur.execute(
                "SELECT id FROM medicines WHERE name=? AND batch_no=?",
                (name, batch_no)
            ).fetchone()

            if exists:
                continue

            cur.execute("""
                INSERT INTO medicines
                (name, category, batch_no, company, supplier, quantity, cost_price,
                 selling_price, expiry_date, added_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, category, batch_no, company, supplier, quantity, cost_price,
                selling_price, expiry_date, now_str(), now_str()
            ))

            med_id = cur.lastrowid
            cur.execute("""
                INSERT INTO purchases
                (medicine_id, medicine_name, quantity, cost_price, total, supplier, purchase_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                med_id, name, quantity, cost_price, quantity * cost_price, supplier, now_str()
            ))

        conn.commit()

    def verify_login(self, username, password):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, password)
            ).fetchone()
            return row is not None

    def log(self, action, details=""):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_log(action, details, created_at) VALUES (?, ?, ?)",
                (action, details, now_str())
            )
            conn.commit()

    def stats(self):
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM medicines").fetchone()["c"]

            expired = conn.execute(
                "SELECT COUNT(*) AS c FROM medicines WHERE date(expiry_date) < date(?)",
                (today_str(),)
            ).fetchone()["c"]

            near = conn.execute(
                "SELECT COUNT(*) AS c FROM medicines WHERE date(expiry_date) BETWEEN date(?) AND date(?)",
                (today_str(), (date.today() + timedelta(days=NEAR_EXPIRY_DAYS)).strftime(DATE_FORMAT))
            ).fetchone()["c"]

            low = conn.execute(
                "SELECT COUNT(*) AS c FROM medicines WHERE quantity <= ?",
                (LOW_STOCK_LIMIT,)
            ).fetchone()["c"]

            stock_value = conn.execute(
                "SELECT IFNULL(SUM(quantity * cost_price), 0) AS v FROM medicines"
            ).fetchone()["v"]

            sales_total = conn.execute(
                "SELECT IFNULL(SUM(total), 0) AS s FROM sales"
            ).fetchone()["s"]

            today_sales = conn.execute(
                "SELECT IFNULL(SUM(total), 0) AS s FROM sales WHERE date(sale_date)=date(?)",
                (today_str(),)
            ).fetchone()["s"]

            today_added = conn.execute(
                "SELECT COUNT(*) AS c FROM medicines WHERE date(added_date)=date(?)",
                (today_str(),)
            ).fetchone()["c"]

            return {
                "total": total,
                "expired": expired,
                "near": near,
                "low": low,
                "stock_value": stock_value,
                "sales_total": sales_total,
                "today_sales": today_sales,
                "today_added": today_added,
            }

    def get_medicines(self, keyword="", status="All", batch_keyword=""):
        query = """
            SELECT id, name, category, batch_no, company, supplier, quantity,
                   cost_price, selling_price, expiry_date, added_date, updated_at
            FROM medicines
        """
        params = []
        where = []

        if keyword:
            like = f"%{keyword}%"
            where.append("""
                (
                    name LIKE ?
                    OR category LIKE ?
                    OR batch_no LIKE ?
                    OR company LIKE ?
                    OR supplier LIKE ?
                )
            """)
            params.extend([like, like, like, like, like])

        # Separate batch number search for faster pharmacy batch-wise checking
        if batch_keyword:
            where.append("batch_no LIKE ?")
            params.append(f"%{batch_keyword}%")

        if status == "Expired":
            where.append("date(expiry_date) < date(?)")
            params.append(today_str())
        elif status == "Near Expiry":
            where.append("date(expiry_date) BETWEEN date(?) AND date(?)")
            params.append(today_str())
            params.append((date.today() + timedelta(days=NEAR_EXPIRY_DAYS)).strftime(DATE_FORMAT))
        elif status == "Low Stock":
            where.append("quantity <= ?")
            params.append(LOW_STOCK_LIMIT)
        elif status == "Safe":
            where.append("quantity > ? AND date(expiry_date) > date(?)")
            params.append(LOW_STOCK_LIMIT)
            params.append((date.today() + timedelta(days=NEAR_EXPIRY_DAYS)).strftime(DATE_FORMAT))

        if where:
            query += " WHERE " + " AND ".join(where)

        query += " ORDER BY id DESC"

        with self.connect() as conn:
            return conn.execute(query, params).fetchall()

    def get_medicine(self, med_id):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()

    def find_same_batch_medicine(self, name, batch_no, expiry_date, exclude_id=None):
        """Find exact same medicine batch.
        Pharmacy rule: same medicine + same batch + same expiry must be updated
        using Add Stock, not added again as a duplicate medicine record.
        """
        query = """
            SELECT id, name, batch_no, expiry_date, quantity
            FROM medicines
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
              AND TRIM(batch_no) = TRIM(?)
              AND expiry_date = ?
        """
        params = [name, batch_no, expiry_date]

        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)

        with self.connect() as conn:
            return conn.execute(query, params).fetchone()

    def add_medicine(self, data):
        same_batch = self.find_same_batch_medicine(
            data["name"],
            data["batch_no"],
            data["expiry_date"]
        )
        if same_batch:
            return False, (
                "This same medicine with the same batch number and same expiry date already exists.\n\n"
                "Please select that medicine from Inventory and use Add Stock instead."
            )

        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO medicines
                (name, category, batch_no, company, supplier, quantity, cost_price,
                 selling_price, expiry_date, added_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["name"], data["category"], data["batch_no"], data["company"],
                data["supplier"], data["quantity"], data["cost_price"], data["selling_price"],
                data["expiry_date"], now_str(), now_str()
            ))

            med_id = cur.lastrowid
            cur.execute("""
                INSERT INTO purchases
                (medicine_id, medicine_name, quantity, cost_price, total, supplier, purchase_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                med_id, data["name"], data["quantity"], data["cost_price"],
                data["quantity"] * data["cost_price"], data["supplier"], now_str()
            ))

            conn.commit()
            self.log("ADD_MEDICINE", data["name"])
            return True, "Medicine added successfully."

    def update_medicine(self, med_id, data):
        same_batch = self.find_same_batch_medicine(
            data["name"],
            data["batch_no"],
            data["expiry_date"],
            exclude_id=med_id
        )
        if same_batch:
            return False, (
                "Another record already has the same medicine name, batch number, and expiry date.\n\n"
                "Please update stock in the existing record instead of creating duplicate batches."
            )

        with self.connect() as conn:
            conn.execute("""
                UPDATE medicines
                SET name=?, category=?, batch_no=?, company=?, supplier=?,
                    quantity=?, cost_price=?, selling_price=?, expiry_date=?, updated_at=?
                WHERE id=?
            """, (
                data["name"], data["category"], data["batch_no"], data["company"],
                data["supplier"], data["quantity"], data["cost_price"], data["selling_price"],
                data["expiry_date"], now_str(), med_id
            ))
            conn.commit()
            self.log("UPDATE_MEDICINE", str(med_id))
            return True, "Medicine updated successfully."

    def delete_medicine(self, med_id):
        with self.connect() as conn:
            med = conn.execute("SELECT name FROM medicines WHERE id=?", (med_id,)).fetchone()
            conn.execute("DELETE FROM medicines WHERE id=?", (med_id,))
            conn.commit()
            self.log("DELETE_MEDICINE", med["name"] if med else str(med_id))

    def add_stock(self, med_id, qty, cost_price, supplier):
        with self.connect() as conn:
            med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
            if not med:
                return False

            expiry = parse_date(med["expiry_date"])
            if expiry is None:
                return False

            if expiry < date.today():
                return False

            new_qty = med["quantity"] + qty
            conn.execute("""
                UPDATE medicines
                SET quantity=?, cost_price=?, supplier=?, updated_at=?
                WHERE id=?
            """, (new_qty, cost_price, supplier, now_str(), med_id))

            conn.execute("""
                INSERT INTO purchases
                (medicine_id, medicine_name, quantity, cost_price, total, supplier, purchase_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                med_id, med["name"], qty, cost_price, qty * cost_price, supplier, now_str()
            ))

            conn.commit()
            self.log("ADD_STOCK", f"{med['name']} +{qty}")
            return True

    def sell_medicine(self, med_id, qty, customer="", payment="Cash", transaction_id=""):
        with self.connect() as conn:
            med = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
            if not med:
                return False, "Medicine not found."

            # Final safety validation at database level also.
            # Even if the form validation is missed, wrong sales should not be saved.
            if qty is None or qty <= 0:
                return False, "Quantity must be greater than zero."

            if med["quantity"] <= 0:
                return False, "This medicine is out of stock."

            expiry = parse_date(med["expiry_date"])
            if expiry is None:
                return False, "Invalid expiry date. Selling is not allowed."

            if expiry < date.today():
                return False, "This medicine is expired. Selling is not allowed."

            if med["quantity"] < qty:
                return False, f"Not enough stock available. Only {med['quantity']} units are available."

            if med["selling_price"] <= 0:
                return False, "Invalid selling price. Sale cannot be completed."

            allowed_payments = ["Cash", "UPI", "Card"]
            if payment not in allowed_payments:
                return False, "Please select a valid payment method."

            if payment in ("UPI", "Card") and not transaction_id.strip():
                return False, f"{payment} reference/transaction number is required."

            total = qty * med["selling_price"]
            new_qty = med["quantity"] - qty

            conn.execute(
                "UPDATE medicines SET quantity=?, updated_at=? WHERE id=?",
                (new_qty, now_str(), med_id)
            )

            conn.execute("""
                INSERT INTO sales
                (medicine_id, medicine_name, quantity, selling_price, total, sale_date, customer_name, payment_method, transaction_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                med_id, med["name"], qty, med["selling_price"], total, now_str(),
                customer.strip(), payment, transaction_id.strip()
            ))

            conn.commit()
            self.log("SALE", f"{med['name']} qty {qty}")
            return True, f"Sale completed. Total amount: {money(total)}"

    def sales_rows(self):
        with self.connect() as conn:
            return conn.execute("""
                SELECT id, medicine_name, quantity, selling_price, total, sale_date, customer_name, payment_method, transaction_id
                FROM sales
                ORDER BY id DESC
            """).fetchall()

    def purchase_rows(self):
        with self.connect() as conn:
            return conn.execute("""
                SELECT id, medicine_name, quantity, cost_price, total, supplier, purchase_date
                FROM purchases
                ORDER BY id DESC
            """).fetchall()

    def alert_rows(self):
        with self.connect() as conn:
            return conn.execute("""
                SELECT name, quantity, expiry_date
                FROM medicines
                WHERE quantity <= ?
                   OR date(expiry_date) < date(?)
                   OR date(expiry_date) BETWEEN date(?) AND date(?)
                ORDER BY date(expiry_date) ASC
            """, (
                LOW_STOCK_LIMIT,
                today_str(),
                today_str(),
                (date.today() + timedelta(days=NEAR_EXPIRY_DAYS)).strftime(DATE_FORMAT)
            )).fetchall()


# ============================================================
# MAIN APPLICATION
# ============================================================

class PharmacyApp:
    def __init__(self, root):
        self.root = root
        self.db = Database()
        self.db.init_db()

        self.root.title(APP_TITLE)
        self.root.geometry("1500x850")
        self.root.minsize(1250, 720)
        self.root.configure(bg=Theme.BG)

        self.current_user = None
        self.selected_id = None
        self.bg_photo = None
        self.logo_bg_label = None
        self.alert_shown = False

        self.setup_style()
        self.show_login()

    # --------------------------------------------------------
    # BASIC UI
    # --------------------------------------------------------

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # 10x polished global UI style: cleaner tables, premium headings, neat spacing.
        self.root.option_add("*Font", "{Segoe UI} 10")
        self.root.option_add("*TCombobox*Listbox.font", "{Segoe UI} 10")

        style.configure(
            "Treeview",
            background=Theme.WHITE,
            foreground=Theme.TEXT,
            rowheight=36,
            fieldbackground=Theme.WHITE,
            bordercolor=Theme.BORDER,
            lightcolor=Theme.BORDER,
            darkcolor=Theme.BORDER,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading",
            background="#EAF2F8",
            foreground=Theme.NAVY,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=(8, 10)
        )
        style.configure(
            "Dashboard.Treeview",
            background=Theme.WHITE,
            foreground=Theme.TEXT,
            rowheight=40,
            fieldbackground=Theme.WHITE,
            bordercolor="#C9D6E2",
            lightcolor="#C9D6E2",
            darkcolor="#C9D6E2",
            font=("Segoe UI", 10, "bold")
        )
        style.configure(
            "Dashboard.Treeview.Heading",
            background="#E8F1F7",
            foreground=Theme.NAVY,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=(10, 12)
        )
        style.map(
            "Treeview",
            background=[("selected", Theme.NAVY)],
            foreground=[("selected", Theme.WHITE)]
        )
        style.configure("Vertical.TScrollbar", gripcount=0, background="#D9E2EC", troughcolor="#F5F7FA", bordercolor=Theme.BORDER)
        style.configure("Horizontal.TScrollbar", gripcount=0, background="#D9E2EC", troughcolor="#F5F7FA", bordercolor=Theme.BORDER)
        style.configure("TCombobox", padding=(6, 4), fieldbackground=Theme.WHITE, background=Theme.WHITE)

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def button(self, parent, text, command, bg=Theme.NAVY, width=None, height=2):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=Theme.WHITE,
            activebackground=Theme.NAVY_DARK,
            activeforeground=Theme.WHITE,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            width=width,
            height=height,
            padx=10,
            pady=2
        )

        def on_enter(event):
            btn.config(bg=Theme.NAVY_DARK if bg == Theme.NAVY else bg)

        def on_leave(event):
            btn.config(bg=bg)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def entry(self, parent, width=30, show=None):
        return tk.Entry(
            parent,
            width=width,
            show=show,
            font=("Segoe UI", 11),
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=Theme.BORDER,
            highlightcolor=Theme.BLUE
        )

    # --------------------------------------------------------
    # LOGIN PAGE
    # --------------------------------------------------------

    def show_login(self):
        self.clear()
        self.root.bind("<Return>", lambda event: self.login())

        self.logo_bg_label = tk.Label(self.root)
        self.logo_bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.set_login_background()
        self.root.bind("<Configure>", self.resize_login_background)

        self.create_login_card()

    def set_login_background(self):
        if Image is None or ImageTk is None or not os.path.exists(LOGO_FILE):
            self.logo_bg_label.config(
                bg="#EAF4FF",
                text="Keep logo3.png in the same folder as gui.py",
                fg=Theme.NAVY,
                font=("Segoe UI", 18, "bold")
            )
            return

        try:
            win_w = max(self.root.winfo_width(), 1200)
            win_h = max(self.root.winfo_height(), 720)

            img = Image.open(LOGO_FILE).convert("RGB")
            img_w, img_h = img.size
            scale = max(win_w / img_w, win_h / img_h)

            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

            left = (new_w - win_w) // 2
            top = (new_h - win_h) // 2
            img = img.crop((left, top, left + win_w, top + win_h))

            self.bg_photo = ImageTk.PhotoImage(img)
            self.logo_bg_label.config(image=self.bg_photo)
            self.logo_bg_label.image = self.bg_photo
        except Exception:
            self.logo_bg_label.config(bg="#EAF4FF")

    def resize_login_background(self, event=None):
        if hasattr(self, "logo_bg_label") and self.logo_bg_label.winfo_exists():
            self.set_login_background()

    def create_login_card(self):
        """Matching professional medical admin portal.
        Only the login card is redesigned; all project features stay unchanged.
        """
        def rounded_rect(canvas, x1, y1, x2, y2, r=24, **kwargs):
            points = [
                x1 + r, y1, x2 - r, y1,
                x2, y1, x2, y1 + r,
                x2, y2 - r, x2, y2,
                x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r,
                x1, y1 + r, x1, y1
            ]
            return canvas.create_polygon(points, smooth=True, **kwargs)

        # Card colours selected to match the logo3.png background:
        # soft pharmacy blue + navy + clean white glass look.
        CARD_BG = "#F3F9FD"
        CARD_INNER = "#FFFFFF"
        NAVY = "#062B46"
        BLUE = "#1677B7"
        SOFT_BLUE = "#DDEFF8"
        BORDER = "#BFD7E8"
        MUTED = "#5E7182"

        # Keep card on right side so the Local Pharmacy background remains visible.
        card = tk.Canvas(self.root, width=500, height=500, bg="#EDF6FC", bd=0, highlightthickness=0)
        card.place(relx=0.765, rely=0.535, anchor="center")

        # Soft shadow + frosted professional panel
        rounded_rect(card, 30, 34, 472, 474, r=34, fill="#AFC5D4", outline="")
        rounded_rect(card, 22, 24, 464, 464, r=34, fill=CARD_BG, outline=BORDER, width=2)
        rounded_rect(card, 42, 44, 444, 444, r=26, fill=CARD_INNER, outline="#D8E7F1", width=1)

        # Subtle medical blue corner shapes, matching the background design
        card.create_arc(340, 8, 540, 208, start=180, extent=90, fill="#C7E4F3", outline="")
        card.create_arc(378, 30, 560, 224, start=180, extent=90, fill="#8CC7E7", outline="")
        card.create_arc(410, 58, 574, 246, start=180, extent=90, fill=BLUE, outline="")
        card.create_oval(58, 388, 170, 500, fill="#E8F4FA", outline="")
        card.create_oval(82, 410, 198, 520, fill="#D7ECF8", outline="")

        # Medical icon badge
        card.create_oval(206, 58, 294, 146, fill="#FFFFFF", outline="#C1DDED", width=2)
        card.create_oval(222, 74, 278, 130, fill=SOFT_BLUE, outline="")
        card.create_rectangle(244, 88, 256, 116, fill=BLUE, outline="")
        card.create_rectangle(230, 96, 270, 108, fill=BLUE, outline="")

        # Portal heading - same professional palette as the background
        card.create_text(250, 188, text="Admin Portal", fill=NAVY, font=("Segoe UI", 30, "bold"))

        # Animated login text
        self.login_animation_text = card.create_text(
            250,
            220,
            text="Welcome to Local Pharmacy",
            fill=BLUE,
            font=("Segoe UI", 11, "bold")
        )

        self.login_anim_index = 0
        self.login_anim_messages = [
            "Welcome to Local Pharmacy",
            "Manage Stock Safely",
            "Track Expiry Dates Easily",
            "Secure Admin Login"
        ]

        def animate_login_text():
            if not card.winfo_exists():
                return

            self.login_anim_index = (self.login_anim_index + 1) % len(self.login_anim_messages)
            card.itemconfig(
                self.login_animation_text,
                text=self.login_anim_messages[self.login_anim_index]
            )

            self.root.after(1800, animate_login_text)

        animate_login_text()

        card.create_text(250, 247, text="Secure access for stock, billing and expiry records", fill=MUTED, font=("Segoe UI", 9))
        card.create_line(78, 270, 422, 270, fill="#D7E6F0", width=1)

        # Username field
        card.create_text(82, 300, text="Username", anchor="w", fill=NAVY, font=("Segoe UI", 10, "bold"))
        rounded_rect(card, 78, 318, 422, 367, r=13, fill="#F7FBFE", outline="#C7D9E6", width=1)
        card.create_text(106, 343, text="👤", fill=BLUE, font=("Segoe UI Emoji", 14))
        self.login_username = tk.Entry(
            card,
            font=("Segoe UI", 12),
            bd=0,
            bg="#F7FBFE",
            fg="#243B53",
            insertbackground=NAVY
        )
        self.login_username.insert(0, ADMIN_USERNAME)
        card.create_window(268, 343, window=self.login_username, width=282, height=28)

        # Password field
        card.create_text(82, 392, text="Password", anchor="w", fill=NAVY, font=("Segoe UI", 10, "bold"))
        rounded_rect(card, 78, 410, 422, 459, r=13, fill="#F7FBFE", outline="#C7D9E6", width=1)
        card.create_text(106, 435, text="🔒", fill=BLUE, font=("Segoe UI Emoji", 14))
        self.login_password = tk.Entry(
            card,
            font=("Segoe UI", 12),
            bd=0,
            bg="#F7FBFE",
            fg="#243B53",
            insertbackground=NAVY,
            show="*"
        )
        card.create_window(268, 435, window=self.login_password, width=282, height=28)

        # Button placed slightly below card using same navy-blue medical shade
        login_btn = tk.Button(
            card,
            text="LOGIN→",
            bg=NAVY,
            fg="#FFFFFF",
            activebackground="#041D31",
            activeforeground="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.login
        )
        card.create_window(250, 486, window=login_btn, width=344, height=46)

        self.login_password.focus_set()

    def login(self):
        username = self.login_username.get().strip()
        password = self.login_password.get().strip()

        if self.db.verify_login(username, password):
            self.current_user = username
            self.db.log("LOGIN", f"{username} logged in")
            self.root.unbind("<Configure>")
            self.show_app()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")

    # --------------------------------------------------------
    # MAIN LAYOUT
    # --------------------------------------------------------

    def show_app(self):
        self.clear()
        self.root.configure(bg=Theme.BG)
        self.root.bind("<Return>", lambda event: None)

        self.create_header()
        self.create_main_body()
        self.show_dashboard()
        self.root.after(600, self.show_startup_alerts)

    def create_header(self):
        header = tk.Frame(self.root, bg=Theme.NAVY, height=82)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=APP_NAME,
            bg=Theme.NAVY,
            fg=Theme.WHITE,
            font=("Segoe UI", 22, "bold")
        ).pack(side="left", padx=28)

        self.clock_label = tk.Label(
            header,
            text="",
            bg=Theme.NAVY,
            fg="#DDEFFF",
            font=("Segoe UI", 11, "bold")
        )
        self.clock_label.pack(side="right", padx=(0, 25))

        tk.Label(
            header,
            text="👤 Admin",
            bg=Theme.NAVY,
            fg=Theme.WHITE,
            font=("Segoe UI", 11, "bold")
        ).pack(side="right", padx=(0, 25))

        self.update_clock()

    def update_clock(self):
        if hasattr(self, "clock_label") and self.clock_label.winfo_exists():
            self.clock_label.config(text=datetime.now().strftime("📅 %d-%m-%Y   %I:%M:%S %p"))
            self.root.after(1000, self.update_clock)

    def create_main_body(self):
        body = tk.Frame(self.root, bg=Theme.BG)
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=Theme.WHITE, width=245)
        self.sidebar.pack(side="left", fill="y", padx=(18, 10), pady=18)
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(body, bg=Theme.BG)
        self.content.pack(side="right", fill="both", expand=True, padx=(10, 18), pady=18)

        self.create_sidebar()

    def create_sidebar(self):
        tk.Label(
            self.sidebar,
            text="PHARMACY MENU",
            bg=Theme.WHITE,
            fg=Theme.NAVY,
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=18, pady=(22, 12))

        menu = [
            ("🏠  Dashboard", self.show_dashboard, Theme.NAVY),
            ("💊  Inventory", self.show_inventory, Theme.NAVY),
            ("➕  Add Medicine", self.open_add_medicine, Theme.NAVY),
            ("📦  Add Stock", self.open_add_stock, Theme.NAVY),
            ("🧾  Sell Medicine", self.open_sell_medicine, Theme.NAVY),
            ("📈  Analytics", self.show_analytics, Theme.NAVY),
            ("📄  Reports", self.show_reports, Theme.NAVY),
            ("⟳  Refresh", self.refresh_all, Theme.NAVY),
        ]

        for text, command, color in menu:
            self.button(self.sidebar, text, command, bg=color, width=22).pack(padx=14, pady=5, fill="x")

        tk.Frame(self.sidebar, bg="#E4E7EC", height=1).pack(fill="x", padx=18, pady=20)

        self.button(self.sidebar, "⏻  Logout", self.logout, bg=Theme.RED, width=22).pack(padx=14, pady=5, fill="x")


    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def page_title(self, title, subtitle):
        top = tk.Frame(self.content, bg=Theme.WHITE, bd=1, relief="solid")
        top.pack(fill="x", pady=(0, 14))

        accent = tk.Frame(top, bg=Theme.NAVY, width=6)
        accent.pack(side="left", fill="y")

        text_box = tk.Frame(top, bg=Theme.WHITE)
        text_box.pack(side="left", fill="x", expand=True, padx=16, pady=12)

        tk.Label(text_box, text=title, bg=Theme.WHITE, fg=Theme.NAVY, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(text_box, text=subtitle, bg=Theme.WHITE, fg=Theme.MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

    # --------------------------------------------------------
    # DASHBOARD PAGE
    # --------------------------------------------------------

    def show_dashboard(self):
        self.clear_content()
        self.page_title("Dashboard", "")

        self.cards_frame = tk.Frame(self.content, bg=Theme.BG)
        self.cards_frame.pack(fill="x", pady=(0, 12))

        stats = self.db.stats()

        self.metric_card(self.cards_frame, "💊", "Total Medicines", str(stats["total"]), Theme.NAVY)
        self.metric_card(self.cards_frame, "⛔", "Expired", str(stats["expired"]), Theme.RED)
        self.metric_card(self.cards_frame, "⚠", "Near Expiry", str(stats["near"]), Theme.ORANGE)
        self.metric_card(self.cards_frame, "📉", "Low Stock", str(stats["low"]), Theme.GREEN)

        self.cards_frame2 = tk.Frame(self.content, bg=Theme.BG)
        self.cards_frame2.pack(fill="x", pady=(0, 14))

        self.metric_card(self.cards_frame2, "₹", "Stock Value", money(stats["stock_value"]), Theme.BLUE)
        self.metric_card(self.cards_frame2, "🧾", "Total Sales", money(stats["sales_total"]), Theme.GRAY)
        self.metric_card(self.cards_frame2, "📅", "Today Sales", money(stats["today_sales"]), Theme.SKY)
        self.metric_card(self.cards_frame2, "➕", "Added Today", str(stats["today_added"]), Theme.GRAY)

        # 10/10 dashboard alert panel: rounded premium card, clean header and bold readable rows.
        panel_canvas = tk.Canvas(self.content, bg=Theme.BG, bd=0, highlightthickness=0)
        panel_canvas.pack(fill="both", expand=True)

        panel = tk.Frame(panel_canvas, bg=Theme.WHITE)
        panel_window = panel_canvas.create_window(18, 18, anchor="nw", window=panel)

        def rounded_rect(canvas, x1, y1, x2, y2, r=24, **kwargs):
            points = [
                x1 + r, y1, x2 - r, y1,
                x2, y1, x2, y1 + r,
                x2, y2 - r, x2, y2,
                x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r,
                x1, y1 + r, x1, y1
            ]
            return canvas.create_polygon(points, smooth=True, **kwargs)

        def resize_panel(event=None):
            panel_canvas.delete("bg")
            w = max(panel_canvas.winfo_width(), 300)
            h = max(panel_canvas.winfo_height(), 220)
            rounded_rect(panel_canvas, 8, 10, w - 8, h - 8, r=22, fill="#D7E1EA", outline="", tags="bg")
            rounded_rect(panel_canvas, 2, 2, w - 14, h - 16, r=22, fill=Theme.WHITE, outline="#C7D5E2", width=1, tags="bg")
            panel_canvas.coords(panel_window, 20, 18)
            panel_canvas.itemconfig(panel_window, width=max(w - 44, 260), height=max(h - 42, 180))
            panel_canvas.tag_lower("bg")

        panel_canvas.bind("<Configure>", resize_panel)

        top = tk.Frame(panel, bg=Theme.WHITE)
        top.pack(fill="x", padx=18, pady=(16, 10))

        left_head = tk.Frame(top, bg=Theme.WHITE)
        left_head.pack(side="left")
        tk.Label(left_head, text="🚨 Critical Alerts", bg=Theme.WHITE, fg=Theme.NAVY_DARK, font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(left_head, text="Expired, near-expiry and low-stock medicines needing attention", bg=Theme.WHITE, fg=Theme.MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 0))

        limit_badge = tk.Label(
            top,
            text=f"Low stock ≤ {LOW_STOCK_LIMIT}   •   Near expiry: {NEAR_EXPIRY_DAYS} days",
            bg="#EEF5F9",
            fg=Theme.NAVY,
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=7
        )
        limit_badge.pack(side="right")

        table_box = tk.Frame(panel, bg=Theme.WHITE)
        table_box.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        columns = ("Medicine", "Qty", "Expiry", "Alert")
        self.alert_table = ttk.Treeview(table_box, columns=columns, show="headings", height=9, style="Dashboard.Treeview")
        for col in columns:
            self.alert_table.heading(col, text=col)

        self.alert_table.column("Medicine", width=390, anchor="w")
        self.alert_table.column("Qty", width=120, anchor="center")
        self.alert_table.column("Expiry", width=180, anchor="center")
        self.alert_table.column("Alert", width=250, anchor="center")

        self.alert_table.tag_configure("expired", background="#F7E6EA", foreground="#8B263D")
        self.alert_table.tag_configure("near", background="#FBF0DF", foreground="#805513")
        self.alert_table.tag_configure("low", background="#FFF6DC", foreground="#6D5000")

        yscroll = ttk.Scrollbar(table_box, orient="vertical", command=self.alert_table.yview)
        self.alert_table.configure(yscrollcommand=yscroll.set)
        self.alert_table.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        today = date.today()
        near_date = today + timedelta(days=NEAR_EXPIRY_DAYS)

        for row in self.db.alert_rows():
            expiry = parse_date(row["expiry_date"])
            tag = "low"
            alert = "Low Stock"

            if expiry and expiry < today:
                tag = "expired"
                alert = "Expired"
            elif expiry and today <= expiry <= near_date:
                tag = "near"
                alert = "Near Expiry"
            elif row["quantity"] <= LOW_STOCK_LIMIT:
                tag = "low"
                alert = "Low Stock"

            self.alert_table.insert("", "end", values=(row["name"], row["quantity"], row["expiry_date"], alert), tags=(tag,))

    def metric_card(self, parent, icon, title, value, color):
        # 10/10 premium metric card: rounded corners, shadow, colored badge and clean spacing.
        card_canvas = tk.Canvas(parent, width=10, height=124, bg=Theme.BG, bd=0, highlightthickness=0)
        card_canvas.pack(side="left", fill="x", expand=True, padx=5)

        def rounded_rect(canvas, x1, y1, x2, y2, r=20, **kwargs):
            points = [
                x1 + r, y1, x2 - r, y1,
                x2, y1, x2, y1 + r,
                x2, y2 - r, x2, y2,
                x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r,
                x1, y1 + r, x1, y1
            ]
            return canvas.create_polygon(points, smooth=True, **kwargs)

        def draw_card(event=None):
            card_canvas.delete("all")
            w = max(card_canvas.winfo_width(), 190)
            h = 116

            # shadow and main card
            rounded_rect(card_canvas, 8, 12, w - 2, h + 4, r=22, fill="#D7E1EA", outline="")
            rounded_rect(card_canvas, 2, 4, w - 8, h - 2, r=22, fill=Theme.WHITE, outline="#C8D6E2", width=1)

            # top accent line and icon badge
            rounded_rect(card_canvas, 2, 4, w - 8, 12, r=6, fill=color, outline="")
            card_canvas.create_oval(20, 34, 78, 92, fill=color, outline="")
            card_canvas.create_text(49, 63, text=icon, fill=Theme.WHITE, font=("Segoe UI Emoji", 21, "bold"))

            # value and title
            card_canvas.create_text(92, 48, text=value, anchor="w", fill=Theme.NAVY_DARK, font=("Segoe UI", 20, "bold"))
            card_canvas.create_text(92, 78, text=title, anchor="w", fill=Theme.BLUE, font=("Segoe UI", 9, "bold"))

            # small decorative dot for premium look
            card_canvas.create_oval(w - 32, 28, w - 22, 38, fill="#EAF2F8", outline="")

        card_canvas.bind("<Configure>", draw_card)

    # --------------------------------------------------------
    # INVENTORY PAGE
    # --------------------------------------------------------

    def show_inventory(self):
        self.clear_content()
        self.page_title("Medicine Inventory", "Search, filter, update and monitor complete medicine records.")

        search_frame = tk.Frame(self.content, bg=Theme.BG)
        search_frame.pack(fill="x", pady=(0, 12))

        tk.Label(search_frame, text="🔍 Search:", bg=Theme.BG, fg=Theme.NAVY, font=("Segoe UI", 10, "bold")).pack(side="left")

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 11), width=24, bd=1, relief="solid")
        search_entry.pack(side="left", padx=8, ipady=6)
        search_entry.bind("<KeyRelease>", lambda event: self.load_inventory())

        tk.Label(search_frame, text="Batch No:", bg=Theme.BG, fg=Theme.NAVY, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 5))

        self.batch_search_var = tk.StringVar()
        batch_entry = tk.Entry(search_frame, textvariable=self.batch_search_var, font=("Segoe UI", 11), width=15, bd=1, relief="solid")
        batch_entry.pack(side="left", padx=(0, 8), ipady=6)
        batch_entry.bind("<KeyRelease>", lambda event: self.load_inventory())

        tk.Label(search_frame, text="Status:", bg=Theme.BG, fg=Theme.NAVY, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(10, 5))

        self.status_var = tk.StringVar(value="All")
        status = ttk.Combobox(search_frame, textvariable=self.status_var, values=["All", "Expired", "Near Expiry", "Low Stock", "Safe"], state="readonly", width=15)
        status.pack(side="left", ipady=4)
        status.bind("<<ComboboxSelected>>", lambda event: self.load_inventory())

        self.button(search_frame, "Export CSV", self.export_inventory_csv, bg=Theme.TEAL, width=12).pack(side="right", padx=5)
        self.button(search_frame, "Refresh", self.load_inventory, bg=Theme.GRAY, width=10).pack(side="right", padx=5)
        self.button(search_frame, "Delete Selected", self.delete_selected_medicine, bg=Theme.RED, width=15).pack(side="right", padx=5)

        panel = tk.Frame(self.content, bg=Theme.WHITE, bd=1, relief="solid")
        panel.pack(fill="both", expand=True)

        columns = ("ID", "Name", "Category", "Batch", "Company", "Supplier", "Qty", "Cost", "Sell", "Expiry", "Status")
        self.inventory_table = ttk.Treeview(panel, columns=columns, show="headings", height=14)

        widths = {
            "ID": 55, "Name": 180, "Category": 105, "Batch": 95, "Company": 150,
            "Supplier": 145, "Qty": 70, "Cost": 95, "Sell": 95, "Expiry": 110, "Status": 115
        }

        for col in columns:
            self.inventory_table.heading(col, text=col)
            anchor = "center" if col in ("ID", "Qty", "Cost", "Sell", "Expiry", "Status") else "w"
            self.inventory_table.column(col, width=widths[col], anchor=anchor)

        yscroll = ttk.Scrollbar(panel, orient="vertical", command=self.inventory_table.yview)
        xscroll = ttk.Scrollbar(panel, orient="horizontal", command=self.inventory_table.xview)
        self.inventory_table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.inventory_table.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        yscroll.grid(row=0, column=1, sticky="ns", pady=12)
        xscroll.grid(row=1, column=0, sticky="ew", padx=(12, 0))

        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        self.inventory_table.tag_configure("expired", background=Theme.RED_ROW, foreground=Theme.RED)
        self.inventory_table.tag_configure("near", background=Theme.ORANGE_ROW, foreground=Theme.ORANGE)
        self.inventory_table.tag_configure("low", background=Theme.YELLOW_ROW, foreground=Theme.ORANGE)
        self.inventory_table.tag_configure("safe", background=Theme.WHITE, foreground=Theme.TEXT)

        self.inventory_table.bind("<<TreeviewSelect>>", self.select_inventory_row)
        self.inventory_table.bind("<Double-1>", lambda event: self.open_edit_medicine())

        actions = tk.Frame(self.content, bg=Theme.BG)
        actions.pack(fill="x", pady=(12, 0))

        self.button(actions, "Edit Selected", self.open_edit_medicine, bg=Theme.NAVY, width=14).pack(side="left", padx=5)
        self.button(actions, "Delete Selected", self.delete_selected_medicine, bg=Theme.RED, width=15).pack(side="left", padx=5)
        self.button(actions, "Sell Selected", self.open_sell_medicine, bg=Theme.PURPLE, width=14).pack(side="left", padx=5)
        self.button(actions, "Add Stock", self.open_add_stock, bg=Theme.TEAL, width=14).pack(side="left", padx=5)

        self.load_inventory()

    def get_row_status(self, row):
        today = date.today()
        near_date = today + timedelta(days=NEAR_EXPIRY_DAYS)
        expiry = parse_date(row["expiry_date"])

        if expiry and expiry < today:
            return "Expired", "expired"
        if expiry and today <= expiry <= near_date:
            return "Near Expiry", "near"
        if row["quantity"] <= LOW_STOCK_LIMIT:
            return "Low Stock", "low"
        return "Safe", "safe"

    def load_inventory(self):
        if not hasattr(self, "inventory_table") or not self.inventory_table.winfo_exists():
            return

        for item in self.inventory_table.get_children():
            self.inventory_table.delete(item)

        keyword = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        batch_keyword = self.batch_search_var.get().strip() if hasattr(self, "batch_search_var") else ""
        status_filter = self.status_var.get() if hasattr(self, "status_var") else "All"

        for row in self.db.get_medicines(keyword, status_filter, batch_keyword):
            status, tag = self.get_row_status(row)
            self.inventory_table.insert("", "end", values=(
                row["id"], row["name"], row["category"], row["batch_no"], row["company"],
                row["supplier"], row["quantity"], money(row["cost_price"]),
                money(row["selling_price"]), row["expiry_date"], status
            ), tags=(tag,))

    def select_inventory_row(self, event=None):
        selected = self.inventory_table.focus()
        if selected:
            values = self.inventory_table.item(selected, "values")
            if values:
                self.selected_id = safe_int(values[0])

    def get_selected_id(self):
        if hasattr(self, "inventory_table") and self.inventory_table.winfo_exists():
            self.select_inventory_row()
        if not self.selected_id:
            messagebox.showwarning("No Selection", "Please select a medicine from inventory.")
            return None
        return self.selected_id

    # --------------------------------------------------------
    # MEDICINE FORMS
    # --------------------------------------------------------

    def open_add_medicine(self):
        self.medicine_form("Add Medicine", "add")

    def open_edit_medicine(self):
        med_id = self.get_selected_id()
        if med_id:
            self.medicine_form("Edit Medicine", "edit", med_id)

    def medicine_form(self, title, mode, med_id=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=Theme.BG)
        center_window(win, 760, 610)
        win.resizable(False, False)

        header = tk.Frame(win, bg=Theme.NAVY, height=62)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=title,
            bg=Theme.NAVY,
            fg=Theme.WHITE,
            font=("Segoe UI", 20, "bold")
        ).pack(side="left", padx=24)

        tk.Label(
            header,
            text="Stock • Supplier • Expiry",
            bg=Theme.NAVY,
            fg="#DDEFFF",
            font=("Segoe UI", 10)
        ).pack(side="right", padx=24)

        card = tk.Frame(win, bg=Theme.WHITE, bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=20, pady=18)

        tk.Label(
            card,
            text="Medicine Information",
            bg=Theme.WHITE,
            fg=Theme.NAVY,
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(14, 6))

        entries = {}

        def lbl(row, col, text):
            tk.Label(
                card,
                text=text,
                bg=Theme.WHITE,
                fg=Theme.TEXT,
                font=("Segoe UI", 9, "bold")
            ).grid(row=row, column=col, sticky="w", padx=18, pady=(6, 2))

        def ent(row, col, key, default=""):
            box = tk.Entry(
                card,
                font=("Segoe UI", 10),
                width=26,
                bd=1,
                relief="solid",
                highlightthickness=1,
                highlightbackground=Theme.BORDER,
                highlightcolor=Theme.BLUE
            )
            box.grid(row=row, column=col, sticky="w", padx=18, ipady=5)
            if default:
                box.insert(0, default)
            entries[key] = box
            return box

        # Left column
        lbl(1, 0, "Medicine Name *")
        ent(2, 0, "name")

        lbl(3, 0, "Category *")
        category = ttk.Combobox(
            card,
            values=["Tablet", "Capsule", "Syrup", "Injection", "Ointment", "Drops", "Other"],
            state="readonly",
            width=24,
            font=("Segoe UI", 10)
        )
        category.current(0)
        category.grid(row=4, column=0, sticky="w", padx=18, ipady=4)
        entries["category"] = category

        lbl(5, 0, "Batch Number")
        ent(6, 0, "batch_no")

        lbl(7, 0, "Company Name")
        ent(8, 0, "company")

        # Right column
        lbl(1, 1, "Supplier Name")
        ent(2, 1, "supplier", "Local Supplier")

        lbl(3, 1, "Quantity *")
        ent(4, 1, "quantity")

        lbl(5, 1, "Cost Price")
        ent(6, 1, "cost_price")

        lbl(7, 1, "Selling Price")
        ent(8, 1, "selling_price")

        # Expiry date dropdowns
        # This replaces the DateEntry calendar popup because some systems have
        # month/year focus issues in tkcalendar. The admin selects Day, Month,
        # and Year, and the system automatically converts it to YYYY-MM-DD.
        sep = tk.Frame(card, bg="#E4E7EC", height=1)
        sep.grid(row=9, column=0, columnspan=2, sticky="ew", padx=18, pady=(16, 8))

        lbl(10, 0, "Expiry Date *")

        expiry_frame = tk.Frame(card, bg=Theme.WHITE)
        expiry_frame.grid(row=11, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 4))

        default_expiry = date.today() + timedelta(days=365)
        month_values = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        year_values = [str(y) for y in range(date.today().year - 10, date.today().year + 11)]

        day_var = tk.StringVar(value=f"{default_expiry.day:02d}")
        month_var = tk.StringVar(value=month_values[default_expiry.month - 1])
        year_var = tk.StringVar(value=str(default_expiry.year))

        day_combo = ttk.Combobox(
            expiry_frame,
            textvariable=day_var,
            values=[f"{d:02d}" for d in range(1, 32)],
            state="readonly",
            width=5,
            font=("Segoe UI", 9)
        )
        day_combo.pack(side="left", padx=(0, 5), ipady=2)

        month_combo = ttk.Combobox(
            expiry_frame,
            textvariable=month_var,
            values=month_values,
            state="readonly",
            width=11,
            font=("Segoe UI", 9)
        )
        month_combo.pack(side="left", padx=(0, 5), ipady=2)

        year_combo = ttk.Combobox(
            expiry_frame,
            textvariable=year_var,
            values=year_values,
            state="readonly",
            width=7,
            font=("Segoe UI", 9)
        )
        year_combo.pack(side="left", ipady=2)

        def update_day_options(event=None):
            selected_year = safe_int(year_var.get(), default_expiry.year)
            selected_month = month_values.index(month_var.get()) + 1 if month_var.get() in month_values else default_expiry.month
            last_day = calendar.monthrange(selected_year, selected_month)[1]
            current_day = safe_int(day_var.get(), 1)

            day_values = [f"{d:02d}" for d in range(1, last_day + 1)]
            day_combo.config(values=day_values)

            if current_day > last_day:
                day_var.set(f"{last_day:02d}")
            elif current_day < 1:
                day_var.set("01")

        month_combo.bind("<<ComboboxSelected>>", update_day_options)
        year_combo.bind("<<ComboboxSelected>>", update_day_options)
        update_day_options()

        entries["expiry_day"] = day_var
        entries["expiry_month"] = month_var
        entries["expiry_year"] = year_var

        if mode == "edit":
            med = self.db.get_medicine(med_id)
            if not med:
                messagebox.showerror("Error", "Medicine not found.")
                win.destroy()
                return

            for key in ["name", "batch_no", "company", "supplier", "quantity", "cost_price", "selling_price"]:
                entries[key].delete(0, "end")
                entries[key].insert(0, med[key])

            category_values = ["Tablet", "Capsule", "Syrup", "Injection", "Ointment", "Drops", "Other"]
            entries["category"].set(med["category"] if med["category"] in category_values else "Other")

            exp = parse_date(med["expiry_date"])
            if exp:
                entries["expiry_day"].set(f"{exp.day:02d}")
                entries["expiry_month"].set(month_values[exp.month - 1])
                entries["expiry_year"].set(str(exp.year))
                update_day_options()

        def get_expiry():
            try:
                selected_day = safe_int(entries["expiry_day"].get(), -1)
                selected_month = month_values.index(entries["expiry_month"].get()) + 1 if entries["expiry_month"].get() in month_values else -1
                selected_year = safe_int(entries["expiry_year"].get(), -1)
                return date(selected_year, selected_month, selected_day).strftime(DATE_FORMAT)
            except Exception:
                return ""

        def save():
            name_text = entries["name"].get().strip()
            category_text = entries["category"].get().strip()
            batch_text = entries["batch_no"].get().strip()
            company_text = entries["company"].get().strip()
            supplier_text = entries["supplier"].get().strip()
            quantity_text = entries["quantity"].get().strip()
            cost_text = entries["cost_price"].get().strip()
            selling_text = entries["selling_price"].get().strip()
            expiry_text = get_expiry()

            # Required-field validation: no important box should be empty.
            if not name_text:
                messagebox.showwarning("Missing", "Medicine name is required.")
                return
            if not category_text:
                messagebox.showwarning("Missing", "Category is required.")
                return
            if not batch_text:
                messagebox.showwarning("Missing", "Batch number is required.")
                return
            if not company_text:
                messagebox.showwarning("Missing", "Company name is required.")
                return
            if not supplier_text:
                messagebox.showwarning("Missing", "Supplier name is required.")
                return
            if not quantity_text:
                messagebox.showwarning("Missing", "Quantity is required.")
                return
            if not cost_text:
                messagebox.showwarning("Missing", "Cost price is required.")
                return
            if not selling_text:
                messagebox.showwarning("Missing", "Selling price is required.")
                return
            if parse_date(expiry_text) is None:
                messagebox.showwarning("Invalid Date", "Please select a valid expiry date.")
                return

            # Number validation: quantity and prices should be proper positive values.
            if not quantity_text.isdigit():
                messagebox.showwarning("Invalid", "Quantity must be a number.")
                return

            data = {
                "name": name_text,
                "category": category_text,
                "batch_no": batch_text,
                "company": company_text,
                "supplier": supplier_text,
                "quantity": safe_int(quantity_text, -1),
                "cost_price": safe_float(cost_text, -1),
                "selling_price": safe_float(selling_text, -1),
                "expiry_date": expiry_text
            }

            if data["quantity"] <= 0:
                messagebox.showwarning("Invalid", "Quantity must be greater than zero.")
                return
            if data["cost_price"] <= 0:
                messagebox.showwarning("Invalid", "Cost price must be greater than zero.")
                return
            if data["selling_price"] <= 0:
                messagebox.showwarning("Invalid", "Selling price must be greater than zero.")
                return
            if data["selling_price"] <= data["cost_price"]:
                messagebox.showwarning("Invalid", "Selling price must be greater than cost price to get profit.")
                return

            if mode == "add":
                ok, msg = self.db.add_medicine(data)
            else:
                ok, msg = self.db.update_medicine(med_id, data)

            if not ok:
                messagebox.showwarning("Duplicate Batch Found", msg)
                return

            messagebox.showinfo("Success", msg)
            win.destroy()
            self.refresh_all()

        actions = tk.Frame(card, bg=Theme.WHITE)
        actions.grid(row=12, column=0, columnspan=2, pady=(28, 16))

        self.button(
            actions,
            "SAVE MEDICINE" if mode == "add" else "UPDATE MEDICINE",
            save,
            bg=Theme.NAVY,
            width=20
        ).pack(side="left", padx=8)

        self.button(
            actions,
            "CANCEL",
            win.destroy,
            bg=Theme.GRAY,
            width=12
        ).pack(side="left", padx=8)

    def delete_selected_medicine(self):
        med_id = self.get_selected_id()
        if not med_id:
            return

        med = self.db.get_medicine(med_id)
        name = med["name"] if med else "selected medicine"

        if messagebox.askyesno("Confirm Delete", f"Delete {name}?"):
            self.db.delete_medicine(med_id)
            self.selected_id = None
            messagebox.showinfo("Deleted", "Medicine deleted successfully.")
            self.refresh_all()

    # --------------------------------------------------------
    # STOCK AND SALES
    # --------------------------------------------------------

    def open_add_stock(self):
        """Add stock for an existing medicine.
        Extra option added: if no inventory medicine is selected, or if the admin wants,
        they can open Add New Medicine directly from this Add Stock option.
        """

        def open_new_medicine_from_stock(current_win=None):
            if current_win is not None and current_win.winfo_exists():
                current_win.destroy()
            self.medicine_form("Add New Medicine from Add Stock", "add")

        # Try to read selected medicine from inventory, if inventory page is open.
        if hasattr(self, "inventory_table") and self.inventory_table.winfo_exists():
            self.select_inventory_row()

        med_id = self.selected_id

        # If no medicine is selected, give an extra option to add a new medicine.
        if not med_id:
            choice = messagebox.askyesno(
                "Add Stock",
                "No medicine is selected from inventory.\n\n"
                "Do you want to add a new medicine from Add Stock?"
            )
            if choice:
                open_new_medicine_from_stock()
            return

        med = self.db.get_medicine(med_id)
        if not med:
            choice = messagebox.askyesno(
                "Add Stock",
                "Selected medicine was not found.\n\n"
                "Do you want to add a new medicine from Add Stock?"
            )
            if choice:
                open_new_medicine_from_stock()
            return

        expiry = parse_date(med["expiry_date"])
        if expiry is None:
            messagebox.showerror(
                "Invalid Expiry Date",
                "This medicine has an invalid expiry date. Stock cannot be added."
            )
            return

        if expiry < date.today():
            messagebox.showerror(
                "Expired Medicine",
                "This medicine is already expired. Stock cannot be added."
            )
            return

        win = tk.Toplevel(self.root)
        win.title("Add Stock")
        win.configure(bg=Theme.WHITE)
        center_window(win, 460, 500)
        win.resizable(False, False)

        tk.Label(win, text="Add Stock", bg=Theme.WHITE, fg=Theme.NAVY, font=("Segoe UI", 22, "bold")).pack(pady=(24, 5))
        tk.Label(win, text=med["name"], bg=Theme.WHITE, fg=Theme.MUTED, font=("Segoe UI", 11)).pack(pady=(0, 6))

        tk.Label(
            win,
            text="Existing medicine selected from inventory",
            bg=Theme.WHITE,
            fg=Theme.BLUE,
            font=("Segoe UI", 9, "bold")
        ).pack(pady=(0, 14))

        form = tk.Frame(win, bg=Theme.WHITE)
        form.pack()

        tk.Label(form, text="Quantity to Add", bg=Theme.WHITE, fg=Theme.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 3))
        qty_entry = self.entry(form, width=30)
        qty_entry.pack(ipady=7)

        tk.Label(form, text="Cost Price", bg=Theme.WHITE, fg=Theme.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 3))
        cost_entry = self.entry(form, width=30)
        cost_entry.pack(ipady=7)
        cost_entry.insert(0, str(med["cost_price"]))

        tk.Label(form, text="Supplier", bg=Theme.WHITE, fg=Theme.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 3))
        supplier_entry = self.entry(form, width=30)
        supplier_entry.pack(ipady=7)
        supplier_entry.insert(0, med["supplier"] or "Local Supplier")

        def save():
            qty_text = qty_entry.get().strip()
            cost_text = cost_entry.get().strip()
            supplier = supplier_entry.get().strip()

            if not qty_text:
                messagebox.showwarning("Missing", "Quantity to add is required.")
                return
            if not cost_text:
                messagebox.showwarning("Missing", "Cost price is required.")
                return
            if not supplier:
                messagebox.showwarning("Missing", "Supplier name is required.")
                return
            if not qty_text.isdigit():
                messagebox.showwarning("Invalid", "Quantity must be a number.")
                return

            qty = safe_int(qty_text, -1)
            cost = safe_float(cost_text, -1)

            if qty <= 0:
                messagebox.showwarning("Invalid", "Quantity must be greater than zero.")
                return
            if cost <= 0:
                messagebox.showwarning("Invalid", "Cost price must be greater than zero.")
                return
            if cost >= float(med["selling_price"]):
                messagebox.showwarning(
                    "Invalid",
                    "Cost price must be less than selling price to maintain profit."
                )
                return

            ok = self.db.add_stock(med_id, qty, cost, supplier)
            if not ok:
                messagebox.showerror(
                    "Stock Not Added",
                    "Stock cannot be added for this medicine. Please check expiry date and medicine details."
                )
                return

            messagebox.showinfo("Success", "Stock added successfully.")
            win.destroy()
            self.refresh_all()

        btn_frame = tk.Frame(win, bg=Theme.WHITE)
        btn_frame.pack(pady=22)

        self.button(btn_frame, "ADD STOCK", save, bg=Theme.TEAL, width=18).pack(side="left", padx=6)
        self.button(
            btn_frame,
            "ADD NEW MEDICINE",
            lambda: open_new_medicine_from_stock(win),
            bg=Theme.NAVY,
            width=18
        ).pack(side="left", padx=6)

    def open_sell_medicine(self):
        med_id = self.get_selected_id()
        if not med_id:
            return

        med = self.db.get_medicine(med_id)
        if not med:
            return

        # Instant safety check: do not even open the Sell Medicine window
        # if the selected medicine is expired or has an invalid expiry date.
        expiry = parse_date(med["expiry_date"])

        if expiry is None:
            messagebox.showerror(
                "Invalid Expiry Date",
                "This medicine has an invalid expiry date. We cannot sell it."
            )
            return

        if expiry < date.today():
            messagebox.showerror(
                "Expired Medicine",
                "We cannot sell this medicine because it is already expired."
            )
            return

        win = tk.Toplevel(self.root)
        win.title("Sell Medicine")
        win.configure(bg=Theme.WHITE)
        center_window(win, 490, 600)
        win.resizable(False, False)

        tk.Label(win, text="Sell Medicine", bg=Theme.WHITE, fg=Theme.NAVY, font=("Segoe UI", 22, "bold")).pack(pady=(24, 5))
        tk.Label(win, text=f"{med['name']} | Available: {med['quantity']} | Price: {money(med['selling_price'])}", bg=Theme.WHITE, fg=Theme.MUTED, font=("Segoe UI", 11)).pack(pady=(0, 18))

        form = tk.Frame(win, bg=Theme.WHITE)
        form.pack()

        tk.Label(form, text="Quantity", bg=Theme.WHITE, fg=Theme.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 3))
        qty_entry = self.entry(form, width=34)
        qty_entry.pack(ipady=7)
        qty_entry.insert(0, "1")

        tk.Label(form, text="Customer Name", bg=Theme.WHITE, fg=Theme.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 3))
        customer_entry = self.entry(form, width=34)
        customer_entry.pack(ipady=7)

        tk.Label(form, text="Payment Method", bg=Theme.WHITE, fg=Theme.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 3))
        payment = ttk.Combobox(form, values=["Cash", "UPI", "Card"], state="readonly", width=32, font=("Segoe UI", 10))
        payment.current(0)
        payment.pack(ipady=5)

        tk.Label(form, text="UPI/Card Reference No.", bg=Theme.WHITE, fg=Theme.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 3))
        ref_entry = self.entry(form, width=34)
        ref_entry.pack(ipady=7)

        help_label = tk.Label(
            form,
            text="For Cash, reference number can be left blank.",
            bg=Theme.WHITE,
            fg=Theme.MUTED,
            font=("Segoe UI", 9)
        )
        help_label.pack(anchor="w", pady=(4, 0))

        total_label = tk.Label(win, text=f"Total: {money(med['selling_price'])}", bg=Theme.WHITE, fg=Theme.GREEN, font=("Segoe UI", 15, "bold"))
        total_label.pack(pady=(18, 0))

        def update_total(event=None):
            qty = safe_int(qty_entry.get(), 0)
            total_label.config(text=f"Total: {money(qty * med['selling_price'])}")

        qty_entry.bind("<KeyRelease>", update_total)

        def on_payment_change(event=None):
            if payment.get() == "Cash":
                help_label.config(text="For Cash, reference number can be left blank.")
            elif payment.get() == "UPI":
                help_label.config(text="Enter UPI transaction ID, for example: UPI123456.")
            else:
                help_label.config(text="Enter card approval/reference number.")

        payment.bind("<<ComboboxSelected>>", on_payment_change)

        def complete_sale():
            qty_text = qty_entry.get().strip()
            customer_name = customer_entry.get().strip()
            pay_method = payment.get().strip()
            ref_no = ref_entry.get().strip()

            # Re-read latest medicine details before sale.
            # This prevents selling with old stock data if inventory was updated.
            latest_med = self.db.get_medicine(med_id)
            if not latest_med:
                messagebox.showerror("Medicine Not Found", "This medicine record is no longer available.")
                return

            latest_expiry = parse_date(latest_med["expiry_date"])
            if latest_expiry is None:
                messagebox.showerror("Invalid Expiry Date", "This medicine has an invalid expiry date. Selling is not allowed.")
                return
            if latest_expiry < date.today():
                messagebox.showerror("Expired Medicine", "This medicine is expired. Selling is not allowed.")
                return

            if not qty_text:
                messagebox.showwarning("Missing", "Quantity is required.")
                return
            if not qty_text.isdigit():
                messagebox.showwarning("Invalid", "Quantity must contain numbers only.")
                return

            qty = safe_int(qty_text, -1)
            if qty <= 0:
                messagebox.showwarning("Invalid", "Quantity must be greater than zero.")
                return
            if latest_med["quantity"] <= 0:
                messagebox.showwarning("Out of Stock", "This medicine is out of stock.")
                return
            if qty > latest_med["quantity"]:
                messagebox.showwarning("Insufficient Stock", f"Only {latest_med['quantity']} units are available. Please enter a lower quantity.")
                return

            if latest_med["selling_price"] <= 0:
                messagebox.showwarning("Invalid Price", "Selling price must be greater than zero.")
                return

            if not customer_name:
                messagebox.showwarning("Customer Name Required", "Please enter customer name.")
                return
            if len(customer_name) < 2:
                messagebox.showwarning("Invalid Customer Name", "Customer name must have at least 2 characters.")
                return
            if not all(ch.isalpha() or ch.isspace() or ch == "." for ch in customer_name):
                messagebox.showwarning("Invalid Customer Name", "Customer name should contain only letters, spaces, or dot.")
                return

            if pay_method not in ("Cash", "UPI", "Card"):
                messagebox.showwarning("Payment Method Required", "Please select a valid payment method.")
                return
            if pay_method == "Cash" and ref_no:
                messagebox.showwarning("Invalid Reference", "Cash payment does not need UPI/Card reference number.")
                return
            if pay_method in ("UPI", "Card") and not ref_no:
                messagebox.showwarning("Payment Reference Required", f"Please enter {pay_method} reference/transaction number.")
                return
            if ref_no and len(ref_no) < 4:
                messagebox.showwarning("Invalid Reference", "Reference/transaction number must have at least 4 characters.")
                return
            if ref_no and not all(ch.isalnum() or ch in "-/" for ch in ref_no):
                messagebox.showwarning("Invalid Reference", "Reference number should contain only letters, numbers, hyphen or slash.")
                return

            total_amount = qty * latest_med["selling_price"]

            ok, msg = self.db.sell_medicine(med_id, qty, customer_name, pay_method, ref_no)
            if ok:
                messagebox.showinfo("Success", msg)
                win.destroy()
                self.show_bill_receipt(
                    medicine_name=latest_med["name"],
                    batch_no=latest_med["batch_no"],
                    qty=qty,
                    unit_price=latest_med["selling_price"],
                    total=total_amount,
                    customer=customer_name,
                    payment_method=pay_method,
                    reference_no=ref_no
                )
                self.refresh_all()
            else:
                messagebox.showerror("Sale Error", msg)

        self.button(win, "COMPLETE SALE", complete_sale, bg=Theme.GRAY, width=22).pack(pady=25)

    def show_bill_receipt(self, medicine_name, batch_no, qty, unit_price, total, customer, payment_method, reference_no):
        """Display a simple pharmacy bill receipt after successful sale."""
        receipt_no = datetime.now().strftime("BILL%Y%m%d%H%M%S")
        sale_time = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
        customer_display = customer if customer else "Walk-in Customer"
        reference_display = reference_no if reference_no else "-"

        receipt_text = f"""
LOCAL PHARMACY
Inventory & Expiry Management System
----------------------------------------
Receipt No : {receipt_no}
Date/Time  : {sale_time}
Customer   : {customer_display}
----------------------------------------
Medicine   : {medicine_name}
Batch No   : {batch_no}
Quantity   : {qty}
Unit Price : {money(unit_price)}
----------------------------------------
Total      : {money(total)}
Payment    : {payment_method}
Reference  : {reference_display}
----------------------------------------
Thank you. Please keep this receipt.
""".strip()

        win = tk.Toplevel(self.root)
        win.title("Bill Receipt")
        win.configure(bg=Theme.BG)
        center_window(win, 520, 610)
        win.resizable(False, False)

        header = tk.Frame(win, bg=Theme.NAVY, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🧾 Bill Receipt", bg=Theme.NAVY, fg=Theme.WHITE, font=("Segoe UI", 20, "bold")).pack(side="left", padx=22)
        tk.Label(header, text=receipt_no, bg=Theme.NAVY, fg="#DDEFFF", font=("Segoe UI", 10, "bold")).pack(side="right", padx=22)

        card = tk.Frame(win, bg=Theme.WHITE, bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=20, pady=18)

        receipt_box = tk.Text(
            card,
            font=("Consolas", 11),
            bg="#F7FAFC",
            fg=Theme.TEXT,
            bd=0,
            relief="flat",
            height=22,
            width=48
        )
        receipt_box.pack(fill="both", expand=True, padx=14, pady=14)
        receipt_box.insert("1.0", receipt_text)
        receipt_box.config(state="disabled")

        actions = tk.Frame(win, bg=Theme.BG)
        actions.pack(fill="x", padx=20, pady=(0, 18))

        def save_receipt():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text File", "*.txt")],
                initialfile=f"{receipt_no}.txt",
                title="Save Bill Receipt"
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write(receipt_text)
            messagebox.showinfo("Saved", "Bill receipt saved successfully.")

        self.button(actions, "SAVE RECEIPT", save_receipt, bg=Theme.TEAL, width=16).pack(side="left")
        self.button(actions, "CLOSE", win.destroy, bg=Theme.NAVY, width=12).pack(side="right")

    # --------------------------------------------------------
    # ANALYTICS
    # --------------------------------------------------------

    def show_analytics(self):
        self.clear_content()
        self.page_title("Graphs and Analytics", "Visual analysis of stock, expiry status and sales performance.")

        options = tk.Frame(self.content, bg=Theme.BG)
        options.pack(fill="x", pady=(0, 15))

        self.button(options, "Stock Quantity Bar Chart", self.chart_stock_bar, bg=Theme.NAVY, width=22).pack(side="left", padx=5)
        self.button(options, "Expiry Status Pie Chart", self.chart_status_pie, bg=Theme.ORANGE, width=22).pack(side="left", padx=5)
        self.button(options, "Purchase Cost Trend", self.chart_purchase_cost_trend, bg=Theme.GRAY, width=22).pack(side="left", padx=5)
        self.button(options, "Top Selling Medicines", self.chart_top_selling_medicines, bg=Theme.BLUE, width=20).pack(side="left", padx=5)
        self.button(options, "Profit Analytics", self.show_profit_analytics, bg=Theme.GREEN, width=18).pack(side="left", padx=5)

        panel = tk.Frame(self.content, bg=Theme.WHITE, bd=1, relief="solid")
        panel.pack(fill="both", expand=True, padx=2, pady=2)

        tk.Label(
            panel,
            text="Select a graph option above to view analytics.",
            bg=Theme.WHITE,
            fg=Theme.MUTED,
            font=("Segoe UI", 15, "bold")
        ).pack(expand=True)

    def chart_window(self, title, fig):
        if FigureCanvasTkAgg is None:
            messagebox.showwarning("Missing Package", "Install matplotlib.")
            return

        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=Theme.WHITE)
        center_window(win, 900, 620)

        tk.Label(win, text=title, bg=Theme.WHITE, fg=Theme.NAVY, font=("Segoe UI", 20, "bold")).pack(pady=12)

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=15)

    def chart_stock_bar(self):
        if plt is None:
            messagebox.showwarning("Missing Package", "Install matplotlib.")
            return

        rows = self.db.get_medicines()
        if not rows:
            messagebox.showwarning("No Data", "No medicines available.")
            return

        names = [r["name"] for r in rows]
        qty = [r["quantity"] for r in rows]

        fig = plt.Figure(figsize=(9, 5.2), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(names, qty, color=Theme.BLUE)
        ax.set_title("Medicine Stock Quantity", color=Theme.NAVY, fontsize=14, fontweight="bold", pad=14)
        ax.set_xlabel("Medicine", color=Theme.TEXT, fontweight="bold")
        ax.set_ylabel("Quantity", color=Theme.TEXT, fontweight="bold")
        ax.tick_params(axis="x", rotation=35, labelsize=9)
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()

        self.chart_window("Stock Quantity Bar Chart", fig)

    def chart_status_pie(self):
        if plt is None:
            messagebox.showwarning("Missing Package", "Install matplotlib.")
            return

        rows = self.db.get_medicines()
        if not rows:
            messagebox.showwarning("No Data", "No data available.")
            return

        counts = {
            "Safe": 0,
            "Expired": 0,
            "Near Expiry": 0,
            "Low Stock": 0
        }

        # Count every medicine only once using the same status logic used in Inventory
        for row in rows:
            status, tag = self.get_row_status(row)
            counts[status] += 1

        color_map = {
            "Safe": Theme.GREEN,
            "Expired": Theme.RED,
            "Near Expiry": Theme.ORANGE,
            "Low Stock": Theme.BLUE
        }

        labels = []
        values = []
        colors = []

        for status in ["Safe", "Expired", "Near Expiry", "Low Stock"]:
            if counts[status] > 0:
                labels.append(status)
                values.append(counts[status])
                colors.append(color_map[status])

        if sum(values) == 0:
            messagebox.showwarning("No Data", "No data available.")
            return

        fig = plt.Figure(figsize=(6.5, 5.3), dpi=100)
        ax = fig.add_subplot(111)
        ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=colors,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
            textprops={"color": Theme.NAVY, "fontsize": 10}
        )
        ax.set_title("Medicine Status Distribution", color=Theme.NAVY, fontsize=13, fontweight="bold")
        fig.tight_layout()

        self.chart_window("Expiry Status Pie Chart", fig)

    def chart_purchase_cost_trend(self):
        if plt is None:
            messagebox.showwarning("Missing Package", "Install matplotlib.")
            return

        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT strftime('%Y-%m', purchase_date) AS month, SUM(total) AS total
                FROM purchases
                GROUP BY strftime('%Y-%m', purchase_date)
                ORDER BY month
            """).fetchall()

        if not rows:
            messagebox.showwarning("No Data", "No purchase data available for purchase cost trend.")
            return

        months = [row["month"] for row in rows]
        totals = [row["total"] for row in rows]

        fig = plt.Figure(figsize=(9, 5.2), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(months, totals, marker="o", linewidth=2.5, color=Theme.GREEN)
        ax.set_title("Purchase Cost Trend", color=Theme.NAVY, fontsize=14, fontweight="bold", pad=14)
        ax.set_xlabel("Month", color=Theme.TEXT, fontweight="bold")
        ax.set_ylabel("Purchase Cost", color=Theme.TEXT, fontweight="bold")
        ax.tick_params(axis="x", rotation=35, labelsize=9)
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()

        self.chart_window("Purchase Cost Trend Chart", fig)

    def chart_top_selling_medicines(self):
        if plt is None:
            messagebox.showwarning("Missing Package", "Install matplotlib.")
            return

        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT medicine_name, SUM(quantity) AS sold_qty, SUM(total) AS revenue
                FROM sales
                GROUP BY medicine_name
                ORDER BY sold_qty DESC, revenue DESC
                LIMIT 10
            """).fetchall()

        if not rows:
            messagebox.showwarning("No Sales Data", "No sales data available. Sell medicines first to view top selling medicines.")
            return

        names = [row["medicine_name"] for row in rows]
        qty = [row["sold_qty"] for row in rows]

        fig = plt.Figure(figsize=(9.5, 5.6), dpi=100)
        ax = fig.add_subplot(111)

        # Vertical chart: medicine names at the bottom, sold quantity at the side.
        ax.bar(names, qty, color=Theme.BLUE, width=0.55)
        ax.set_title("Top Selling Medicines", color=Theme.NAVY, fontsize=14, fontweight="bold", pad=14)
        ax.set_xlabel("Medicine", color=Theme.TEXT, fontweight="bold", labelpad=10)
        ax.set_ylabel("Sold Quantity", color=Theme.TEXT, fontweight="bold", labelpad=10)
        ax.tick_params(axis="x", rotation=25, labelsize=9)
        ax.tick_params(axis="y", labelsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # Show quantity number above each bar for a cleaner viva presentation.
        for index, value in enumerate(qty):
            ax.text(index, value + 0.05, str(value), ha="center", va="bottom", color=Theme.NAVY, fontsize=9, fontweight="bold")

        fig.tight_layout()
        self.chart_window("Top Selling Medicines", fig)

    def show_profit_analytics(self):
        with self.db.connect() as conn:
            rows = conn.execute("""
                SELECT 
                    s.medicine_name,
                    SUM(s.quantity) AS sold_qty,
                    SUM(s.total) AS revenue,
                    SUM(s.quantity * IFNULL(m.cost_price, 0)) AS cost
                FROM sales s
                LEFT JOIN medicines m ON s.medicine_id = m.id
                GROUP BY s.medicine_name
                ORDER BY revenue DESC
            """).fetchall()

        if not rows:
            messagebox.showwarning("No Data", "No sales data available.")
            return

        table_rows = []
        total_revenue = 0
        total_cost = 0

        for row in rows:
            revenue = safe_float(row["revenue"])
            cost = safe_float(row["cost"])
            profit = revenue - cost

            total_revenue += revenue
            total_cost += cost

            table_rows.append((row["medicine_name"], row["sold_qty"], money(revenue), money(cost), money(profit)))

        win = self.table_window("Profit Analytics", ("Medicine", "Sold Qty", "Revenue", "Cost", "Profit"), table_rows, (850, 520))

        tk.Label(
            win,
            text=f"Total Revenue: {money(total_revenue)}     Total Cost: {money(total_cost)}     Profit: {money(total_revenue - total_cost)}",
            bg=Theme.WHITE,
            fg=Theme.GREEN,
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 12))

    # --------------------------------------------------------
    # REPORTS
    # --------------------------------------------------------

    def show_reports(self):
        self.clear_content()
        self.page_title("Reports", "View sales, purchases, restock requirements, supplier summary and export reports.")

        actions = tk.Frame(self.content, bg=Theme.BG)
        actions.pack(fill="x", pady=(0, 15))

        self.button(actions, "Sales History", self.show_sales_history, bg=Theme.PURPLE, width=16).pack(side="left", padx=4)
        self.button(actions, "Purchase Records", self.show_purchase_records, bg=Theme.TEAL, width=16).pack(side="left", padx=4)
        self.button(actions, "Restock List", self.show_low_stock_restock_list, bg=Theme.ORANGE, width=14).pack(side="left", padx=4)
        self.button(actions, "Supplier Report", self.show_supplier_wise_purchase_report, bg=Theme.BLUE, width=15).pack(side="left", padx=4)
        self.button(actions, "Export Inventory CSV", self.export_inventory_csv, bg=Theme.NAVY, width=18).pack(side="left", padx=4)
        self.button(actions, "Expired Report", self.export_expired_report, bg=Theme.RED, width=15).pack(side="left", padx=4)

        panel = tk.Frame(self.content, bg=Theme.WHITE, bd=1, relief="solid")
        panel.pack(fill="both", expand=True)

        tk.Label(
            panel,
            text="Reports section helps the pharmacy maintain sales, purchases and inventory records.",
            bg=Theme.WHITE,
            fg=Theme.MUTED,
            font=("Segoe UI", 14, "bold")
        ).pack(expand=True)

    def table_window(self, title, columns, rows, size=(1000, 560)):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=Theme.BG)
        center_window(win, size[0], size[1])

        header = tk.Frame(win, bg=Theme.NAVY, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=title, bg=Theme.NAVY, fg=Theme.WHITE, font=("Segoe UI", 20, "bold")).pack(side="left", padx=22)
        tk.Label(header, text=f"Total Records: {len(rows)}", bg=Theme.NAVY, fg="#DDEFFF", font=("Segoe UI", 10, "bold")).pack(side="right", padx=22)

        wrap = tk.Frame(win, bg=Theme.WHITE, bd=1, relief="solid")
        wrap.pack(fill="both", expand=True, padx=18, pady=18)

        table = ttk.Treeview(wrap, columns=columns, show="headings")
        for col in columns:
            table.heading(col, text=col)
            width = 165 if col in ("Medicine", "Supplier", "Customer") else 130
            table.column(col, width=width, anchor="center")

        table.tag_configure("odd", background=Theme.WHITE, foreground=Theme.TEXT)
        table.tag_configure("even", background="#F7FAFC", foreground=Theme.TEXT)

        yscroll = ttk.Scrollbar(wrap, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=yscroll.set)

        table.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        yscroll.pack(side="right", fill="y", pady=12, padx=(0, 12))

        for index, row in enumerate(rows):
            table.insert("", "end", values=row, tags=("even" if index % 2 == 0 else "odd",))

        return win

    def show_sales_history(self):
        rows = []
        for r in self.db.sales_rows():
            rows.append((
                r["id"], r["medicine_name"], r["quantity"], money(r["selling_price"]),
                money(r["total"]), r["sale_date"], r["customer_name"],
                r["payment_method"], r["transaction_id"]
            ))

        self.table_window(
            "Sales History",
            ("ID", "Medicine", "Qty", "Price", "Total", "Date", "Customer", "Payment", "Reference No."),
            rows,
            (1250, 560)
        )

    def show_purchase_records(self):
        rows = []
        for r in self.db.purchase_rows():
            rows.append((
                r["id"], r["medicine_name"], r["quantity"], money(r["cost_price"]),
                money(r["total"]), r["supplier"], r["purchase_date"]
            ))

        self.table_window("Purchase Records", ("ID", "Medicine", "Qty", "Cost", "Total", "Supplier", "Date"), rows, (1000, 560))

    def show_low_stock_restock_list(self):
        """Show only active low-stock medicines that can be restocked.
        Expired medicines are not shown here because expired batches should not be restocked.
        They are handled separately in the Critical Alerts / Expired Report.
        """
        rows = []
        today = date.today()

        for r in self.db.get_medicines():
            qty = safe_int(r["quantity"])
            expiry = parse_date(r["expiry_date"])

            # Restock list must show only medicines that are still valid.
            # Expired or invalid-expiry records are not active stock.
            if expiry is None or expiry < today:
                continue

            if qty <= LOW_STOCK_LIMIT:
                status, tag = self.get_row_status(r)

                if status == "Near Expiry":
                    suggestion = "Restock only fresh/new batch if needed"
                else:
                    suggestion = "Restock required"

                rows.append((
                    r["id"],
                    r["name"],
                    r["batch_no"],
                    r["category"],
                    qty,
                    LOW_STOCK_LIMIT,
                    r["supplier"],
                    r["expiry_date"],
                    status,
                    suggestion
                ))

        if not rows:
            messagebox.showinfo("Restock List", "No active low-stock medicines found.")
            return

        self.table_window(
            "Active Low Stock Restock List",
            ("ID", "Medicine", "Batch", "Category", "Qty", "Limit", "Supplier", "Expiry", "Status", "Suggestion"),
            rows,
            (1250, 560)
        )

    def show_supplier_wise_purchase_report(self):
        """Show purchase summary grouped by supplier."""
        with self.db.connect() as conn:
            supplier_rows = conn.execute("""
                SELECT 
                    IFNULL(NULLIF(TRIM(supplier), ''), 'Unknown Supplier') AS supplier_name,
                    COUNT(*) AS purchase_entries,
                    COUNT(DISTINCT medicine_name) AS medicine_count,
                    SUM(quantity) AS total_quantity,
                    SUM(total) AS total_amount,
                    MAX(purchase_date) AS last_purchase
                FROM purchases
                GROUP BY IFNULL(NULLIF(TRIM(supplier), ''), 'Unknown Supplier')
                ORDER BY total_amount DESC
            """).fetchall()

        if not supplier_rows:
            messagebox.showinfo("Supplier Report", "No purchase records found.")
            return

        rows = []
        for r in supplier_rows:
            rows.append((
                r["supplier_name"],
                r["purchase_entries"],
                r["medicine_count"],
                r["total_quantity"],
                money(r["total_amount"]),
                r["last_purchase"]
            ))

        self.table_window(
            "Supplier-wise Purchase Report",
            ("Supplier", "Purchase Entries", "Medicines", "Total Qty", "Total Amount", "Last Purchase"),
            rows,
            (1050, 560)
        )

    def export_inventory_csv(self):
        rows = self.db.get_medicines()
        if not rows:
            messagebox.showwarning("No Data", "No inventory data to export.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            title="Save Inventory Report"
        )

        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Name", "Category", "Batch", "Company", "Supplier", "Quantity",
                "Cost Price", "Selling Price", "Expiry Date", "Status", "Stock Value"
            ])

            for row in rows:
                status, tag = self.get_row_status(row)
                writer.writerow([
                    row["id"], row["name"], row["category"], row["batch_no"],
                    row["company"], row["supplier"], row["quantity"],
                    row["cost_price"], row["selling_price"], row["expiry_date"],
                    status, row["quantity"] * row["cost_price"]
                ])

        messagebox.showinfo("Exported", "Inventory CSV report exported successfully.")

    def export_expired_report(self):
        rows = self.db.get_medicines(status="Expired")
        if not rows:
            messagebox.showinfo("No Expired Medicine", "No expired medicines found.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            title="Save Expired Medicine Report"
        )

        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Medicine", "Batch", "Company", "Quantity", "Expiry Date"])
            for row in rows:
                writer.writerow([row["id"], row["name"], row["batch_no"], row["company"], row["quantity"], row["expiry_date"]])

        messagebox.showinfo("Exported", "Expired medicine report exported successfully.")

    # --------------------------------------------------------
    # REFRESH, ALERT, LOGOUT
    # --------------------------------------------------------

    def refresh_all(self):
        try:
            self.show_dashboard()
        except Exception:
            pass

    def show_startup_alerts(self):
        if self.alert_shown:
            return

        stats = self.db.stats()
        if stats["expired"] > 0 or stats["near"] > 0 or stats["low"] > 0:
            self.show_polished_alert(stats)
            self.alert_shown = True

    def show_polished_alert(self, stats):
        alert = tk.Toplevel(self.root)
        alert.title("Pharmacy Alert")
        alert.configure(bg=Theme.BG)
        alert.resizable(False, False)
        center_window(alert, 520, 360)
        alert.transient(self.root)
        alert.grab_set()

        header = tk.Frame(alert, bg=Theme.NAVY, height=74)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="⚠  Important Stock Alert", bg=Theme.NAVY, fg=Theme.WHITE, font=("Segoe UI", 18, "bold")).pack(side="left", padx=22)

        card = tk.Frame(alert, bg=Theme.WHITE, bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            card,
            text="Please check the Critical Alerts section and take action on these items.",
            bg=Theme.WHITE,
            fg=Theme.MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", padx=18, pady=(18, 10))

        summary = tk.Frame(card, bg=Theme.WHITE)
        summary.pack(fill="x", padx=18, pady=8)

        def small_alert(parent, label, value, color):
            box = tk.Frame(parent, bg="#F7FAFC", bd=1, relief="solid", width=145, height=90)
            box.pack(side="left", expand=True, fill="x", padx=5)
            box.pack_propagate(False)
            tk.Label(box, text=str(value), bg="#F7FAFC", fg=color, font=("Segoe UI", 22, "bold")).pack(pady=(12, 0))
            tk.Label(box, text=label, bg="#F7FAFC", fg=Theme.TEXT, font=("Segoe UI", 9, "bold")).pack()

        small_alert(summary, "Expired", stats["expired"], Theme.RED)
        small_alert(summary, "Near Expiry", stats["near"], Theme.ORANGE)
        small_alert(summary, "Low Stock", stats["low"], Theme.GREEN)

        btn_row = tk.Frame(card, bg=Theme.WHITE)
        btn_row.pack(fill="x", padx=18, pady=(18, 12))
        self.button(btn_row, "VIEW DASHBOARD", alert.destroy, bg=Theme.NAVY, width=18).pack(side="right")

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to logout?"):
            self.db.log("LOGOUT", f"{self.current_user} logged out")
            self.current_user = None
            self.selected_id = None
            self.alert_shown = False
            self.show_login()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = PharmacyApp(root)
    root.mainloop()
