import os
import json
import datetime
import requests

GROQ_MODEL = "llama-3.3-70b-versatile"
OUTPUT_FILE = "reto-semanal.json"

# Banco de temas para rotar — evita repetición y asegura variedad
TEMAS = [
    "prompting avanzado: técnicas de few-shot y chain-of-thought",
    "uso de IA para análisis y toma de decisiones de negocio",
    "automatización de tareas repetitivas con IA",
    "escritura y comunicación profesional asistida por IA",
    "uso de IA para investigación y síntesis de información",
    "creación de sistemas de prompts reutilizables para equipos",
    "IA para análisis de datos y extracción de insights",
    "uso avanzado de contexto largo en conversaciones con IA",
    "construcción de flujos de trabajo con IA encadenada",
    "IA para revisión, mejora y feedback de documentos",
    "uso de IA en reuniones: preparación, síntesis y seguimiento",
    "personalización de asistentes IA para roles específicos",
    "detección de alucinaciones y verificación de outputs de IA",
    "IA para onboarding y formación interna de equipos",
    "uso de multimodalidad: imágenes y documentos con IA",
    "IA para generación y refinamiento de estrategias",
    "prompting para código: del problema al script funcional",
    "IA para customer success y atención al cliente",
    "uso de Kiro: spec-driven development en proyectos reales",
    "IA para creación de contenido y narrativa de marca",
    "optimización de prompts: de vago a preciso",
    "IA para análisis competitivo y benchmarking",
    "construcción de un prompt library para el equipo",
    "IA para planificación y gestión de proyectos",
    "uso ético y responsable de IA en entornos profesionales",
]

HERRAMIENTAS = ["Claude", "Gemini", "Kiro", "Claude", "Gemini"]  # pesos


def get_week_topic() -> str:
    """Selecciona el tema de la semana de forma determinista por número de semana."""
    week_num = datetime.date.today().isocalendar()[1]
    year = datetime.date.today().year
    idx = (week_num + year) % len(TEMAS)
    return TEMAS[idx]


def build_prompt(tema: str, semana_str: str) -> str:
    week_num = datetime.date.today().isocalendar()[1]

    return f"""Eres el director académico de un programa de formación en IA para equipos profesionales mixtos (técnicos y no técnicos) con nivel intermedio.

Esta semana (semana {week_num} de {datetime.date.today().year}) el tema central es: **{tema}**

Genera exactamente 4 ejercicios prácticos para que el equipo practique durante la semana. Los ejercicios deben:
- Ser realizables en 10-20 minutos cada uno
- Cubrir al menos 2 herramientas distintas entre Claude, Gemini y Kiro
- Tiene que poderse realizar con versiones gratuitas
- Tener diferentes niveles: 2 de nivel "Básico" y 2 de nivel "Intermedio"  
- Ser prácticos y aplicables a contextos profesionales reales
- Incluir instrucciones claras y un criterio de éxito medible
- NO requerir conocimientos técnicos avanzados para los básicos
- Incluir los pasos que hay que realizar para completar la practica
- Variar en formato: algunos con prompts de ejemplo, otros más abiertos

Devuelve ÚNICAMENTE un JSON válido con este esquema exacto, sin texto adicional, sin markdown, sin explicaciones:
{{
  "semana": "{semana_str}",
  "num_semana": {week_num},
  "tema": "{tema}",
  "titulo": "Título atractivo y motivador para la semana (máximo 8 palabras)",
  "descripcion": "Una frase que explique por qué este tema es importante esta semana (máximo 20 palabras)",
  "ejercicios": [
    {{
      "id": 1,
      "herramienta": "Claude",
      "nivel": "Basico",
      "titulo": "Título del ejercicio (máximo 6 palabras)",
      "objetivo": "Qué aprenderá o practicará el usuario (1 frase)",
      "instrucciones": "Pasos claros para realizar el ejercicio. Como hacerlo paso a paso. Incluye el prompt de ejemplo si aplica. Máximo 1000 palabras.",
      "criterio_exito": "Cómo sabe el usuario que lo ha hecho bien (1-2 frases)",
      "tiempo_estimado": "10 min"
    }}
  ]
}}"""


def generate_reto(semana_str: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está definida")

    tema = get_week_topic()
    print(f"[INFO] Tema de la semana: {tema}")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": build_prompt(tema, semana_str)}],
        "temperature": 0.7,
    }

    for intento in range(3):
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload, headers=headers, timeout=60
        )
        response.raise_for_status()

        raw = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[DEBUG] Respuesta Groq intento {intento+1}: '{raw[:100]}'")

        if not raw:
            print(f"[WARN] Respuesta vacía, reintentando...")
            import time; time.sleep(10)
            continue

        # Limpiar markdown si viene envuelto
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        raw = raw.strip()

        # Encontrar el JSON aunque venga con texto previo
        start = raw.find('{')
        if start > 0:
            raw = raw[start:]

        try:
            data = json.loads(raw)
            if data.get("ejercicios"):
                print(f"[INFO] {len(data['ejercicios'])} ejercicios generados")
                return data
        except json.JSONDecodeError as e:
            print(f"[WARN] JSON inválido intento {intento+1}: {e}")
            import time; time.sleep(10)

    raise ValueError("No se pudo generar el reto tras 3 intentos")


def main():
    print("[START] Generando reto semanal")

    today = datetime.date.today()
    # Lunes de esta semana
    monday = today - datetime.timedelta(days=today.weekday())
    semana_str = monday.isoformat()

    # Si ya existe el reto de esta semana, no regenerar
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("semana") == semana_str:
            print(f"[INFO] Reto de la semana {semana_str} ya existe, saltando")
            return

    reto = generate_reto(semana_str)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(reto, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Reto guardado en {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
        raise
