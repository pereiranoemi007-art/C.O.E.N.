from flask import Flask, render_template, request, redirect, flash, send_file
import sqlite3
from database import Database
import io
import re

try:
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
except Exception:
    SimpleDocTemplate = None

app = Flask(__name__)
app.secret_key = "softgenius"

db = Database('coen.db')

# ======================
# MENU
# ======================
@app.route('/')
def index():
    return render_template('index.html')

# ======================
# ARTICULOS
# ======================
@app.route('/articulos', methods=['GET', 'POST'])
def articulos():
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        unidad = request.form['unidad']

        if nombre and precio:
            db.execute(
                "INSERT INTO Articulos(nombre, precio, unidad_compra) VALUES(?,?,?)",
                (nombre, float(precio), unidad)
            )

    id_editar = request.args.get('editar')
    editar = None

    if id_editar:
        resultado = db.fetchall("SELECT * FROM Articulos WHERE id=?", (id_editar,))
        if resultado:
            editar = resultado[0]

    datos = db.fetchall("SELECT * FROM Articulos")
    return render_template('articulos.html', datos=datos, editar=editar)

@app.route('/actualizar_articulo/<int:id>', methods=['POST'])
def actualizar_articulo(id):
    db.execute("""
        UPDATE Articulos
        SET nombre=?, precio=?, unidad_compra=?
        WHERE id=?
    """, (
        request.form['nombre'],
        float(request.form['precio']),
        request.form['unidad'],
        id
    ))
    return redirect('/articulos')

@app.route('/eliminar_articulo/<int:id>')
def eliminar_articulo(id):
    db.execute("DELETE FROM Articulos WHERE id=?", (id,))
    return redirect('/articulos')

# ======================
# EVENTOS
# ======================
@app.route('/eventos', methods=['GET', 'POST'])
def eventos():
    if request.method == 'POST':
        nombre = request.form['nombre']
        cantidad = request.form['cantidad']
        tipo = request.form['tipo']

        if nombre and cantidad and tipo:
            db.execute(
                "INSERT INTO Eventos(nombre, cantidad_personas, tipo_actividad) VALUES(?,?,?)",
                (nombre, int(cantidad), tipo)
            )

    datos = db.fetchall("SELECT * FROM Eventos")
    return render_template('eventos.html', datos=datos)

# ======================
# REPORTE PRESUPUESTO
# ======================

@app.route('/eventos/reporte_presupuesto/<int:evento_id>')
def reporte_presupuesto(evento_id):
    if SimpleDocTemplate is None:
        flash('reportlab no está instalado')
        return redirect('/eventos')

    evento = db.fetchone('SELECT nombre, cantidad_personas FROM Eventos WHERE id=?', (evento_id,))
    nombre = evento['nombre'] if evento else f'evento_{evento_id}'
    personas = int(evento['cantidad_personas']) if evento and evento.get('cantidad_personas') else 0

    # ======================
    # RESUMEN
    # ======================
    rows = db.fetchall('''
        SELECT COALESCE(ed.momento, 'Sin momento') AS momento,
               SUM((cd.cant_jov + cd.cant_dor + cd.cant_var) * ? * COALESCE(a.precio,0)) AS presupuesto
        FROM EventoDetalle ed
        JOIN ComidaDetalle cd ON ed.comida_id = cd.comida_id
        JOIN Articulos a ON cd.articulo_id = a.id
        WHERE ed.evento_id = ?
        GROUP BY COALESCE(ed.momento, 'Sin momento')
    ''', (personas, evento_id))

    # ======================
    # DETALLE 🔥
    # ======================
    details = db.fetchall('''
        SELECT 
            COALESCE(ed.momento, 'Sin momento') AS momento,
            a.nombre,
            SUM(cd.cant_jov + cd.cant_dor + cd.cant_var) * ? AS cantidad,
            a.precio,
            (SUM(cd.cant_jov + cd.cant_dor + cd.cant_var) * ? * COALESCE(a.precio,0)) AS subtotal
        FROM EventoDetalle ed
        JOIN ComidaDetalle cd ON ed.comida_id = cd.comida_id
        JOIN Articulos a ON cd.articulo_id = a.id
        WHERE ed.evento_id = ?
        GROUP BY momento, a.id
        ORDER BY momento
    ''', (personas, personas, evento_id))

    # ======================
    # PDF
    # ======================
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Presupuesto - {nombre}", styles['Title'])]

    # TABLA RESUMEN
    data = [["Momento", "Presupuesto"]]
    total = 0
    for r in rows:
        val = r['presupuesto'] or 0
        total += val
        data.append([r['momento'], f"{val:.2f}"])

    data.append(["TOTAL", f"{total:.2f}"])

    table = Table(data)
    table.setStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])
    elements.append(table)

    # ======================
    # TABLA DETALLE 🔥
    # ======================
    elements.append(Spacer(1, 12))
    elements.append(Paragraph('Detalle por Momento y Artículo', styles['Heading2']))

    ddata = [["Momento","Artículo","Cantidad","Precio Unit","Subtotal"]]

    for d in details:
        ddata.append([
            d['momento'],
            d['nombre'],
            d['cantidad'],
            f"{(d['precio'] or 0):.2f}",
            f"{(d['subtotal'] or 0):.2f}"
        ])

    dtable = Table(ddata)
    dtable.setStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])
    elements.append(dtable)

    # GENERAR PDF
    doc.build(elements)
    buf.seek(0)

    safe = re.sub(r'[^a-zA-Z0-9_ ]', '', nombre).replace(' ', '_')

    return send_file(buf,
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'Presupuesto_{safe}.pdf')

