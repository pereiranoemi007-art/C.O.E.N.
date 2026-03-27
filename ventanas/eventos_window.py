import tkinter as tk
import os
import re
from tkinter import ttk, messagebox
from database import Database

# 👉 IMPORTANTE PARA PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


class EventosWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Eventos')
        self.geometry('900x600')
        self.db = Database('coen.db')
        self.create_widgets()
        self.load_eventos()
        self.load_comidas()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(expand=True, fill='both')

        top = ttk.Frame(frm)
        top.pack(fill='x', pady=(0, 10))

        ttk.Label(top, text='Nombre evento:').grid(row=0, column=0, sticky='w', padx=2, pady=2)
        self.nombre = ttk.Entry(top)
        self.nombre.grid(row=0, column=1, sticky='ew', padx=2, pady=2)

        ttk.Label(top, text='Cantidad personas:').grid(row=1, column=0, sticky='w', padx=2, pady=2)
        self.cant_personas = ttk.Entry(top)
        self.cant_personas.grid(row=1, column=1, sticky='ew', padx=2, pady=2)

        ttk.Label(top, text='Tipo actividad:').grid(row=2, column=0, sticky='w', padx=2, pady=2)
        self.tipo = ttk.Combobox(top, values=['Dorcas', 'Jovenes', 'Varones'])
        self.tipo.grid(row=2, column=1, sticky='ew', padx=2, pady=2)

        top.columnconfigure(1, weight=1)

        right_ctrl = ttk.Frame(top)
        right_ctrl.grid(row=0, column=2, rowspan=3, sticky='nsew', padx=(10, 0))

        self.closed_var = tk.IntVar(value=0)
        ttk.Checkbutton(right_ctrl, text='Evento cerrado', variable=self.closed_var).pack(anchor='w', pady=2)

        ttk.Button(right_ctrl, text='Guardar estado', command=self.save_closed_state).pack(anchor='w', pady=2)
        ttk.Button(right_ctrl, text='Agregar Evento', command=self.add_evento).pack(anchor='w', pady=8)

        mid = ttk.Frame(frm)
        mid.pack(fill='both', expand=True, pady=10)

        left = ttk.Frame(mid)
        left.pack(side='left', fill='both', expand=True)

        cols = ('id', 'nombre', 'cantidad_personas', 'tipo_actividad', 'closed')
        self.tree = ttk.Treeview(left, columns=cols, show='headings')

        for col in cols:
            self.tree.heading(col, text=col.capitalize())

        self.tree.pack(side='left', fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select_evento)

        ttk.Scrollbar(left, orient='vertical', command=self.tree.yview).pack(side='right', fill='y')

        right = ttk.Frame(mid)
        right.pack(side='left', fill='both', expand=True, padx=10)

        ttk.Label(right, text='Detalle de evento').pack()

        self.detalle_frame = ttk.Frame(right)
        self.detalle_frame.pack(fill='both', expand=True)

        btns = ttk.Frame(frm)
        btns.pack(fill='x')

        ttk.Button(btns, text='Guardar detalle', command=self.save_detalle).pack(side='left', padx=5)
        ttk.Button(btns, text='Eliminar evento', command=self.delete_evento).pack(side='left', padx=5)
        ttk.Button(btns, text='Reporte Compras', command=self.imprimir_compras).pack(side='left', padx=5)
        ttk.Button(btns, text='Reporte Saldo', command=self.imprimir_saldo).pack(side='left', padx=5)

        self.detalle_rows = []

    def load_eventos(self):
        for r in self.tree.get_children():
            self.tree.delete(r)

        rows = self.db.fetchall('SELECT * FROM Eventos')

        for row in rows:
            self.tree.insert('', 'end', values=(row['id'], row['nombre'], row['cantidad_personas'], row['tipo_actividad'], row['closed']))

    def load_comidas(self):
        self.comidas = self.db.fetchall('SELECT * FROM Comidas')

    def add_evento(self):
        self.db.execute(
            'INSERT INTO Eventos(nombre, cantidad_personas, tipo_actividad, closed) VALUES(?,?,?,?)',
            (self.nombre.get(), self.cant_personas.get(), self.tipo.get(), self.closed_var.get())
        )
        self.load_eventos()

    def on_select_evento(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        vals = self.tree.item(sel[0])['values']
        self.evento_id = vals[0]
        self.evento_nombre = vals[1]  # 🔥 clave

    def save_closed_state(self):
        if not hasattr(self, 'evento_id'):
            return

        self.db.execute('UPDATE Eventos SET closed=? WHERE id=?',
                        (self.closed_var.get(), self.evento_id))

    def save_detalle(self):
        pass

    def delete_evento(self):
        pass

    # ==========================
    # PDF COMPRAS
    # ==========================
    def imprimir_compras(self):
        if not hasattr(self, 'evento_id'):
            messagebox.showwarning('Aviso', 'Seleccione un evento')
            return

        rows = self.db.fetchall('''
            SELECT a.nombre, SUM(cd.cant_jov+cd.cant_dor+cd.cant_var) as total
            FROM EventoDetalle ed
            JOIN ComidaDetalle cd ON ed.comida_id=cd.comida_id
            JOIN Articulos a ON cd.articulo_id=a.id
            WHERE ed.evento_id=?
            GROUP BY a.nombre
        ''', (self.evento_id,))

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        nombre_limpio = re.sub(r'[^a-zA-Z0-9_ ]', '', self.evento_nombre).replace(" ", "_")

        ruta = os.path.join(desktop, f"Compras_{nombre_limpio}.pdf")

        doc = SimpleDocTemplate(ruta)
        styles = getSampleStyleSheet()
        elements = [Paragraph(f"Reporte de Compras - {self.evento_nombre}", styles['Title'])]

        data = [["Artículo", "Cantidad"]]
        for r in rows:
            data.append([r['nombre'], r['total']])

        table = Table(data)
        table.setStyle([('GRID', (0, 0), (-1, -1), 1, colors.black)])

        elements.append(table)
        doc.build(elements)

        messagebox.showinfo("OK", f"PDF generado:\n{ruta}")

    # ==========================
    # PDF SALDO
    # ==========================
    def imprimir_saldo(self):
        if not hasattr(self, 'evento_id'):
            messagebox.showwarning('Aviso', 'Seleccione un evento')
            return

        necesarios = self.db.fetchall('''
            SELECT cd.articulo_id, a.nombre,
            SUM(cd.cant_jov+cd.cant_dor+cd.cant_var) as total
            FROM EventoDetalle ed
            JOIN ComidaDetalle cd ON ed.comida_id=cd.comida_id
            JOIN Articulos a ON cd.articulo_id=a.id
            WHERE ed.evento_id=?
            GROUP BY cd.articulo_id
        ''', (self.evento_id,))

        comprados = self.db.fetchall('''
            SELECT cd.articulo_id, SUM(cd.cantidad) as total
            FROM CompraDetalle cd
            JOIN Compras c ON cd.compra_id = c.id
            WHERE c.evento_id=?
            GROUP BY cd.articulo_id
        ''', (self.evento_id,))

        comprados_dict = {c['articulo_id']: c['total'] for c in comprados}

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        nombre_limpio = re.sub(r'[^a-zA-Z0-9_ ]', '', self.evento_nombre).replace(" ", "_")

        ruta = os.path.join(desktop, f"Saldo_{nombre_limpio}.pdf")

        doc = SimpleDocTemplate(ruta)
        styles = getSampleStyleSheet()
        elements = [Paragraph(f"Reporte de Saldo - {self.evento_nombre}", styles['Title'])]

        data = [["Artículo", "Necesario", "Comprado", "Saldo"]]

        for n in necesarios:
            comprado = comprados_dict.get(n['articulo_id'], 0)
            saldo = (n['total'] or 0) - (comprado or 0)

            data.append([n['nombre'], n['total'], comprado, saldo])

        table = Table(data)
        table.setStyle([('GRID', (0, 0), (-1, -1), 1, colors.black)])

        elements.append(table)
        doc.build(elements)

        messagebox.showinfo("OK", f"PDF generado:\n{ruta}")