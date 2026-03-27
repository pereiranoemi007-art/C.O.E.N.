import tkinter as tk
from tkinter import ttk, messagebox
from database import Database

class ComidasWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Comidas')
        self.geometry('800x500')
        self.db = Database('coen.db')
        self.create_widgets()
        self.load_comidas()
        self.load_articulos()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(expand=True, fill='both')

        top = ttk.Frame(frm)
        top.pack(fill='x')
        ttk.Label(top, text='Descripción:').pack(side='left')
        self.descripcion = ttk.Entry(top)
        self.descripcion.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(top, text='Agregar Comida', command=self.add_comida).pack(side='left', padx=5)

        mid = ttk.Frame(frm)
        mid.pack(fill='both', expand=True, pady=10)

        # Left: Comidas list
        left = ttk.Frame(mid)
        left.pack(side='left', fill='y')
        cols = ('id', 'descripcion')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', height=15)
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.pack(side='left')
        self.tree.bind('<<TreeviewSelect>>', self.on_select_comida)

        # Right: detalle editable
        right = ttk.Frame(mid)
        right.pack(side='left', fill='both', expand=True, padx=10)
        hdr = ttk.Frame(right)
        hdr.pack(fill='x')
        ttk.Label(hdr, text='Detalle de comida').pack()
        # Column titles for the detalle area (use grid for proper alignment)
        cols_hdr = ttk.Frame(right)
        cols_hdr.pack(fill='x', pady=(5, 0))
        cols_hdr.columnconfigure(0, weight=1)
        ttk.Label(cols_hdr, text='Artículo').grid(row=0, column=0, sticky='w', padx=2)
        ttk.Label(cols_hdr, text='Cant Jov').grid(row=0, column=1, padx=15)
        ttk.Label(cols_hdr, text='Cant Dor').grid(row=0, column=2, padx=15)
        ttk.Label(cols_hdr, text='Cant Var').grid(row=0, column=3, padx=15)
        ttk.Label(cols_hdr, text='').grid(row=0, column=4, padx=2)  # placeholder for delete button column

        self.detalle_frame = ttk.Frame(right)
        self.detalle_frame.pack(fill='both', expand=True)
        # allow first column to expand so Combobox fills available space
        self.detalle_frame.columnconfigure(0, weight=1)
        # index to place next detalle row (grid row)
        self.next_detalle_row = 0

        btns = ttk.Frame(frm)
        btns.pack(fill='x')
        ttk.Button(btns, text='Guardar detalle', command=self.save_detalle).pack(side='left', padx=5)
        ttk.Button(btns, text='Eliminar comida', command=self.delete_comida).pack(side='left', padx=5)

        self.detalle_rows = []

    def load_comidas(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        rows = self.db.fetchall('SELECT id, descripcion FROM Comidas')
        for row in rows:
            self.tree.insert('', 'end', values=(row['id'], row['descripcion']))

    def load_articulos(self):
        self.articulos = self.db.fetchall('SELECT id, nombre, precio FROM Articulos')

    def add_comida(self):
        desc = self.descripcion.get().strip()
        if not desc:
            messagebox.showerror('Error', 'Descripción requerida')
            return
        self.db.execute('INSERT INTO Comidas(descripcion) VALUES(?)', (desc,))
        self.descripcion.delete(0, 'end')
        self.load_comidas()

    def on_select_comida(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])['values']
        self.comida_id = vals[0]
        self.load_detalle()

    def clear_detalle_ui(self):
        for w in self.detalle_frame.winfo_children():
            w.destroy()
        self.detalle_rows = []
        self.next_detalle_row = 0

    def load_detalle(self):
        self.clear_detalle_ui()
        rows = self.db.fetchall('SELECT cd.id, cd.articulo_id, a.nombre, cd.cant_jov, cd.cant_dor, cd.cant_var FROM ComidaDetalle cd LEFT JOIN Articulos a ON cd.articulo_id=a.id WHERE cd.comida_id=?', (self.comida_id,))
        for r in rows:
            self.add_detalle_row(r['articulo_id'], r['nombre'], r['cant_jov'], r['cant_dor'], r['cant_var'], existing_id=r['id'])
        # add empty row
        self.add_detalle_row()

    def add_detalle_row(self, articulo_id=None, nombre='', cant_jov=None, cant_dor=None, cant_var=None, existing_id=None):
        row = {}
        # place a frame for the row and use grid inside so columns align with headers
        frm = ttk.Frame(self.detalle_frame)
        frm.grid(row=self.next_detalle_row, column=0, sticky='ew', pady=2)
        frm.columnconfigure(0, weight=1)
        r = self.next_detalle_row
        self.next_detalle_row += 1

        # articulo combobox (column 0)
        cb = ttk.Combobox(frm, values=[a['nombre'] for a in self.articulos])
        if articulo_id:
            cb.set(nombre)
        cb.grid(row=0, column=0, sticky='ew', padx=2)
        row['combobox'] = cb

        # cant_jov (column 1)
        e1 = ttk.Entry(frm, width=8)
        if cant_jov is not None:
            e1.insert(0, str(cant_jov))
        e1.grid(row=0, column=1, padx=6)
        row['cant_jov'] = e1

        # cant_dor (column 2)
        e2 = ttk.Entry(frm, width=8)
        if cant_dor is not None:
            e2.insert(0, str(cant_dor))
        e2.grid(row=0, column=2, padx=6)
        row['cant_dor'] = e2

        # cant_var (column 3)
        e3 = ttk.Entry(frm, width=8)
        if cant_var is not None:
            e3.insert(0, str(cant_var))
        e3.grid(row=0, column=3, padx=6)
        row['cant_var'] = e3

        # delete button (column 4)
        btn = ttk.Button(frm, text='X', width=3, command=lambda f=frm: self.remove_detalle_row(f))
        btn.grid(row=0, column=4, padx=4)

        row['frame'] = frm
        row['id'] = existing_id
        self.detalle_rows.append(row)

    def remove_detalle_row(self, frame):
        for r in list(self.detalle_rows):
            if r['frame'] == frame:
                r['frame'].destroy()
                self.detalle_rows.remove(r)

    def save_detalle(self):
        if not hasattr(self, 'comida_id'):
            messagebox.showwarning('Aviso', 'Seleccione una comida')
            return
        # delete existing details for simplicity then reinsert
        self.db.execute('DELETE FROM ComidaDetalle WHERE comida_id=?', (self.comida_id,))
        for r in self.detalle_rows:
            nombre = r['combobox'].get().strip()
            if not nombre:
                continue
            articulo = next((a for a in self.articulos if a['nombre']==nombre), None)
            if not articulo:
                continue
            try:
                cj = float(r['cant_jov'].get()) if r['cant_jov'].get() else 0
                cd = float(r['cant_dor'].get()) if r['cant_dor'].get() else 0
                cv = float(r['cant_var'].get()) if r['cant_var'].get() else 0
            except ValueError:
                messagebox.showerror('Error', 'Cantidad inválida')
                return
            self.db.execute('INSERT INTO ComidaDetalle(comida_id, articulo_id, cant_jov, cant_dor, cant_var) VALUES(?,?,?,?,?)', (self.comida_id, articulo['id'], cj, cd, cv))
        messagebox.showinfo('OK', 'Detalle guardado')

    def delete_comida(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Aviso', 'Seleccione una comida')
            return
        vals = self.tree.item(sel[0])['values']
        if messagebox.askyesno('Confirmar', f'Eliminar comida {vals[1]}?'):
            self.db.execute('DELETE FROM Comidas WHERE id=?', (vals[0],))
            self.load_comidas()
            self.clear_detalle_ui()
