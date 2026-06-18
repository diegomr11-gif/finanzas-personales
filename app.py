import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
from datetime import date

DB = "finanzas_v3.db"

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
    CREATE TABLE IF NOT EXISTS gastos_fijos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        anio INTEGER,
        mes TEXT,
        quincena TEXT,
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
    except:
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
        "SELECT * FROM gastos_fijos WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
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
        "libre": libre,
        "restante": restante
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
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")

        if st.button("Entrar"):
            if validar_usuario(usuario, clave):
                st.session_state.login = True
                st.session_state.usuario = usuario
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

    with tab2:
        nuevo_usuario = st.text_input("Crear usuario")
        nueva_clave = st.text_input("Crear contraseña", type="password")

        if st.button("Crear cuenta"):
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

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Quincena",
        "Gastos fijos",
        "Gastos diarios",
        "Dinero extra",
        "Tarjetas",
        "Extracto mensual"
    ])

    with tab1:
        st.subheader(f"💵 Registrar salario - {quincena}")

        salario = st.number_input("Valor recibido en esta quincena", min_value=0.0, step=1000.0)

        if st.button("Guardar salario"):
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

        if not registros.empty:
            st.dataframe(registros[["anio", "mes", "quincena", "salario", "fecha"]])

    with tab2:
        st.subheader(f"🏠 Gastos fijos - {quincena}")

        nombre = st.text_input("Nombre del gasto fijo")
        valor = st.number_input("Valor del gasto fijo", min_value=0.0, step=1000.0)

        if st.button("Agregar gasto fijo"):
            if nombre == "" or valor <= 0:
                st.warning("Escribe nombre y valor.")
            else:
                ejecutar(
                    "INSERT INTO gastos_fijos (usuario, anio, mes, quincena, nombre, valor) VALUES (?, ?, ?, ?, ?, ?)",
                    (usuario_actual, anio, mes, quincena, nombre, valor)
                )
                st.success("Gasto fijo agregado.")
                st.rerun()

        gf = leer(
            "SELECT * FROM gastos_fijos WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
            (usuario_actual, anio, mes, quincena)
        )

        if gf.empty:
            st.info("No hay gastos fijos para esta quincena.")
        else:
            for _, fila in gf.iterrows():
                with st.expander(f"{fila['nombre']} - ${fila['valor']:,.0f}"):
                    nuevo_nombre = st.text_input("Nombre", value=fila["nombre"], key=f"gfn{fila['id']}")
                    nuevo_valor = st.number_input(
                        "Valor",
                        min_value=0.0,
                        value=float(fila["valor"]),
                        step=1000.0,
                        key=f"gfv{fila['id']}"
                    )

                    col_editar, col_eliminar = st.columns(2)

                    with col_editar:
                        if st.button("Guardar cambios", key=f"gfe{fila['id']}"):
                            ejecutar(
                                "UPDATE gastos_fijos SET nombre=?, valor=? WHERE id=?",
                                (nuevo_nombre, nuevo_valor, int(fila["id"]))
                            )
                            st.success("Actualizado.")
                            st.rerun()

                    with col_eliminar:
                        if st.button("Eliminar", key=f"gfd{fila['id']}"):
                            ejecutar("DELETE FROM gastos_fijos WHERE id=?", (int(fila["id"]),))
                            st.success("Eliminado.")
                            st.rerun()

    with tab3:
        st.subheader(f"🧾 Gastos diarios - {quincena}")

        descripcion = st.text_input("¿En qué gastaste?")
        valor_gasto = st.number_input("Valor gastado", min_value=0.0, step=1000.0)
        fecha_gasto = st.date_input("Fecha del gasto", date.today())

        if st.button("Guardar gasto diario"):
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

    with tab4:
        st.subheader(f"➕ Dinero extra - {quincena}")

        desc_extra = st.text_input("Descripción del dinero extra")
        valor_extra = st.number_input("Valor extra", min_value=0.0, step=1000.0)
        fecha_extra = st.date_input("Fecha del dinero extra", date.today())

        if st.button("Guardar dinero extra"):
            if desc_extra == "" or valor_extra <= 0:
                st.warning("Llena descripción y valor.")
            else:
                ejecutar(
                    "INSERT INTO extras (usuario, anio, mes, quincena, descripcion, valor, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (usuario_actual, anio, mes, quincena, desc_extra, valor_extra, str(fecha_extra))
                )
                st.success("Dinero extra guardado.")
                st.rerun()

        ex = leer(
            "SELECT * FROM extras WHERE usuario=? AND anio=? AND mes=? AND quincena=?",
            (usuario_actual, anio, mes, quincena)
        )

        if not ex.empty:
            st.dataframe(ex[["descripcion", "valor", "fecha"]])

    with tab5:
        st.subheader("💳 Tarjetas de crédito")

        nombre_tarjeta = st.text_input("Nombre de la tarjeta")
        cupo_total = st.number_input("Cupo total", min_value=0.0, step=1000.0)

        if st.button("Agregar tarjeta"):
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

                    st.markdown("### Registrar compra")
                    desc_compra = st.text_input("Descripción compra", key=f"cd{tarjeta['id']}")
                    valor_compra = st.number_input("Valor compra", min_value=0.0, step=1000.0, key=f"cv{tarjeta['id']}")

                    if st.button("Guardar compra", key=f"cb{tarjeta['id']}"):
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

                    st.markdown("### Registrar pago")
                    desc_pago = st.text_input("Descripción pago", key=f"pd{tarjeta['id']}")
                    valor_pago = st.number_input("Valor pago", min_value=0.0, step=1000.0, key=f"pv{tarjeta['id']}")

                    if st.button("Guardar pago", key=f"pb{tarjeta['id']}"):
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

                    if not mov.empty:
                        st.dataframe(mov[["tipo", "descripcion", "valor", "fecha"]])

            st.error(f"TOTAL DEUDA EN TARJETAS: ${total_deuda:,.0f}")

    with tab6:
        st.subheader(f"📅 Extracto mensual - {mes} {anio}")

        st.markdown("### Quincena 15")
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
        st.dataframe(q15)

        st.markdown("### Quincena 30")
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
        st.dataframe(q30)

        st.markdown("### Total del mes")

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

        fig = px.bar(resumen_mes, x="Concepto", y="Valor", text_auto=True, title=f"Resumen {mes} {anio}")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(resumen_mes)