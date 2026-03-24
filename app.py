import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
import re 
from supabase import create_client, Client
import plotly.express as px

# Load environment variables
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

# Supabase
SUPABASE_URL = "https://oeqiugrnbfgxxqnxpudv.supabase.co"
SUPABASE_KEY = "sb_publishable_wqs-TPzsR3kyzmeuO8gFQQ_YF81Dslc"
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

# System prompt for PQRS processing
SYSTEM_PROMPT = """
You Cundi, a specialized assistant for processing PQRS (Petitions, Queries, Claims, and Requests) for CAR Colombia.

## Direcciones CAR y sus Competencias:

1. Dirección General (DGEN):
• Definir políticas generales y estratégicas de la Corporación.
• Orientar, dirigir y controlar la gestión integral de la Corporación.
• Representar legalmente a la Corporación.
• Gestionar la cooperación internacional y las alianzas estratégicas.
• Asegurar la coordinación interinstitucional para el cumplimiento de objetivos ambientales.

2. Dirección de Laboratorio e Innovación Ambiental (DLIA):
• Análisis y evaluación científica y tecnológica en laboratorios ambientales bajo Normas ISO 17025.
• Formulación y modelamiento financiero de proyectos I+D+I ambientales.
• Coordinación y participación en fondos de financiamiento para proyectos de innovación ambiental.
• Implementación de estrategias para difusión del conocimiento generado por investigación y análisis ambientales.
• Estudios de tendencias del mercado en servicios de laboratorio e innovación ambiental.

3. Dirección de Cultura Ambiental y Servicio al Ciudadano (DCASC):
• Desarrollo de políticas en atención ciudadana, educación ambiental y participación social.
• Asesoría a entidades territoriales en educación ambiental y participación ciudadana.
• Impulsar participación comunitaria en programas ambientales.
• Implementación de mecanismos de participación ciudadana en la gestión ambiental.
• Difusión de proyectos comunitarios en educación y cultura ambiental.

4. Oficina de las Tecnologías de la Información y las Comunicaciones (OTIC):
• Asesoría estratégica en TIC a la Dirección General y dependencias.
• Planeación integral del uso de TIC en la gestión institucional.
• Liderazgo en la implementación de sistemas de información para gobierno en línea.
• Soporte técnico en adquisición y mantenimiento de tecnología y bases de datos.
• Evaluación continua de sistemas informáticos para mejora tecnológica y organizacional.

5. Oficina Asesora de Comunicaciones (OAC):
• Definir y asesorar políticas de comunicación interna y externa.
• Diseñar estrategias para manejo de medios e imagen institucional.
• Coordinar y desarrollar eventos protocolarios y comunicacionales.
• Administrar registros de prensa y materiales audiovisuales institucionales.
• Desarrollar y mantener actualizado el manual de imagen corporativa

6. Oficina Asesora de Planeación (OAP):
• Formular, asesorar y evaluar políticas y estrategias para la planeación integral de la Corporación.
• Coordinar la elaboración y seguimiento al Plan de Acción y Planes Estratégicos Institucionales.
• Elaborar estudios e investigaciones sobre planeación estratégica institucional.
• Apoyar técnicamente procesos de formulación, evaluación y ajuste del presupuesto.
• Realizar seguimiento sistemático a la ejecución física y financiera de los planes institucionales.

7. Dirección de Recursos Naturales (DRN):
• Dirigir y asegurar la planeación para el adecuado cumplimiento de las funciones sobre recursos naturales.
• Controlar el talento humano asignado para la gestión ambiental y de recursos naturales.
• Representar a la Corporación ante comités y juntas ambientales.
• Establecer y perfeccionar el sistema de control interno relacionado con recursos naturales.

8. Dirección de Gestión del Ordenamiento Ambiental Territorial (DGOAT):
• Elaborar modelos y estrategias para el desarrollo urbano sostenible.
• Evaluar técnicamente planes de ordenamiento territorial de los municipios.
• Asistir técnicamente a municipios en planificación territorial con enfoque ambiental.
• Realizar seguimiento ambiental de planes parciales y proyectos municipales.
• Coordinar asistencia técnica a los Comités Ambientales Municipales.

9. Dirección Jurídica (DJUR):
• Gestionar trámites legales y jurídicos institucionales.
• Proyectar actos administrativos relacionados con licencias y sanciones ambientales.
• Responder solicitudes jurídicas externas y peticiones ambientales.
• Apoyar a las direcciones regionales en trámites ambientales jurídicos.
• Elaborar informes legales requeridos por otras entidades y autoridades.

10. Dirección de Evaluación, Seguimiento y Control Ambiental (DESCA):
• Coordinar la formulación y aplicación de directrices técnicas ambientales para los trámites administrativos.
• Supervisar técnicamente expedientes ambientales gestionados por las direcciones regionales.
• Coordinar el acompañamiento técnico para procesos de evaluación y seguimiento ambiental.
• Desarrollar instrumentos económicos para evaluación y seguimiento ambiental.
• Liderar proyectos específicos de protección y recuperación ambiental.

11. Dirección de Infraestructura Ambiental (DIA):
• Formular, ejecutar, controlar y evaluar políticas, planes y proyectos relacionados con infraestructura ambiental y saneamiento básico.
• Supervisar contratos y convenios relacionados con la infraestructura y saneamiento básico.
• Coordinar con entidades territoriales la ejecución de obras ambientales necesarias para la jurisdicción.
• Evaluar técnicamente proyectos relacionados con saneamiento básico e infraestructura ambiental.
• Emitir conceptos técnicos y participar activamente en reuniones relacionadas con infraestructura ambiental.

12. Fondo de Inversiones Ambientales de la Cuenca del Río Bogotá (FIAB):
• Apoyar la definición y evaluación técnica de planes y proyectos ambientales específicos para la cuenca del río Bogotá.
• Coordinar la elaboración técnica de procesos contractuales y proyectos ambientales relacionados con la cuenca.
• Supervisar y controlar contratos relacionados con proyectos de inversión ambiental en la cuenca.
• Coordinar programas y proyectos de infraestructura sostenible y ambiental.
• Gestionar denuncias y quejas ambientales relacionadas con la cuenca del Río Bogotá.

13. Oficina de Talento Humano (OTH):
• Gestionar procesos de selección y vinculación de personal voluntario y practicante.
• Apoyar procesos de negociación y solución de conflictos laborales.
• Proyectar actos administrativos relacionados con acuerdos laborales sindicales.
• Manejar temas relacionados con aportes parafiscales y seguridad social.
• Operar sistemas de información del área y elaborar informes de gestión del talento humano.

14. Dirección Administrativa y Financiera (DAF):
• Formular e implementar políticas administrativas, económicas y financieras.
• Realizar seguimiento integral a la contratación pública y ejecución presupuestal.
• Supervisar la gestión contable, financiera y la programación de recursos provenientes del presupuesto nacional.
• Analizar portafolio de inversiones institucionales y flujo de caja.
• Dirigir procesos internos relacionados con calidad, gestión contractual y financiera.

15. Secretaría General (SGEN):
• Liderar y controlar procesos de contratación administrativa de acuerdo con leyes vigentes.
• Asesorar jurídicamente en materia de contratación pública a las diferentes dependencias.
• Administrar procesos relacionados con adquisición, enajenación y negocios jurídicos sobre predios institucionales.
• Coordinar funciones administrativas del Consejo Directivo y Asamblea Corporativa.
• Hacer seguimiento y control riguroso al cumplimiento de contratos y convenios suscrito

16. Oficina de Control Interno (OCIN):
• Verificación y evaluación del sistema de control interno de la Corporación.
• Supervisión del cumplimiento normativo y procedimental interno.
• Evaluación periódica de riesgos administrativos, financieros y operacionales.
• Auditorías internas para asegurar eficiencia y transparencia.
• Reporte directo a la Dirección General sobre hallazgos y recomendaciones.

17. Dependencias Sede Central (SC):
• Coordinar la logística operativa y administrativa en la sede central.
• Garantizar la comunicación efectiva entre todas las áreas administrativas y técnicas.
• Supervisar procesos internos de gestión documental y archivo.
• Apoyar en procesos transversales relacionados con talento humano y servicios generales.
• Asegurar el cumplimiento de políticas administrativas institucionales.

18. Direcciones Regionales (DR):
• Implementar y supervisar localmente políticas ambientales definidas por la sede central.
• Tramitar permisos, concesiones y licencias ambientales dentro de su jurisdicción regional.
• Monitorear, evaluar y controlar el cumplimiento normativo ambiental en la región.
• Atender denuncias, quejas y solicitudes ambientales de ciudadanos locales.
• Desarrollar y coordinar actividades de educación y sensibilización ambiental en la región.

Cada Dirección Regional adicionalmente puede especializarse en aspectos particulares según su territorio específico:
19. Dirección Regional Almeidas y Guatavita (DRAG)
20. Dirección Regional Alto Magdalena (DRAM)
21. Dirección Regional Bogotá la Calera (DRBC)
22. Dirección Regional Chiquinquirá (DRCH)
23. Dirección Regional Gualivá (DRGU)
24. Dirección Regional Magdalena Centro (DRMC)
25. Dirección Regional Rio Negro (DRRN)
26. Dirección Regional Sabana Occidente (DRSO)
27. Dirección Regional Soacha (DRSOA)
28. Dirección Regional Sumapaz (DRSU)
29. Dirección Regional Tequendama (DRTE)
30. Dirección Regional Ubaté (DRUB)

When receiving a PQRS request (prefix 'PQRS:'), analyze the content and respond with a markdown table using this exact format:

| Campo                        | Valor                                                                                         |
|------------------------------|-----------------------------------------------------------------------------------------------|
| Nombre                       | [Full Name]                                                                                  |
| Cédula                       | [ID Number]                                                                                  |
| Teléfono                     | [Phone Number]                                                                              |
| Correo                       | [Email]                                                                                      |
| Municipio                    | [Location]                                                                                   |
| Asunto                       | [PQRS Description]                                                                          |
| Dirección Asignada           | [Relevant CAR Direction based on the subject]                                                 |
| Justificación                | [Brief explanation of why this direction was selected]                                         |
| Tipo de Respuesta            | [NO APLICA, INTERPONER RECURSO, RESPUESTA A OFICIO (citación, notificación, invitación, etc.)]                                                                           |
| Tipo Remitente               | [Juridica, Natural, Anonima]                                                                  |
| Fecha                        | [Date identified in the text]                                                                  |
| Proceso especial             | [No Aplica, Thomas van der Hammen, Río Bogotá, Cerros Orientales, Auditorías - Entes de Control, DRMI Fúquene, Reporte de licencias de parcelación y construcción] |
| Tipo de Tramite              | [Acciones Constitucionales, Certificación Ambiental para propuesta de Concesión Minera, Curadurías, DP Congreso de la República Ley 5/92 10 días, DP Congreso de la República Ley 5/92 48h, DP Interes Particular Autorizaciones ,  DP Congreso de la República Ley 5/92 5 días, Dp de Consulta, DP en Cumplimiento de Deber Legal ,Dp de interés Particular (Solicitud Certificaciones Cto, pasantias laborales) , Dp, de oficio Permisivos, Dp Defensoria del Pueblo Ley 5/92 5 días, Dp En cumplimiento de un deber legal (Permisos), DP PERMISIVOS, Dp Queja Ambiental (Afectación ambiental), Dp Queja por atención al servicio), DP Queja por Olores Ofensivos, DP Reclamo (Contra Funciones/Funcionarios CAR), DP Recursos - Acuerdos 10 y 09, DP Recursos(15 Días), DP Recursos (60 Días), DP Recursos Exenciones Cobro Coactivo, DP Solicitud de Copias, DP Solicitud de Exepciones de Cobro Coactivo - Estatuto Tributario, DP Solicitud de Exepciones y Reclamaciones Facturación, Documento Informacion Respuesta, Documento Remicion, Procesos Contractuales , Documento Remision Informacion, Documentos para información Institucional - Remisión Información, Ingreso por Redes Sociales, Ingreso PQR, Memorando Interno, Observaciones y/o recomendaciones POMCAS Decreto 2076-2015, Radicación Pago Copias, Radicación Trámites de Oficio o inicidados por CAR, Trámite Res 511 de 2012 Reserva Forestal Cuenca Alta Río Bogotá, Trámites Autodeclaración de Vertimientos Res. 1792 de 2013] |
| Departamento                  | [Department Name]                                                                              |
| Vereda                       | [If applicable, name of the vereda]                                                          |
| Predio                       | [If the property(predio) name is provided, include it]                                                |
| Medio de documento           | Oficio                                                                                        |
| Numero de Folios             | 1                                                                                            |
| Anexos                        | VACIO                                                                                         |
| Observaciones                | [Summary of what the person is asking in the PQRS]                                            |
| Copia a                      | VACIO                                                                                         |
| Quien Entrega                | [Empresa de mensajería, Persona Natural]                                                       |
| Atención Preferencial        | [Adulto Mayor, Desplazado, Discapacidad física, Discapacidad Mental, Discapacidad Sensorial, Grupos Étnicos Minoritarios, Mujer Embarazada, Niños o Adolescentes, Periodista, Veterano de la Fuerza Pública] |

Rules for handling PQRS and direction assignment:
1. Carefully analyze the subject matter of the PQRS to select the most appropriate direction based on their competencies.
2. Provide a brief justification for the assignment.
3. If the subject involves multiple directions, select the primary one most relevant to the main issue.
4. The answer should ALWAYS be in Spanish.
5. If the request doesn't explicitly mention CAR, still process and classify it.
6. If the user provides a PQRS but it is very messy or lacks essential information (like Name, ID, Location, Subject, or Contact info), DO NOT generate the table immediately. Instead, kindly and conversationally ask the user step-by-step for the missing information until you have enough data to fill the required fields.
7. Only generate the markdown table when you have gathered sufficient information (or if the initial request already has enough details).
8. You can select multiple options for the "Tipo de Tramite" field.
9. If the PQRS has a specific location (municipality, vereda, predio), cross it with the local directions to determine the appropriate one.

For regular conversation, respond naturally as a helpful assistant with knowledge about CAR's structure and functions y guía al usuario amablemente.
"""

