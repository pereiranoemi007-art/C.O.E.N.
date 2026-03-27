import tkinter as tk
from tkinter import ttk, messagebox
from database import Database
import os
import re

# PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


class TesoreriaWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Tesorería")
        self.geometry("700x500")
        self.db = Database("coen.db")

        self.crear_tabla()
        self.create_widgets()
        self.load_eventos()

    # ==========================
    # CREAR TABLA
    # ==========================
    def crear_tabla(self):
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS Tesoreria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER,
            motivo TEXT,
            monto REAL
        )
        """)

    # ==========================
    # INTERFAZ
    # ==========================
    def create_widgets(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(expand=True, fill='both')

        # Evento
        top = ttk.Frame(frm)
        top.pack(fill='x', pady=5)

        ttk.Label(top, text="Evento:").pack(side='left')
        self.eventos_cb = ttk.Combobox(top, width=40)
        self.eventos_cb.pack(side='left', padx=5)
        self.eventos_cb.bind("<<ComboboxSelected>>", self.cargar)

        # Motivo
        ttk.Label(frm, text="Motivo del ingreso:").pack(anchor='w', pady=(10,0))
        self.motivo = ttk.Entry(frm)
        self.motivo.pack(fill='x')

        # Monto
        ttk.Label(frm, text="Monto:").pack(anchor='w', pady=(10,0))
        self.monto = ttk.Entry(frm)
        self.monto.pack(fill='x')

        # Botones
        ttk.Button(frm, text="Agregar ingreso", command=self.agregar).pack(pady=5)
        ttk.Button(frm, text="Ver Balance", command=self.ver_balance).pack(pady=5)
        ttk.Button(frm, text="Exportar Balance PDF", command=self.exportar_balance_pdf).pack(pady=5)

        # Tabla
        cols = ("motivo", "monto")
        self.tree = ttk.Treeview(frm, columns=cols, show='headings')
        self.tree.heading("motivo", text="Motivo")
        self.tree.heading("monto", text="Monto")
        self.tree.pack(expand=True, fill='both')

    # ==========================
    # CARGAR EVENTOS
    # ==========================
    def load_eventos(self):
        evs = self.db.fetchall("SELECT id, nombre FROM Eventos")
        self.eventos = evs
        self.eventos_cb['values'] = [f"{e['id']} - {e['nombre']}" for e in evs]

    # ==========================
    # CARGAR INGRESOS
    # ==========================
    def cargar(self, event=None):
        self.tree.delete(*self.tree.get_children())

        ev_txt = self.eventos_cb.get()
        if not ev_txt:
            return

        self.evento_id = int(ev_txt.split('-')[0])
        self.evento_nombre = ev_txt.split('-')[1].strip()

        rows = self.db.fetchall(
            "SELECT motivo, monto FROM Tesoreria WHERE evento_id=?",
            (self.evento_id,)
        )

        for r in rows:
            self.tree.insert('', 'end', values=(r['motivo'], r['monto']))

    # ==========================
    # AGREGAR INGRESO
    # ==========================
    def agregar(self):
        ev_txt = self.eventos_cb.get()
        if not ev_txt:
            messagebox.showerror("Error", "Seleccione un evento")
            return

        evento_id = int(ev_txt.split('-')[0])
        motivo = self.motivo.get().strip()

        if not motivo:
            messagebox.showerror("Error", "Ingrese un motivo")
            return

        try:
            monto = float(self.monto.get())
        except:
            messagebox.showerror("Error", "Monto inválido")
            return

        self.db.execute(
            "INSERT INTO Tesoreria(evento_id, motivo, monto) VALUES(?,?,?)",
            (evento_id, motivo, monto)
        )

        self.motivo.delete(0, 'end')
        self.monto.delete(0, 'end')

        self.cargar()

        messagebox.showinfo("OK", "Ingreso guardado")

    # ==========================
    # BALANCE SIMPLE
    # ==========================
    def ver_balance(self):
        ev_txt = self.eventos_cb.get()
        if not ev_txt:
            messagebox.showerror("Error", "Seleccione un evento")
            return

        evento_id = int(ev_txt.split('-')[0])

        ingresos = self.db.fetchall('''
            SELECT SUM(monto) as total FROM Tesoreria WHERE evento_id=?
        ''', (evento_id,))
        total_ingresos = ingresos[0]['total'] if ingresos and ingresos[0]['total'] else 0

        egresos = self.db.fetchall('''
            SELECT SUM(precio_total) as total
            FROM CompraDetalle cd
            JOIN Compras c ON cd.compra_id = c.id
            WHERE c.evento_id=?
        ''', (evento_id,))
        total_egresos = egresos[0]['total'] if egresos and egresos[0]['total'] else 0

        saldo = total_ingresos - total_egresos

        messagebox.showinfo(
            "Balance",
            f"Ingresos: {total_ingresos:.2f}\n"
            f"Compras: {total_egresos:.2f}\n"
            f"Saldo: {saldo:.2f}"
        )

    # ==========================
    # PDF BALANCE COMPLETO
    # ==========================
    def exportar_balance_pdf(self):
        ev_txt = self.eventos_cb.get()
        if not ev_txt:
            messagebox.showerror("Error", "Seleccione un evento")
            return

        evento_id = int(ev_txt.split('-')[0])
        evento_nombre = ev_txt.split('-')[1].strip()

        # INGRESOS
        ingresos = self.db.fetchall('''
            SELECT motivo, monto FROM Tesoreria WHERE evento_id=?
        ''', (evento_id,))
        total_ingresos = sum([i['monto'] or 0 for i in ingresos])

        # EGRESOS
        egresos = self.db.fetchall('''
            SELECT a.nombre, cd.cantidad, cd.precio_unit, cd.precio_total
            FROM CompraDetalle cd
            JOIN Compras c ON cd.compra_id = c.id
            JOIN Articulos a ON cd.articulo_id = a.id
            WHERE c.evento_id=?
        ''', (evento_id,))
        total_egresos = sum([e['precio_total'] or 0 for e in egresos])

        saldo = total_ingresos - total_egresos

        # RUTA
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        nombre_limpio = re.sub(r'[^a-zA-Z0-9_ ]', '', evento_nombre).replace(" ", "_")
        ruta = os.path.join(desktop, f"Balance_{nombre_limpio}.pdf")

        doc = SimpleDocTemplate(ruta)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"Balance del Evento: {evento_nombre}", styles['Title']))
        elements.append(Spacer(1, 10))

        # INGRESOS
        elements.append(Paragraph("Ingresos", styles['Heading2']))
        data_ing = [["Motivo", "Monto"]]
        for i in ingresos:
            data_ing.append([i['motivo'], f"{i['monto']:.2f}"])
        data_ing.append(["TOTAL", f"{total_ingresos:.2f}"])

        t1 = Table(data_ing)
        t1.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgreen)
        ]))
        elements.append(t1)
        elements.append(Spacer(1, 15))

        messagebox.showinfo("OK", f"PDF generado en escritorio:\n{ruta}")