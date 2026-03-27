import tkinter as tk
from tkinter import ttk, messagebox
from database import Database




class ArticlesWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Artículos')
        self.geometry('800x600')
        self.db = Database('coen.db')
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(expand=True, fill='both')

        # Form
        form = ttk.Frame(frm)
        form.pack(fill='x')

        ttk.Label(form, text='Nombre:').grid(row=0, column=0, sticky='w')
        self.nombre = ttk.Entry(form)
        self.nombre.grid(row=0, column=1, sticky='ew')

        ttk.Label(form, text='Precio:').grid(row=1, column=0, sticky='w')
        self.precio = ttk.Entry(form)
        self.precio.grid(row=1, column=1, sticky='ew')

        ttk.Label(form, text='Unidad compra:').grid(row=2, column=0, sticky='w')
        self.unidad = ttk.Entry(form)
        self.unidad.grid(row=2, column=1, sticky='ew')

        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(frm)
        btns.pack(fill='x', pady=10)
        ttk.Button(btns, text='Agregar', command=self.add).pack(side='left', padx=5)
        ttk.Button(btns, text='Editar', command=self.edit).pack(side='left', padx=5)
        ttk.Button(btns, text='Eliminar', command=self.delete).pack(side='left', padx=5)

        # Table
        cols = ('id', 'nombre', 'precio', 'unidad_compra')
        self.tree = ttk.Treeview(frm, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.pack(expand=True, fill='both')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def load_data(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        rows = self.db.fetchall('SELECT id, nombre, precio, unidad_compra FROM Articulos')
        for row in rows:
            self.tree.insert('', 'end', values=(row['id'], row['nombre'], row['precio'], row['unidad_compra']))

    def add(self):
        nombre = self.nombre.get().strip()
        try:
            precio = float(self.precio.get())
        except ValueError:
            messagebox.showerror('Error', 'Precio inválido')
            return
        unidad = self.unidad.get().strip()
        if not nombre:
            messagebox.showerror('Error', 'Nombre requerido')
            return
        self.db.execute('INSERT INTO Articulos(nombre, precio, unidad_compra) VALUES(?,?,?)', (nombre, precio, unidad))
        self.load_data()
        self.nombre.delete(0, 'end')
        self.precio.delete(0, 'end')
        self.unidad.delete(0, 'end')

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])['values']
        self.edit_id = vals[0]
        self.nombre.delete(0, 'end'); self.nombre.insert(0, vals[1])
        self.precio.delete(0, 'end'); self.precio.insert(0, vals[2])
        self.unidad.delete(0, 'end'); self.unidad.insert(0, vals[3])

    def edit(self):
        if not hasattr(self, 'edit_id'):
            messagebox.showwarning('Aviso', 'Seleccione un artículo')
            return
        nombre = self.nombre.get().strip()
        try:
            precio = float(self.precio.get())
        except ValueError:
            messagebox.showerror('Error', 'Precio inválido')
            return
        unidad = self.unidad.get().strip()
        self.db.execute('UPDATE Articulos SET nombre=?, precio=?, unidad_compra=? WHERE id=?', (nombre, precio, unidad, self.edit_id))
        self.load_data()

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Aviso', 'Seleccione un artículo')
            return
        vals = self.tree.item(sel[0])['values']
        if messagebox.askyesno('Confirmar', f'Eliminar artículo {vals[1]}?'):
            self.db.execute('DELETE FROM Articulos WHERE id=?', (vals[0],))
            self.load_data()