class StreamHandler(BaseCallbackHandler):
    def __init__(self, container):
        self.container = container
        self.text = ""
        
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        display_response(self.text, self.container)

def extract_table_data(markdown_text):
    try:
        table_pattern = r'\|.*\|'
        table_rows = re.findall(table_pattern, markdown_text)
        
        if not table_rows:
            return None, None
            
        headers = ['Campo', 'Valor']
        data = []
        for row in table_rows[2:]:
            values = [col.strip() for col in row.split('|')[1:-1]]
            if len(values) == 2:
                data.append(values)
        
        df = pd.DataFrame(data, columns=headers)
        pre_table = markdown_text.split('|')[0].strip()
        post_table = markdown_text.split('|')[-1].strip()
        other_text = f"{pre_table}\n\n{post_table}".strip()
        
        return df, other_text
    except Exception as e:
        return None, None

def save_to_supabase(df):
    if not supabase:
        st.error("Error: Cliente de Supabase no inicializado. Revisa tus credenciales.")
        return False
        
    try:
        data_dict = {}
        for index, row in df.iterrows():
            key = str(row['Campo']).lower().replace(' ', '_').strip()
            # Handle special characters for supabase columns
            key = ''.join(c for c in key if c.isalnum() or c == '_')
            data_dict[key] = str(row['Valor'])
            
        # Intentamos insertar en la tabla 'pqrs'
        response = supabase.table("pqrs").insert(data_dict).execute()
        return True
    except Exception as e:
        st.error(f"Error al guardar en Supabase: Verifica que la tabla 'pqrs' exista con los nombres de columnas correctos (ej: nombre, cedula). Detalle: {str(e)}")
        return False

