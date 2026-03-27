import tkinter as tk
from tkinter import ttk, messagebox
from database import Database

class ComprasWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Compras')
        self.geometry('800x500')
        self.db = Database('coen.db')

        try:
            self.db.execute("ALTER TABLE CompraDetalle ADD COLUMN precio_unit REAL")
        except:
            pass

        self.create_widgets()
        self.load_eventos()
        self.load_articulos()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(expand=True, fill='both')

        top = ttk.Frame(frm)
        top.pack(fill='x')

        ttk.Label(top, text='Evento:').pack(side='left')
        self.eventos_cb = ttk.Combobox(top)
        self.eventos_cb.pack(side='left', padx=5)
        self.eventos_cb.bind("<<ComboboxSelected>>", self.on_event_change)

        self.btn_guardar = ttk.Button(top, text='Guardar', command=self.guardar)
        self.btn_guardar.pack(side='left', padx=10)

        ttk.Label(frm, text='Detalle de Compra', font=('Segoe UI', 12, 'bold')).pack(pady=5)

        header = ttk.Frame(frm)
        header.pack(fill='x')
        ttk.Label(header, text='Artículo', width=30).pack(side='left')
        ttk.Label(header, text='Cantidad', width=10).pack(side='left')
        ttk.Label(header, text='Precio', width=10).pack(side='left')

        self.detalle_frame = ttk.Frame(frm)
        self.detalle_frame.pack(fill='both', expand=True)

        self.btn_add = ttk.Button(frm, text='Agregar fila', command=self.add_row)
        self.btn_add.pack(pady=5)

        self.rows = []

    def load_eventos(self):
        evs = self.db.fetchall('SELECT id, nombre, closed FROM Eventos')
        self.eventos = evs
        self.eventos_cb['values'] = [f"{e['id']} - {e['nombre']}" for e in evs]

    def load_articulos(self):
        self.articulos = self.db.fetchall('SELECT id, nombre FROM Articulos')

    def on_event_change(self, event=None):
        self.cargar_datos()
        self.control_evento()

    def control_evento(self):
        ev_txt = self.eventos_cb.get()
        evento_id = int(ev_txt.split('-')[0])
        ev = next((e for e in self.eventos if e['id'] == evento_id), None)

        if ev and ev['closed']:
            self.btn_guardar['state'] = 'disabled'
            self.btn_add['state'] = 'disabled'
            for r in self.rows:
                r['articulo']['state'] = 'disabled'
                r['cantidad']['state'] = 'disabled'
                r['precio']['state'] = 'disabled'
        else:
            self.btn_guardar['state'] = 'normal'
            self.btn_add['state'] = 'normal'

    def limpiar(self):
        for w in self.detalle_frame.winfo_children():
            w.destroy()
        self.rows = []

    def cargar_datos(self):
        self.limpiar()

        ev_txt = self.eventos_cb.get().strip()
        if not ev_txt:
            return

        evento_id = int(ev_txt.split('-')[0])

        datos = self.db.fetchall('''
            SELECT cd.articulo_id, a.nombre, cd.cantidad, cd.precio_unit
            FROM CompraDetalle cd
            JOIN Compras c ON cd.compra_id = c.id
            JOIN Articulos a ON cd.articulo_id = a.id
            WHERE c.evento_id = ?
        ''', (evento_id,))

        for d in datos:
            self.add_row(d['nombre'], d['cantidad'], d['precio_unit'])

    def add_row(self, nombre='', cantidad='', precio=''):
        row = {}
        frm = ttk.Frame(self.detalle_frame)
        frm.pack(fill='x', pady=2)

        cb = ttk.Combobox(frm, values=[a['nombre'] for a in self.articulos], width=30)
        cb.set(nombre)
        cb.pack(side='left')
        row['articulo'] = cb

        e1 = ttk.Entry(frm, width=10)
        e1.insert(0, cantidad)
        e1.pack(side='left', padx=5)
        row['cantidad'] = e1

        e2 = ttk.Entry(frm, width=10)
        e2.insert(0, precio)
        e2.pack(side='left', padx=5)
        row['precio'] = e2

        btn = ttk.Button(frm, text='X', command=lambda f=frm: self.eliminar_row(f))
        btn.pack(side='left')
        row['frame'] = frm

        self.rows.append(row)

    def eliminar_row(self, frame):
        for r in list(self.rows):
            if r['frame'] == frame:
                r['frame'].destroy()
                self.rows.remove(r)

    def guardar(self):
        ev_txt = self.eventos_cb.get().strip()
        if not ev_txt:
            messagebox.showerror('Error', 'Seleccione un evento')
            return

        evento_id = int(ev_txt.split('-')[0])

        # borrar datos anteriores del evento
        compras = self.db.fetchall("SELECT id FROM Compras WHERE evento_id=?", (evento_id,))
        for c in compras:
            self.db.execute("DELETE FROM CompraDetalle WHERE compra_id=?", (c['id'],))
        self.db.execute("DELETE FROM Compras WHERE evento_id=?", (evento_id,))

        # crear nueva compra
        self.db.execute("INSERT INTO Compras(nombre, evento_id) VALUES(?,?)", ("Compra", evento_id))
        compra_id = self.db.cursor.lastrowid

        for r in self.rows:
            nombre = r['articulo'].get().strip()
            if not nombre:
                continue

            articulo = next((a for a in self.articulos if a['nombre']==nombre), None)
            if not articulo:
                continue

            try:
                cantidad = float(r['cantidad'].get())
                precio = float(r['precio'].get())
            except:
                messagebox.showerror('Error', 'Datos inválidos')
                return

            total = cantidad * precio

            self.db.execute(
                "INSERT INTO CompraDetalle(compra_id, articulo_id, cantidad, precio_unit, precio_total) VALUES(?,?,?,?,?)",
                (compra_id, articulo['id'], cantidad, precio, total)
            )

        messagebox.showinfo('OK', 'Guardado correctamente')
