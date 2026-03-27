import sqlite3


class Database:
    def __init__(self, filename='coen.db'):
        # Conectar a SQLite (import sqlite3 arriba)
        self.conn = sqlite3.connect(filename)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()  # 👈 se ejecuta solo