def display_response(response_text, container):
    if '|' in response_text:
        df, other_text = extract_table_data(response_text)
        if df is not None:
            if other_text:
                container.markdown(other_text)
            
            container.markdown("### Información PQRS")
            styled_df = df.style.set_properties(**{
                'background-color': '#ffffff',
                'color': '#03688b',
                'border': '2px solid #029b9a'
            })
            
            container.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Save the current PQRS to session state for the Confirmation UI
            st.session_state['current_pqrs'] = df
        else:
            container.markdown(response_text)
    else:
        container.markdown(response_text)

def get_chat_response(prompt, temperature=0.3):
    try:
        response_placeholder = st.empty()
        stream_handler = StreamHandler(response_placeholder)
        
        chat_model = ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            api_key=API_KEY,
            streaming=True,
            callbacks=[stream_handler]
        )
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        if "messages" in st.session_state:
            for msg in st.session_state.messages[-3:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(SystemMessage(content=msg["content"]))
        
        response = chat_model.invoke(messages)
        return stream_handler.text
        
    except Exception as e:
        return f"Error: {str(e)}"

def render_dashboard():
    st.header("📊 Dashboard de Gestión Institucional", anchor=False)
    
    if not supabase:
        st.error("Supabase no está configurado correctamente para cargar métricas.")
        return
        
    try:
        response = supabase.table("pqrs").select("*").execute()
        data = response.data
        if not data:
            st.info("No hay datos suficientes registrados en la base de datos (tabla 'pqrs') para generar gráficos.")
            return
            
        df = pd.DataFrame(data)
        
        # Variables: Municipio, Dirección", Tipo Res, Tipo Rem, Fecha, Proceso, Trámite, Dpto, Atención
        # Plot 1: Municipio
        if 'municipio' in df.columns:
            m_count = df['municipio'].value_counts().reset_index()
            fig1 = px.bar(m_count, x='municipio', y='count', title="PQRS por Municipio", color_discrete_sequence=['#029b9a'])
            st.plotly_chart(fig1, use_container_width=True)
            
        col1, col2 = st.columns(2)
        with col1:
            if 'direccion_asignada' in df.columns:
                fig2 = px.pie(df['direccion_asignada'].value_counts().reset_index(), values='count', names='direccion_asignada', title="Distribución por Dirección Asignada", color_discrete_sequence=['#03688b', '#ed7403', '#f8b101', '#acca14', '#029b9a'])
                st.plotly_chart(fig2, use_container_width=True)
        with col2:
            if 'departamento' in df.columns:
                fig3 = px.pie(df['departamento'].value_counts().reset_index(), values='count', names='departamento', title="Afectación por Departamento", color_discrete_sequence=['#acca14', '#029b9a'])
                st.plotly_chart(fig3, use_container_width=True)
                
        col3, col4 = st.columns(2)
        with col3:
            if 'tipo_remitente' in df.columns:
                fig4 = px.pie(df['tipo_remitente'].value_counts().reset_index(), values='count', names='tipo_remitente', title="Tipo de Remitente", color_discrete_sequence=['#f8b101', '#ed7403'])
                st.plotly_chart(fig4, use_container_width=True)
        with col4:
            if 'tipo_respuesta' in df.columns:
                fig5 = px.bar(df['tipo_respuesta'].value_counts().reset_index(), x='tipo_respuesta', y='count', title="Tipo de Respuesta Requerida", color_discrete_sequence=['#03688b'])
                st.plotly_chart(fig5, use_container_width=True)
                
        col5, col6 = st.columns(2)
        with col5:
            if 'atencion_preferencial' in df.columns:
                fig6 = px.pie(df['atencion_preferencial'].value_counts().reset_index(), values='count', names='atencion_preferencial', title="Atención Preferencial", color_discrete_sequence=['#029b9a', '#acca14'])
                st.plotly_chart(fig6, use_container_width=True)
        with col6:
            if 'proceso_especial' in df.columns:
                fig7 = px.pie(df['proceso_especial'].value_counts().reset_index(), values='count', names='proceso_especial', title="Procesos Especiales", color_discrete_sequence=['#ed7403', '#f8b101'])
                st.plotly_chart(fig7, use_container_width=True)
                
        if 'tipo_de_tramite' in df.columns or 'tipo_tramite' in df.columns:
            tr_col = 'tipo_de_tramite' if 'tipo_de_tramite' in df.columns else 'tipo_tramite'
            tr_count = df[tr_col].value_counts().reset_index().head(10)
            fig8 = px.bar(tr_count, x='count', y=tr_col, orientation='h', title="Top 10 Tipos de Trámite", color_discrete_sequence=['#03688b'])
            st.plotly_chart(fig8, use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar datos del Dashboard: {str(e)}")

def main():
    st.set_page_config(page_title="CARresponde", layout="wide", page_icon="📝")
    
    # Custom CSS
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: #ffffff;
    }}
    /* Main titles and markdown text */
    h1, h2, h3, h4, p, span {{
        color: #03688b !important;
    }}
    /* Primary buttons */
    .stButton>button {{
        background-color: #029b9a !important;
        color: #ffffff !important;
        border: none;
        border-radius: 5px;
    }}
    .stButton>button:hover {{
        background-color: #03688b !important;
        color: #ffffff !important;
    }}
    /* Tabs custom styling */
    button[data-baseweb="tab"] {{
        color: #03688b !important;
        font-weight: bold;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: #ffffff !important;
        border-bottom: 4px solid #ed7403 !important;
        color: #ed7403 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Validate OpenAI key
    if not API_KEY:
        st.error("Error: OPENAI_API_KEY no fue encontrada en las variables de entorno.")
        st.stop()

    with st.sidebar:
        try:
            st.image("logo.png", use_container_width=True)
        except:
            st.title("CAR Cundinamarca")
        
        st.markdown("**Bienvenido al Sistema de Gestión de PQRS**")
        st.markdown("Clasifica tus requerimientos y visualiza estadísticas en tiempo real.")
        
        if st.button("Borrar Historial del Chat"):
            st.session_state.messages = []
            st.session_state.current_pqrs = None
            st.rerun()

    tab_chat, tab_dash = st.tabs(["🤖 Asistente Virtual", "📈 Dashboard Estadístico"])
    
    with tab_chat:
        st.title("CAResponde", anchor=False)
        st.markdown("**Soy Cundi, tú asistente virtual para la CAR.** Radica aquí tus PQRS de forma estructurada.")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant" and '|' in message["content"]:
                    display_response(message["content"], st)
                else:
                    st.markdown(message["content"])

        # Peticion de Confirmación
        if 'current_pqrs' in st.session_state and st.session_state['current_pqrs'] is not None:
            st.markdown("---")
            st.warning("**¿Deseas radicar y enviar esta PQRS al sistema central de la CAR (Supabase)?**")
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("✅ Sí, Radicar PQRS"):
                    success = save_to_supabase(st.session_state['current_pqrs'])
                    if success:
                        st.success("¡PQRS enviada exitosamente a la base de datos!")
                        st.session_state['current_pqrs'] = None
                        # We use time.sleep(1) to let the success message display before clearing it out, or just leave it until next response.
            with col2:
                if st.button("❌ Cancelar / Ignorar"):
                    st.session_state['current_pqrs'] = None
                    st.rerun()

        if prompt := st.chat_input("Escribe tu solicitud acá..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                is_pqrs = prompt.upper().startswith("PQRS:")
                if is_pqrs:
                    pqrs_content = prompt[5:].strip()
                    response = get_chat_response(pqrs_content)
                else:
                    response = get_chat_response(prompt)
                
                # Check directly format for capturing the Table
                if '|' in response:
                    df, _ = extract_table_data(response)
                    if df is not None:
                        st.session_state['current_pqrs'] = df
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

    with tab_dash:
        render_dashboard()

if __name__ == "__main__":
    main()
