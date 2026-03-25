import os
import re
import json
import ssl
import unicodedata
import warnings
warnings.filterwarnings('ignore')

# ── Patch SSL globally BEFORE any network library is imported ──────────────────
# Needed on Windows corporate networks with self-signed certificates
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

_orig_create_default_context = ssl.create_default_context
def _patched_ssl_context(*args, **kwargs):
    ctx = _orig_create_default_context(*args, **kwargs)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
ssl.create_default_context = _patched_ssl_context

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass
# ───────────────────────────────────────────────────────────────────────────────

import pandas as pd
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from supabase import create_client, Client

load_dotenv()

# Fix SSL certificate verification for corporate/Windows networks

API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = "https://oeqiugrnbfgxxqnxpudv.supabase.co"
SUPABASE_KEY = "sb_publishable_wqs-TPzsR3kyzmeuO8gFQQ_YF81Dslc"

try:
    import httpx
    from supabase import ClientOptions
    _no_ssl_client = httpx.Client(verify=False)
    supabase: Client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(httpx_client=_no_ssl_client)
    )
except Exception:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None

app = Flask(__name__)

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
| Tipo de Respuesta            | [NO APLICA, INTERPONER RECURSO, RESPUESTA A OFICIO]                                          |
| Tipo Remitente               | [Juridica, Natural, Anonima]                                                                  |
| Fecha                        | [Date identified in the text]                                                                  |
| Proceso especial             | [No Aplica, Thomas van der Hammen, Río Bogotá, Cerros Orientales, etc.]                       |
| Tipo de Tramite              | [Select from the applicable types]                                                            |
| Departamento                 | [Department Name]                                                                              |
| Vereda                       | [If applicable]                                                                               |
| Predio                       | [If applicable]                                                                               |
| Medio de documento           | Oficio                                                                                        |
| Numero de Folios             | 1                                                                                            |
| Anexos                       | VACIO                                                                                         |
| Observaciones                | [Summary of what the person is asking]                                                        |
| Copia a                      | VACIO                                                                                         |
| Quien Entrega                | [Empresa de mensajería, Persona Natural]                                                       |
| Atención Preferencial        | [Adulto Mayor, Desplazado, Discapacidad, etc.]                                                |

Rules:
1. Carefully analyze the subject matter to select the most appropriate direction.
2. Provide a brief justification for the assignment.
3. If the subject involves multiple directions, select the primary one.
4. The answer should ALWAYS be in Spanish.
5. If the request doesn't explicitly mention CAR, still process and classify it.
6. If the PQRS lacks essential information, ask conversationally for missing data before generating the table.
7. Only generate the markdown table when you have sufficient information.
8. You can select multiple options for "Tipo de Tramite".
9. If the PQRS has a specific location, cross it with local directions.

For regular conversation, respond naturally as a helpful assistant with knowledge about CAR's structure and functions.
"""


def extract_table_data(markdown_text):
    try:
        table_pattern = r'\|.*\|'
        table_rows = re.findall(table_pattern, markdown_text)
        if not table_rows:
            return None, markdown_text
        headers = ['Campo', 'Valor']
        data = []
        for row in table_rows[2:]:
            values = [col.strip() for col in row.split('|')[1:-1]]
            if len(values) == 2:
                data.append(values)
        df = pd.DataFrame(data, columns=headers)
        # Extract text before/after table
        lines = markdown_text.split('\n')
        pre, post, in_table = [], [], False
        for line in lines:
            if re.match(r'\|.*\|', line.strip()):
                in_table = True
            elif in_table:
                post.append(line)
            else:
                pre.append(line)
        other_text = '\n'.join(pre + post).strip()
        return df, other_text
    except Exception:
        return None, markdown_text


def _normalize_key(text):
    """Lowercase, remove accents, replace spaces with underscores, keep only alnum+underscore."""
    # Decompose unicode and remove combining characters (accents)
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_str = ''.join(c for c in nfkd if not unicodedata.combining(c))
    key = ascii_str.lower().strip().replace(' ', '_')
    key = re.sub(r'[^a-z0-9_]', '', key)
    return key


def save_to_supabase(fields):
    if not supabase:
        return False, "Cliente Supabase no inicializado"
    try:
        data_dict = {}
        for campo, valor in fields.items():
            key = _normalize_key(campo)
            data_dict[key] = str(valor)
        supabase.table("pqrs").insert(data_dict).execute()
        return True, "PQRS radicada exitosamente"
    except Exception as e:
        return False, str(e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'logo.png', mimetype='image/png')


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('prompt', '')
    history = data.get('history', [])

    def generate():
        try:
            chat_model = ChatOpenAI(
                model="gpt-4o",
                temperature=0.3,
                api_key=API_KEY,
                streaming=True,
            )
            messages = [SystemMessage(content=SYSTEM_PROMPT)]
            for msg in history[-6:]:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                else:
                    messages.append(SystemMessage(content=msg['content']))
            messages.append(HumanMessage(content=prompt))

            full_text = ""
            for chunk in chat_model.stream(messages):
                token = chunk.content
                full_text += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            # After streaming, check if there's a table
            df, other_text = extract_table_data(full_text)
            if df is not None:
                table_data = df.to_dict('records')
                yield f"data: {json.dumps({'table': table_data, 'other_text': other_text})}\n\n"

            yield f"data: {json.dumps({'done': True, 'full_text': full_text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/save_pqrs', methods=['POST'])
def save_pqrs():
    data = request.json
    fields = data.get('fields', {})
    success, message = save_to_supabase(fields)
    return jsonify({'success': success, 'message': message})


@app.route('/api/dashboard')
def dashboard():
    if not supabase:
        return jsonify({'error': 'Supabase no configurado'})
    try:
        response = supabase.table("pqrs").select("*").execute()
        return jsonify({'data': response.data})
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
