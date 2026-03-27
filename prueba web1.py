from flask import Flask, render_template, request, redirect, flash, send_file
import sqlite3
from database import Database
import io
import os
import re
try:
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
except Exception:
    SimpleDocTemplate = None

app = Flask(__name__)
app.secret_key = "softgenius"  # 🔥 NECESARIO para flash

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

    # 🔥 DETECTAR SI SE QUIERE EDITAR
    id_editar = request.args.get('editar')
    editar = None

    if id_editar:
        resultado = db.fetchall("SELECT * FROM Articulos WHERE id=?", (id_editar,))
        if resultado:
            editar = resultado[0]

    datos = db.fetchall("SELECT * FROM Articulos")

    return render_template('articulos.html', datos=datos, editar=editar)


# ✅ ACTUALIZAR ARTÍCULO
@app.route('/actualizar_articulo/<int:id>', methods=['POST'])
def actualizar_articulo(id):
    nombre = request.form['nombre']
    precio = request.form['precio']
    unidad = request.form['unidad']

    db.execute("""
        UPDATE Articulos
        SET nombre=?, precio=?, unidad_compra=?
        WHERE id=?
    """, (nombre, float(precio), unidad, id))

    return redirect('/articulos')


# ❌ ELIMINAR (ya lo tenías)
@app.route('/eliminar_articulo/<int:id>')
def eliminar_articulo(id):
    db.execute("DELETE FROM Articulos WHERE id=?", (id,))
    return redirect('/articulos')

# ======================
# EVENTOS
# ======================
@app.route('/eventos/reporte_presupuesto/<int:evento_id>')
def reporte_presupuesto(evento_id):
    if SimpleDocTemplate is None:
        flash('reportlab no está instalado')
        return redirect('/eventos')

    evento = db.fetchone('SELECT nombre, cantidad_personas, tipo_actividad FROM Eventos WHERE id=?', (evento_id,))
    nombre = evento['nombre'] if evento else f'evento_{evento_id}'
    personas = int(evento.get('cantidad_personas') or 0) if evento else 0
    tipo = (evento.get('tipo_actividad') or '').strip().lower() if evento else ''

    # 🔹 TRAER unidad_compra también
    rows = db.fetchall('''
        SELECT COALESCE(ed.momento, 'Sin momento') AS momento,
               a.id AS articulo_id,
               a.nombre,
               a.precio,
               a.unidad_compra,
               SUM(cd.cant_jov) AS sum_jov,
               SUM(cd.cant_dor) AS sum_dor,
               SUM(cd.cant_var) AS sum_var
        FROM EventoDetalle ed
        JOIN ComidaDetalle cd ON ed.comida_id = cd.comida_id
        JOIN Articulos a ON cd.articulo_id = a.id
        WHERE ed.evento_id = ?
        GROUP BY momento, a.id
        ORDER BY momento
    ''', (evento_id,))

    momentos = {}
    detalle = []
    total = 0

    for r in rows:
        # tipo de actividad
        if tipo.startswith('dor'):
            per = r.get('sum_dor') or 0
        elif tipo.startswith('jov'):
            per = r.get('sum_jov') or 0
        elif tipo.startswith('var'):
            per = r.get('sum_var') or 0
        else:
            per = (r.get('sum_jov') or 0) + (r.get('sum_dor') or 0) + (r.get('sum_var') or 0)

        # cantidad total base
        cantidad_total = per * personas

        # 🔴 AJUSTE POR UNIDAD DE COMPRA
        unidad = float(r.get('unidad_compra') or 1)
        if unidad > 0:
            cantidad_compra = cantidad_total / unidad
        else:
            cantidad_compra = cantidad_total

        precio = float(r.get('precio') or 0)
        subtotal = cantidad_compra * precio

        momento = r['momento']

        momentos[momento] = momentos.get(momento, 0) + subtotal
        total += subtotal

        detalle.append({
            'momento': momento,
            'nombre': r['nombre'],
            'cantidad': cantidad_compra,
            'precio': precio,
            'subtotal': subtotal
        })

    # PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"Presupuesto estimado - {nombre}", styles['Title'])]

    # resumen
    data = [["Momento", "Presupuesto"]]
    for m, val in momentos.items():
        data.append([m, f"{val:.2f}"])

    data.append(["TOTAL", f"{total:.2f}"])

    table = Table(data)
    table.setStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgreen)
    ])
    elements.append(table)

    # detalle
    elements.append(Spacer(1,12))
    elements.append(Paragraph('Detalle por Momento y Artículo', styles['Heading2']))

    ddata = [["Momento","Artículo","Cantidad","Precio Unit","Subtotal"]]
    for d in detalle:
        ddata.append([
            d['momento'],
            d['nombre'],
            f"{d['cantidad']:.2f}",
            f"{d['precio']:.2f}",
            f"{d['subtotal']:.2f}"
        ])

    dtable = Table(ddata)
    dtable.setStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])
    elements.append(dtable)

    doc.build(elements)
    buf.seek(0)

    safe = re.sub(r'[^a-zA-Z0-9_ ]', '', nombre).replace(' ', '_')
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Presupuesto_{safe}.pdf'
    )
