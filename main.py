import tkinter as tk
from tkinter import ttk
from ventanas.articles_window import ArticlesWindow
from ventanas.comidas_window import ComidasWindow
from ventanas.eventos_window import EventosWindow
from ventanas.compras_window import ComprasWindow
from ventanas.tesoreria_window import TesoreriaWindow
from database import Database




DB = Database('coen.db')




class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Sistema de Gestión - Coen')
        self.geometry('800x600')
        self.resizable(False, False)
        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text='Menú Principal', font=('Segoe UI', 14)).pack(pady=10)

        btns = [
            ('Artículos', self.open_articulos),
            ('Comida', self.open_comidas),
            ('Compra', self.open_compras),
            ('Evento', self.open_eventos),
            ('Tesoreria', self.open_tesoreria),
            ('Salir', self.quit)
        ]

        for (text, cmd) in btns:
            ttk.Button(frame, text=text, command=cmd).pack(fill='x', pady=5)

    def open_articulos(self):
        ArticlesWindow(self)

    def open_comidas(self):
        ComidasWindow(self)

    def open_compras(self):
        ComprasWindow(self)

    def open_eventos(self):
        EventosWindow(self)   
        
    def open_tesoreria(self):
        TesoreriaWindow(self)

if __name__ == '__main__':
    app = MainApp()
    app.mainloop()