# ======================
# TESORERIA - BALANCE
# ======================
@app.route('/tesoreria/reporte_balance/<int:evento_id>')
def reporte_tesoreria_balance(evento_id):

    if SimpleDocTemplate is None:
        flash('reportlab no está instalado')
        return redirect('/tesoreria')

    evento = db.fetchone('SELECT nombre FROM Eventos WHERE id=?', (evento_id,))
    nombre = evento['nombre'] if evento else f'evento_{evento_id}'

    ingresos = db.fetchall('SELECT motivo, monto FROM Tesoreria WHERE evento_id=?', (evento_id,))
    total_ingresos = sum([i['monto'] or 0 for i in ingresos])

    egresos = db.fetchall('''
        SELECT a.nombre, cd.cantidad, cd.precio_total
        FROM CompraDetalle cd
        JOIN Compras c ON cd.compra_id = c.id
        JOIN Articulos a ON cd.articulo_id = a.id
        WHERE c.evento_id=?
    ''', (evento_id,))

    total_egresos = sum([e['precio_total'] or 0 for e in egresos])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Balance del Evento: {nombre}", styles['Title']))
    elements.append(Spacer(1, 10))

    # INGRESOS
    data_ing = [["Motivo", "Monto"]]
    for i in ingresos:
        data_ing.append([i['motivo'], f"{i['monto']:.2f}"])
    data_ing.append(["TOTAL", f"{total_ingresos:.2f}"])

    t1 = Table(data_ing)
    t1.setStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])
    elements.append(t1)

    elements.append(Spacer(1, 15))

    # EGRESOS
    data_eg = [["Artículo", "Cantidad", "Total"]]
    for e in egresos:
        data_eg.append([e['nombre'], e['cantidad'], f"{e['precio_total']:.2f}"])

    data_eg.append(["TOTAL", "", f"{total_egresos:.2f}"])

    t2 = Table(data_eg)
    t2.setStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])
    elements.append(t2)

    # SALDO
    saldo = total_ingresos - total_egresos
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Saldo: {saldo:.2f}", styles['Heading2']))

    doc.build(elements)
    buf.seek(0)

    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'Balance_{nombre}.pdf')




# ======================
# TESORERIA
# ======================
@app.route('/tesoreria', methods=['GET', 'POST'])
def tesoreria():
    eventos = db.fetchall("SELECT * FROM Eventos")

    if request.method == 'POST':
        evento_id = request.form['evento']
        motivo = request.form['motivo']
        monto = request.form['monto']

        # impedir cambios si evento cerrado
        ev = db.fetchone('SELECT closed FROM Eventos WHERE id=?', (evento_id,)) if evento_id else None
        if ev and ev.get('closed'):
            flash('Evento cerrado: no se pueden modificar tesorería')
            return redirect('/tesoreria')

        if evento_id and motivo and monto:
            db.execute(
                "INSERT INTO Tesoreria(evento_id, motivo, monto) VALUES(?,?,?)",
                (evento_id, motivo, float(monto))
            )

    datos = db.fetchall("SELECT * FROM Tesoreria")
    return render_template('tesoreria.html', datos=datos, eventos=eventos)


# ======================
# COMPRAS
# ======================

@app.route('/compras', methods=['GET', 'POST'])
def compras():
    eventos = db.fetchall("SELECT * FROM Eventos")
    articulos = db.fetchall("SELECT * FROM Articulos")
    selected_event = request.args.get('evento')

    if request.method == 'POST':
        evento_id = request.form.get('evento')
        if not evento_id:
            flash('Seleccione un evento antes de guardar la compra')
            return redirect('/compras')
        try:
            evento_id = int(evento_id)
        except Exception:
            flash('Evento inválido')
            return redirect('/compras')
        # impedir cambios si el evento está cerrado
        ev = db.fetchone('SELECT closed FROM Eventos WHERE id=?', (evento_id,)) if evento_id else None
        if ev and ev.get('closed'):
            flash('Evento cerrado: no se pueden modificar las compras')
            return redirect('/compras')

        # 🔥 Borrar compras anteriores del evento
        db.execute("""
            DELETE FROM CompraDetalle 
            WHERE compra_id IN (
                SELECT id FROM Compras WHERE evento_id=?
            )
        """, (evento_id,))

        db.execute(
            "DELETE FROM Compras WHERE evento_id=?",
            (evento_id,)
        )

        # 🔥 Insertar nueva compra
        compra_id = db.execute(
            "INSERT INTO Compras(nombre, evento_id) VALUES(?,?)",
            ("Compra", evento_id)
        )

        # 🔥 Datos del formulario
        articulos_ids = request.form.getlist('articulo')
        cantidades = request.form.getlist('cantidad')
        precios = request.form.getlist('precio')
        precios_unit = request.form.getlist('precio_unit')
        precios_total = request.form.getlist('precio_total')

        for i in range(len(articulos_ids)):
            if not articulos_ids[i]:
                continue

            try:
                articulo_id = int(articulos_ids[i])
                cantidad = float(cantidades[i])
                # prefer precio_total if provided, else compute from precio_unit
                if precios_total and len(precios_total)>i and precios_total[i]:
                    precio = float(precios_total[i]) / (cantidad if cantidad else 1)
                elif precios_unit and len(precios_unit)>i and precios_unit[i]:
                    precio = float(precios_unit[i])
                else:
                    precio = float(precios[i])
            except:
                continue

            total = cantidad * precio

            db.execute(
                """INSERT INTO CompraDetalle
                (compra_id, articulo_id, cantidad, precio_unit, precio_total)
                VALUES(?,?,?,?,?)""",
                (compra_id, articulo_id, cantidad, precio, total)
            )

        flash("Compra guardada correctamente")
        # after saving redirect to show compras for the event
        return redirect(f'/compras?evento={evento_id}')

    # 🔍 MOSTRAR DATOS EN PANTALLA
    # mostrar solo compras del evento seleccionado
    if selected_event:
        datos = db.fetchall("""
            SELECT cd.id, cd.cantidad, cd.precio_total, a.nombre AS articulo, c.id AS compra_id
            FROM CompraDetalle cd
            JOIN Compras c ON cd.compra_id = c.id
            LEFT JOIN Articulos a ON cd.articulo_id = a.id
            WHERE c.evento_id=?
        """, (selected_event,))
    else:
        datos = []

    # comprobar si evento está cerrado
    event_closed = False
    if selected_event:
        try:
            ev = db.fetchone('SELECT closed FROM Eventos WHERE id=?', (selected_event,))
            event_closed = bool(ev and ev.get('closed'))
        except Exception:
            event_closed = False

    return render_template(
        'compras.html',
        eventos=eventos,
        articulos=articulos,
        datos=datos,
        selected_event=selected_event,
        event_closed=event_closed
    )


@app.route('/compras/eliminar/<int:compra_id>')
def eliminar_compra(compra_id):
    # eliminar detalle y compra
    # find evento_id to preserve selection after delete
    comp = db.fetchone('SELECT evento_id FROM Compras WHERE id=?', (compra_id,))
    evento_id = comp['evento_id'] if comp else None

    db.execute('DELETE FROM CompraDetalle WHERE compra_id=?', (compra_id,))
    db.execute('DELETE FROM Compras WHERE id=?', (compra_id,))
    flash('Compra eliminada')
    if evento_id:
        return redirect(f'/compras?evento={evento_id}')
    return redirect('/compras')



# # ======================
# GUARDAR DETALLE COMIDA
# ======================
@app.route('/guardar_detalle', methods=['POST'])
def guardar_detalle():
    comida_id = request.form.get('comida_id')

    # validar comida
    try:
        comida_id_int = int(comida_id)
    except Exception:
        flash('ID de comida inválido')
        return redirect('/comidas')

    comida = db.fetchone('SELECT id FROM Comidas WHERE id=?', (comida_id_int,))
    if not comida:
        flash('Comida no encontrada')
        return redirect('/comidas')

    # no borrar nada aun — primero validar filas y luego reemplazar en una transacción

    articulos_form = request.form.getlist('articulo')
    jov = request.form.getlist('jov')
    dor = request.form.getlist('dor')
    var = request.form.getlist('var')

    # traer articulos en dict por nombre para lookup rapido
    articulos_db = {a['nombre']: a for a in db.fetchall("SELECT * FROM Articulos")}

    filas_a_insertar = []

    for i in range(len(articulos_form)):
        nombre = articulos_form[i]

        if not nombre:
            continue

        articulo = articulos_db.get(nombre)
        if not articulo:
            # no se encontró artículo: ignorar fila y continuar
            flash(f"Artículo no encontrado en DB: {nombre}")
            continue

        try:
            cj = float(jov[i]) if jov[i] else 0
            cd = float(dor[i]) if dor[i] else 0
            cv = float(var[i]) if var[i] else 0
        except Exception:
            flash('Valores numéricos inválidos en detalle de comida')
            continue
        # acumular filas válidas
        filas_a_insertar.append((comida_id_int, articulo['id'], cj, cd, cv))

    # si no hay filas válidas, no borrar existentes
    if not filas_a_insertar:
        flash('No se recibieron filas válidas para guardar; se conservan los detalles existentes')
        return redirect('/comidas')

    # insertar en transacción: borrar previos y luego insertar nuevos
    try:
        # usar cursor/conn directamente para controlar commit/rollback (Database.execute hace commit automático)
        db.conn.execute('BEGIN')
        db.cursor.execute("DELETE FROM ComidaDetalle WHERE comida_id=?", (comida_id_int,))
        for fila in filas_a_insertar:
            db.cursor.execute("INSERT INTO ComidaDetalle(comida_id, articulo_id, cant_jov, cant_dor, cant_var) VALUES(?,?,?,?,?)", fila)
        db.conn.commit()
        flash('Detalle de comida actualizado')
    except Exception as ex:
        try:
            db.conn.rollback()
        except Exception:
            pass
        flash(f'Error guardando detalle de comida: {ex}')

    return redirect('/comidas')


# ======================
# ELIMINAR COMIDA
# ======================
@app.route('/eliminar_comida/<int:id>')
def eliminar_comida(id):
    db.execute("DELETE FROM Comidas WHERE id=?", (id,))
    # also delete detalle rows
    db.execute("DELETE FROM ComidaDetalle WHERE comida_id=?", (id,))
    flash('Comida eliminada')
    return redirect('/comidas')


# ======================
# AGREGAR COMIDA
# ======================
@app.route('/add_comida', methods=['POST'])
def add_comida():
    desc = request.form['descripcion']

    if desc:
        # DBs older may have different column names / constraints. Try safe inserts with fallbacks.
        try:
            if db.has_column('Comidas', 'descripcion') and db.has_column('Comidas', 'nombre'):
                new_id = db.execute("INSERT INTO Comidas(descripcion, nombre) VALUES(?,?)", (desc, desc))
            elif db.has_column('Comidas', 'descripcion'):
                new_id = db.execute("INSERT INTO Comidas(descripcion) VALUES(?)", (desc,))
            elif db.has_column('Comidas', 'nombre'):
                new_id = db.execute("INSERT INTO Comidas(nombre) VALUES(?)", (desc,))
            else:
                new_id = db.execute("INSERT INTO Comidas(descripcion) VALUES(?)", (desc,))
            flash(f"Comida creada (id={new_id})")
        except sqlite3.IntegrityError:
            # intento alternativo: si existe 'nombre' y la inserción previa falló por NOT NULL, forzamos insertar nombre
            try:
                if db.has_column('Comidas', 'nombre'):
                    new_id = db.execute("INSERT INTO Comidas(nombre) VALUES(?)", (desc,))
                    flash(f"Comida creada (id={new_id})")
                else:
                    new_id = db.execute("INSERT INTO Comidas(descripcion) VALUES(?)", (desc,))
                    flash(f"Comida creada (id={new_id})")
            except Exception:
                # último recurso: intentar insertar sin columnas (si tabla cambió drásticamente)
                try:
                    # avoid inserting into VALUES(...) because table may have different number of columns
                    raise
                except Exception as ex:
                    # informar y no intentar un INSERT inválido
                    print('Error insertando comida (fallback):', ex)
                    flash('No se pudo crear la comida: esquema de BD incompatible')
                    # do not re-raise to avoid breaking the request flow

    return redirect('/comidas')


# ======================
# RUTA COMIDAS (WEB)
# ======================
@app.route('/comidas')
def comidas():
    comidas = db.fetchall("SELECT * FROM Comidas")
    # normalizar campo descripcion para compatibilidad con esquemas antiguos
    for c in comidas:
        if 'descripcion' not in c or not c.get('descripcion'):
            # si existe 'nombre', usarla como descripcion
            if 'nombre' in c and c.get('nombre'):
                c['descripcion'] = c['nombre']
            else:
                c['descripcion'] = ''
    articulos = db.fetchall("SELECT * FROM Articulos")

    # detalles por comida (se muestran en la UI y se filtran con JS)
    detalles = db.fetchall(
        """
        SELECT cd.id, cd.comida_id, cd.articulo_id, a.nombre AS articulo,
               cd.cant_jov, cd.cant_dor, cd.cant_var
        FROM ComidaDetalle cd
        LEFT JOIN Articulos a ON cd.articulo_id = a.id
        """
    )

    return render_template('comidas.html', comidas=comidas, articulos=articulos, detalles=detalles)



# ======================
# RUN
# ======================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5005, debug=True)