# ==========================
# REPORTES TESORERIA (WEB)
# ==========================
@app.route('/tesoreria/reporte_balance/<int:evento_id>')
def reporte_tesoreria_balance(evento_id):
    if SimpleDocTemplate is None:
        flash('reportlab no está instalado')
        return redirect('/tesoreria')

    evento = db.fetchone('SELECT nombre FROM Eventos WHERE id=?', (evento_id,))
    nombre = evento['nombre'] if evento else f'evento_{evento_id}'

    ingresos = db.fetchall('SELECT motivo, monto FROM Tesoreria WHERE evento_id=?', (evento_id,))
    total_ingresos = sum([i['monto'] or 0 for i in ingresos])
    # ensure precio_unit is filled for old rows (no-destructive backfill)
    try:
        db.execute("UPDATE CompraDetalle SET precio_unit = precio_total / NULLIF(cantidad,0) WHERE precio_unit IS NULL AND cantidad>0")
    except Exception:
        pass

    egresos = db.fetchall('''
        SELECT a.nombre, cd.cantidad, cd.precio_unit, cd.precio_total, c.id as compra_id
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

    # EGRESOS resumen
    elements.append(Paragraph("Egresos (Compras)", styles['Heading2']))
    # Reporte de gasto por comida (sumar por comida vinculada)
    gastos_por_comida = db.fetchall('''
        SELECT ed.momento as momento, SUM(cd.precio_total) as gasto
        FROM EventoDetalle ed
        JOIN ComidaDetalle cdet ON ed.comida_id = cdet.comida_id
        LEFT JOIN CompraDetalle cd ON cdet.articulo_id = cd.articulo_id
        LEFT JOIN Compras c ON cd.compra_id = c.id AND c.evento_id = ?
        WHERE ed.evento_id = ?
        GROUP BY ed.momento
    ''', (evento_id, evento_id))

    # Mostrar solo total (usar precio de compra guardado en CompraDetalle)
    data_eg = [["Artículo", "Cantidad", "Total"]]
    for e in egresos:
        total_display = f"{(e.get('precio_total') or 0):.2f}"
        data_eg.append([e['nombre'], e['cantidad'], total_display])
    data_eg.append(["TOTAL", "", "", f"{total_egresos:.2f}"])
    t2 = Table(data_eg)
    t2.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black)]))
    elements.append(t2)
    # SALDO
    saldo = total_ingresos - total_egresos
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Saldo del evento: {saldo:.2f}", styles['Heading2']))

    # Gasto por comida
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Gasto por Comida", styles['Heading2']))
    data_gc = [["Momento", "Gasto"]]
    for g in gastos_por_comida:
        data_gc.append([g['momento'] or 'Sin momento', f"{g['gasto'] or 0:.2f}"])
    tg = Table(data_gc)
    tg.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black)]))
    elements.append(tg)

    doc.build(elements)
    buf.seek(0)
    safe = re.sub(r'[^a-zA-Z0-9_ ]', '', nombre).replace(' ', '_')
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f'Balance_{safe}.pdf')



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
    try:
        app.run(debug=True)
    except Exception:
        import traceback
        traceback.print_exc()
        try:
            with open('error.log', 'a', encoding='utf-8') as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise
