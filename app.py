import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
from datetime import date

DB = "finanzas_v4.db"

st.set_page_config(page_title="Mis Finanzas", page_icon="💰", layout="wide")

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

QUINCENAS = ["15 del mes", "30 del mes"]


def conectar():
    return sqlite3.connect(DB)


def hash_clave(clave):
    return hashlib.sha256(clave.encode()).hexdigest()


def ejecutar(sql, params=()):
    conn = conectar()
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()


def leer(sql, params=()):
    conn = conectar()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def crear_tablas():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        clave TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS quincenas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        anio INTEGER,
        mes TEXT,
        quincena TEXT,
        salario REAL,
        fecha TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_gastos_fijos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        nombre TEXT,
        valor REAL,
        predeterminado INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS gastos_fijos_quincena (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        anio INTEGER,
        mes TEXT,
        quincena TEXT,
        gasto_id INTEGER,
        nombre TEXT,
        valor REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS gastos_diarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        anio INTEGER,
        mes TEXT,
        quincena TEXT,
        descripcion TEXT,
        valor REAL,
        fecha TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS extras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        anio INTEGER,
        mes TEXT,
        quincena TEXT,
        descripcion TEXT,
        valor REAL,
        fecha TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tarjetas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        nombre TEXT,
        cupo_total REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_tarjeta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        tarjeta_id INTEGER,
        tipo TEXT,
        descripcion TEXT,
        valor REAL,
        fecha TEXT
    )
    """)

    conn.commit()
    conn.close()


def crear_usuario(usuario, clave):
    try:
        ejecutar(
            "INSERT INTO usuarios (usuario, clave) VALUES (?, ?)",
            (usuario, hash_clave(clave))
        )
        return True
    except Exception:
        return False


def validar_usuario(usuario, clave):
    df = leer(
        "SELECT * FROM usuarios WHERE usuario=? AND clave=?",
        (usuario, hash_clave(clave))
    )
    return not df.empty


def calcular_quincena(usuario, anio, mes, quincena):
    salario_df = leer(
        "SELECT * FROM quincenas WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
        (usuario, anio, mes, quincena)
    )

    gf_df = leer(
        "SELECT * FROM gastos_fijos_quincena WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
        (usuario, anio, mes, quincena)
    )

    gd_df = leer(
        "SELECT * FROM gastos_diarios WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
        (usuario, anio, mes, quincena)
    )

    ex_df = leer(
        "SELECT * FROM extras WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
        (usuario, anio, mes, quincena)
    )

    salario = salario_df["salario"].sum() if not salario_df.empty else 0
    gastos_fijos = gf_df["valor"].sum() if not gf_df.empty else 0
    gastos_diarios = gd_df["valor"].sum() if not gd_df.empty else 0
    extras = ex_df["valor"].sum() if not ex_df.empty else 0

    ingresos = salario + extras
    restante = ingresos - gastos_fijos - gastos_diarios

    if restante > 0:
        ahorro = restante * 0.30
        placentero = restante * 0.50
        libre = restante * 0.20
    else:
        ahorro = 0
        placentero = 0
        libre = restante

    return {
        "salario": salario,
        "extras": extras,
        "ingresos": ingresos,
        "gastos_fijos": gastos_fijos,
        "gastos_diarios": gastos_diarios,
        "ahorro": ahorro,
        "placentero": placentero,
        "libre": libre
    }


crear_tablas()

if "login" not in st.session_state:
    st.session_state.login = False

if "usuario" not in st.session_state:
    st.session_state.usuario = ""

if not st.session_state.login:
    st.title("🔐 Mis Finanzas Personales")

    tab1, tab2 = st.tabs(["Iniciar sesión", "Crear cuenta"])

    with tab1:
        with st.form("form_login"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            entrar = st.form_submit_button("Entrar")

        if entrar:
            if validar_usuario(usuario, clave):
                st.session_state.login = True
                st.session_state.usuario = usuario
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

    with tab2:
        with st.form("form_crear"):
            nuevo_usuario = st.text_input("Crear usuario")
            nueva_clave = st.text_input("Crear contraseña", type="password")
            crear = st.form_submit_button("Crear cuenta")

        if crear:
            if nuevo_usuario == "" or nueva_clave == "":
                st.warning("Llena usuario y contraseña.")
            elif crear_usuario(nuevo_usuario, nueva_clave):
                st.success("Cuenta creada. Ahora inicia sesión.")
            else:
                st.error("Ese usuario ya existe.")

else:
    usuario_actual = st.session_state.usuario

    st.title("💰 Dashboard de Finanzas Personales")

    if st.button("Cerrar sesión"):
        st.session_state.login = False
        st.session_state.usuario = ""
        st.rerun()

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        anio = st.number_input("Año", min_value=2024, max_value=2100, value=date.today().year)

    with col2:
        mes = st.selectbox("Mes", MESES, index=date.today().month - 1)

    with col3:
        quincena = st.selectbox("Quincena de trabajo", QUINCENAS)

    datos_15 = calcular_quincena(usuario_actual, anio, mes, "15 del mes")
    datos_30 = calcular_quincena(usuario_actual, anio, mes, "30 del mes")
    datos_actual = calcular_quincena(usuario_actual, anio, mes, quincena)

    total_mes = {
        "ingresos": datos_15["ingresos"] + datos_30["ingresos"],
        "gastos_fijos": datos_15["gastos_fijos"] + datos_30["gastos_fijos"],
        "gastos_diarios": datos_15["gastos_diarios"] + datos_30["gastos_diarios"],
        "ahorro": datos_15["ahorro"] + datos_30["ahorro"],
        "placentero": datos_15["placentero"] + datos_30["placentero"],
        "libre": datos_15["libre"] + datos_30["libre"]
    }

    st.subheader(f"📌 Resumen de {quincena}")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Ingresos", f"${datos_actual['ingresos']:,.0f}")
    c2.metric("Gastos fijos", f"${datos_actual['gastos_fijos']:,.0f}")
    c3.metric("Gastos diarios", f"${datos_actual['gastos_diarios']:,.0f}")
    c4.metric("Ahorro 30%", f"${datos_actual['ahorro']:,.0f}")
    c5.metric("Placentero 50%", f"${datos_actual['placentero']:,.0f}")
    c6.metric("Libre 20%", f"${datos_actual['libre']:,.0f}")

    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Quincena",
        "Catálogo gastos fijos",
        "Asignar gastos fijos",
        "Gastos diarios",
        "Dinero extra",
        "Tarjetas",
        "Extracto mensual"
    ])

    with tab1:
        st.subheader(f"💵 Registrar salario - {quincena}")

        with st.form("form_salario"):
            salario = st.number_input("Valor recibido", min_value=0.0, step=1000.0)
            guardar_salario = st.form_submit_button("Guardar salario")

        if guardar_salario:
            if salario <= 0:
                st.warning("Ingresa un valor.")
            else:
                ejecutar(
                    "INSERT INTO quincenas (usuario, anio, mes, quincena, salario, fecha) VALUES (?, ?, ?, ?, ?, ?)",
                    (usuario_actual, anio, mes, quincena, salario, str(date.today()))
                )
                st.success("Salario guardado.")
                st.rerun()

        registros = leer(
            "SELECT * FROM quincenas WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
            (usuario_actual, anio, mes, quincena)
        )

        if registros.empty:
            st.info("No hay salarios guardados.")
        else:
            for _, fila in registros.iterrows():
                col_s1, col_s2 = st.columns([4, 1])
                with col_s1:
                    st.write(f"{fila['quincena']} | ${fila['salario']:,.0f} | {fila['fecha']}")
                with col_s2:
                    if st.button("Eliminar", key=f"eliminar_salario_{fila['id']}"):
                        ejecutar("DELETE FROM quincenas WHERE id=?", (int(fila["id"]),))
                        st.success("Salario eliminado.")
                        st.rerun()

    with tab2:
        st.subheader("🏠 Catálogo de gastos fijos")

        with st.form("form_catalogo_gasto"):
            nombre = st.text_input("Nombre del gasto fijo")
            valor = st.number_input("Valor", min_value=0.0, step=1000.0)
            predeterminado = st.checkbox("Predeterminado")
            agregar = st.form_submit_button("Agregar gasto fijo")

        if agregar:
            if nombre == "" or valor <= 0:
                st.warning("Escribe nombre y valor.")
            else:
                ejecutar(
                    "INSERT INTO catalogo_gastos_fijos (usuario, nombre, valor, predeterminado) VALUES (?, ?, ?, ?)",
                    (usuario_actual, nombre, valor, 1 if predeterminado else 0)
                )
                st.success("Gasto fijo agregado al catálogo.")
                st.rerun()

        catalogo = leer(
            "SELECT * FROM catalogo_gastos_fijos WHERE usuario=?",
            (usuario_actual,)
        )

        if catalogo.empty:
            st.info("No tienes gastos fijos en el catálogo.")
        else:
            for _, fila in catalogo.iterrows():
                estado = "Predeterminado" if fila["predeterminado"] == 1 else "Opcional"
                with st.expander(f"{fila['nombre']} - ${fila['valor']:,.0f} | {estado}"):
                    nuevo_nombre = st.text_input("Nombre", value=fila["nombre"], key=f"cat_n{fila['id']}")
                    nuevo_valor = st.number_input(
                        "Valor",
                        min_value=0.0,
                        value=float(fila["valor"]),
                        step=1000.0,
                        key=f"cat_v{fila['id']}"
                    )
                    nuevo_pred = st.checkbox(
                        "Predeterminado",
                        value=True if fila["predeterminado"] == 1 else False,
                        key=f"cat_p{fila['id']}"
                    )

                    col_a, col_b = st.columns(2)

                    with col_a:
                        if st.button("Guardar cambios", key=f"cat_e{fila['id']}"):
                            ejecutar(
                                "UPDATE catalogo_gastos_fijos SET nombre=?, valor=?, predeterminado=? WHERE id=?",
                                (nuevo_nombre, nuevo_valor, 1 if nuevo_pred else 0, int(fila["id"]))
                            )
                            st.success("Actualizado.")
                            st.rerun()

                    with col_b:
                        if st.button("Eliminar", key=f"cat_d{fila['id']}"):
                            ejecutar("DELETE FROM catalogo_gastos_fijos WHERE id=?", (int(fila["id"]),))
                            ejecutar("DELETE FROM gastos_fijos_quincena WHERE gasto_id=?", (int(fila["id"]),))
                            st.success("Eliminado.")
                            st.rerun()

    with tab3:
        st.subheader(f"✅ Asignar gastos fijos a {quincena}")

        catalogo = leer(
            "SELECT * FROM catalogo_gastos_fijos WHERE usuario=?",
            (usuario_actual,)
        )

        asignados = leer(
            "SELECT * FROM gastos_fijos_quincena WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
            (usuario_actual, anio, mes, quincena)
        )

        if catalogo.empty:
            st.warning("Primero agrega gastos fijos en el catálogo.")
        else:
            st.write("Selecciona los gastos que aplican para esta quincena.")

            seleccionados = []

            for _, gasto in catalogo.iterrows():
                ya_asignado = False

                if not asignados.empty:
                    ya_asignado = int(gasto["id"]) in asignados["gasto_id"].astype(int).tolist()

                valor_default = ya_asignado or gasto["predeterminado"] == 1

                col_check, col_valor = st.columns([3, 1])

                with col_check:
                    marcado = st.checkbox(
                        f"{gasto['nombre']} - ${gasto['valor']:,.0f}",
                        value=valor_default,
                        key=f"check_{anio}_{mes}_{quincena}_{gasto['id']}"
                    )

                with col_valor:
                    valor_editado = st.number_input(
                        "Valor",
                        min_value=0.0,
                        value=float(gasto["valor"]),
                        step=1000.0,
                        key=f"valor_asig_{anio}_{mes}_{quincena}_{gasto['id']}"
                    )

                if marcado:
                    seleccionados.append((int(gasto["id"]), gasto["nombre"], valor_editado))

            if st.button("Guardar gastos fijos de esta quincena"):
                ejecutar(
                    "DELETE FROM gastos_fijos_quincena WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
                    (usuario_actual, anio, mes, quincena)
                )

                for gasto_id, nombre_gasto, valor_gasto in seleccionados:
                    ejecutar(
                        """
                        INSERT INTO gastos_fijos_quincena 
                        (usuario, anio, mes, quincena, gasto_id, nombre, valor)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (usuario_actual, anio, mes, quincena, gasto_id, nombre_gasto, valor_gasto)
                    )

                st.success("Gastos fijos guardados para esta quincena.")
                st.rerun()

            st.subheader("Gastos aplicados actualmente")

            asignados = leer(
                "SELECT * FROM gastos_fijos_quincena WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
                (usuario_actual, anio, mes, quincena)
            )

            if asignados.empty:
                st.info("Aún no hay gastos asignados a esta quincena.")
            else:
                st.dataframe(asignados[["nombre", "valor"]])

    with tab4:
        st.subheader(f"🧾 Gastos diarios - {quincena}")

        with st.form("form_gasto_diario"):
            descripcion = st.text_input("¿En qué gastaste?")
            valor_gasto = st.number_input("Valor gastado", min_value=0.0, step=1000.0)
            fecha_gasto = st.date_input("Fecha del gasto", date.today())
            guardar_gd = st.form_submit_button("Guardar gasto diario")

        if guardar_gd:
            if descripcion == "" or valor_gasto <= 0:
                st.warning("Llena descripción y valor.")
            else:
                ejecutar(
                    "INSERT INTO gastos_diarios (usuario, anio, mes, quincena, descripcion, valor, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (usuario_actual, anio, mes, quincena, descripcion, valor_gasto, str(fecha_gasto))
                )
                st.success("Gasto diario guardado.")
                st.rerun()

        gd = leer(
            "SELECT * FROM gastos_diarios WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
            (usuario_actual, anio, mes, quincena)
        )

        if not gd.empty:
            st.dataframe(gd[["descripcion", "valor", "fecha"]])

    with tab5:
        st.subheader(f"➕ Dinero extra - {quincena}")

        with st.form("form_extra"):
            descripcion_extra = st.text_input("Descripción")
            valor_extra = st.number_input("Valor extra", min_value=0.0, step=1000.0)
            fecha_extra = st.date_input("Fecha del dinero extra", date.today())
            guardar_extra = st.form_submit_button("Guardar dinero extra")

        if guardar_extra:
            if descripcion_extra == "" or valor_extra <= 0:
                st.warning("Llena descripción y valor.")
            else:
                ejecutar(
                    "INSERT INTO extras (usuario, anio, mes, quincena, descripcion, valor, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (usuario_actual, anio, mes, quincena, descripcion_extra, valor_extra, str(fecha_extra))
                )
                st.success("Dinero extra guardado.")
                st.rerun()

        ex = leer(
            "SELECT * FROM extras WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
            (usuario_actual, anio, mes, quincena)
        )

        if not ex.empty:
            st.dataframe(ex[["descripcion", "valor", "fecha"]])

    with tab6:
        st.subheader("💳 Tarjetas de crédito")

        with st.form("form_tarjeta"):
            nombre_tarjeta = st.text_input("Nombre de la tarjeta")
            cupo_total = st.number_input("Cupo total", min_value=0.0, step=1000.0)
            agregar_tarjeta = st.form_submit_button("Agregar tarjeta")

        if agregar_tarjeta:
            if nombre_tarjeta == "" or cupo_total <= 0:
                st.warning("Escribe nombre y cupo.")
            else:
                ejecutar(
                    "INSERT INTO tarjetas (usuario, nombre, cupo_total) VALUES (?, ?, ?)",
                    (usuario_actual, nombre_tarjeta, cupo_total)
                )
                st.success("Tarjeta agregada.")
                st.rerun()

        tarjetas = leer("SELECT * FROM tarjetas WHERE usuario=?", (usuario_actual,))
        movimientos = leer("SELECT * FROM movimientos_tarjeta WHERE usuario=?", (usuario_actual,))

        total_deuda = 0

        if tarjetas.empty:
            st.info("No tienes tarjetas registradas.")
        else:
            for _, tarjeta in tarjetas.iterrows():
                mov = movimientos[movimientos["tarjeta_id"] == tarjeta["id"]] if not movimientos.empty else pd.DataFrame()

                compras = mov[mov["tipo"] == "Compra"]["valor"].sum() if not mov.empty else 0
                pagos = mov[mov["tipo"] == "Pago"]["valor"].sum() if not mov.empty else 0
                deuda = compras - pagos
                disponible = tarjeta["cupo_total"] - deuda
                total_deuda += deuda

                with st.expander(f"{tarjeta['nombre']} | Debo: ${deuda:,.0f} | Disponible: ${disponible:,.0f}"):
                    a, b, c = st.columns(3)
                    a.metric("Cupo total", f"${tarjeta['cupo_total']:,.0f}")
                    b.metric("Deuda", f"${deuda:,.0f}")
                    c.metric("Disponible", f"${disponible:,.0f}")

                    with st.form(f"form_compra_{tarjeta['id']}"):
                        st.markdown("### Registrar compra")
                        desc_compra = st.text_input("Descripción compra")
                        valor_compra = st.number_input("Valor compra", min_value=0.0, step=1000.0)
                        guardar_compra = st.form_submit_button("Guardar compra")

                    if guardar_compra:
                        if desc_compra == "" or valor_compra <= 0:
                            st.warning("Llena descripción y valor.")
                        elif valor_compra > disponible:
                            st.error("La compra supera el cupo disponible.")
                        else:
                            ejecutar(
                                "INSERT INTO movimientos_tarjeta (usuario, tarjeta_id, tipo, descripcion, valor, fecha) VALUES (?, ?, ?, ?, ?, ?)",
                                (usuario_actual, int(tarjeta["id"]), "Compra", desc_compra, valor_compra, str(date.today()))
                            )
                            st.success("Compra guardada.")
                            st.rerun()

                    with st.form(f"form_pago_{tarjeta['id']}"):
                        st.markdown("### Registrar pago")
                        desc_pago = st.text_input("Descripción pago")
                        valor_pago = st.number_input("Valor pago", min_value=0.0, step=1000.0)
                        guardar_pago = st.form_submit_button("Guardar pago")

                    if guardar_pago:
                        if desc_pago == "" or valor_pago <= 0:
                            st.warning("Llena descripción y valor.")
                        elif valor_pago > deuda:
                            st.error("El pago no puede ser mayor a la deuda.")
                        else:
                            ejecutar(
                                "INSERT INTO movimientos_tarjeta (usuario, tarjeta_id, tipo, descripcion, valor, fecha) VALUES (?, ?, ?, ?, ?, ?)",
                                (usuario_actual, int(tarjeta["id"]), "Pago", desc_pago, valor_pago, str(date.today()))
                            )
                            st.success("Pago guardado.")
                            st.rerun()

                    st.markdown("### Movimientos")
                    if mov.empty:
                        st.info("Esta tarjeta no tiene movimientos.")
                    else:
                        st.dataframe(mov[["tipo", "descripcion", "valor", "fecha"]])

                    st.markdown("### Administrar tarjeta")
                    nuevo_nombre_tarjeta = st.text_input(
                        "Editar nombre",
                        value=tarjeta["nombre"],
                        key=f"edit_nombre_tarjeta_{tarjeta['id']}"
                    )
                    nuevo_cupo_tarjeta = st.number_input(
                        "Editar cupo",
                        min_value=0.0,
                        value=float(tarjeta["cupo_total"]),
                        step=1000.0,
                        key=f"edit_cupo_tarjeta_{tarjeta['id']}"
                    )

                    col_edit_t, col_delete_t = st.columns(2)

                    with col_edit_t:
                        if st.button("Guardar cambios tarjeta", key=f"guardar_tarjeta_{tarjeta['id']}"):
                            ejecutar(
                                "UPDATE tarjetas SET nombre=?, cupo_total=? WHERE id=?",
                                (nuevo_nombre_tarjeta, nuevo_cupo_tarjeta, int(tarjeta["id"]))
                            )
                            st.success("Tarjeta actualizada.")
                            st.rerun()

                    with col_delete_t:
                        st.warning("Eliminar esta tarjeta también elimina sus compras y pagos.")
                        if st.button("Eliminar tarjeta", key=f"eliminar_tarjeta_{tarjeta['id']}"):
                            ejecutar(
                                "DELETE FROM movimientos_tarjeta WHERE tarjeta_id=?",
                                (int(tarjeta["id"]),)
                            )
                            ejecutar(
                                "DELETE FROM tarjetas WHERE id=?",
                                (int(tarjeta["id"]),)
                            )
                            st.success("Tarjeta eliminada.")
                            st.rerun()

            st.error(f"TOTAL DEUDA EN TARJETAS: ${total_deuda:,.0f}")

    with tab7:
        st.subheader(f"📅 Extracto mensual - {mes} {anio}")

        q15 = pd.DataFrame({
            "Concepto": ["Ingresos", "Gastos fijos", "Gastos diarios", "Ahorro", "Placentero", "Libre"],
            "Valor": [
                datos_15["ingresos"],
                datos_15["gastos_fijos"],
                datos_15["gastos_diarios"],
                datos_15["ahorro"],
                datos_15["placentero"],
                datos_15["libre"]
            ]
        })

        q30 = pd.DataFrame({
            "Concepto": ["Ingresos", "Gastos fijos", "Gastos diarios", "Ahorro", "Placentero", "Libre"],
            "Valor": [
                datos_30["ingresos"],
                datos_30["gastos_fijos"],
                datos_30["gastos_diarios"],
                datos_30["ahorro"],
                datos_30["placentero"],
                datos_30["libre"]
            ]
        })

        resumen_mes = pd.DataFrame({
            "Concepto": ["Ingresos", "Gastos fijos", "Gastos diarios", "Ahorro", "Placentero", "Libre"],
            "Valor": [
                total_mes["ingresos"],
                total_mes["gastos_fijos"],
                total_mes["gastos_diarios"],
                total_mes["ahorro"],
                total_mes["placentero"],
                total_mes["libre"]
            ]
        })

        st.markdown("### Quincena 15")
        st.dataframe(q15)

        st.markdown("### Quincena 30")
        st.dataframe(q30)

        st.markdown("### Total del mes")
        fig = px.bar(resumen_mes, x="Concepto", y="Valor", text_auto=True, title=f"Resumen {mes} {anio}")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(resumen_mes)
