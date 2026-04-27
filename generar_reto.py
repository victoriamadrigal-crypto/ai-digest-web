import os
import json
import datetime
import time
import requests

GROQ_MODEL  = "llama-3.3-70b-versatile"
OUTPUT_FILE = "reto-semanal.json"

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


def get_week_topic() -> str:
    week_num = datetime.date.today().isocalendar()[1]
    year     = datetime.date.today().year
    return TEMAS[(week_num + year) % len(TEMAS)]


def build_prompt(tema: str, semana_str: str) -> str:
    week_num = datetime.date.today().isocalendar()[1]
    return f"""Eres el director académico de un programa de formación en IA para equipos profesionales mixtos con nivel intermedio-avanzado.

Esta semana (semana {week_num} de {datetime.date.today().year}) el tema es: {tema}

Genera exactamente 4 ejercicios prácticos. Reglas estrictas:
- 2 ejercicios nivel "Basico" y 2 nivel "Intermedio"
- Mínimo 2 herramientas distintas entre Claude, Gemini y Kiro
- Los pasos deben ser TAN detallados que alguien sin experiencia pueda seguirlos: indicar URL exacta, qué elemento de la interfaz tocar, qué texto escribir, qué esperar ver en pantalla
- El prompt_ejemplo debe ser un prompt COMPLETO y real, listo para copiar y pegar, mínimo 60 palabras
- consejo_pro debe ser un truco real y accionable, no genérico

Devuelve ÚNICAMENTE JSON sin texto adicional:
{{
  "semana": "{semana_str}",
  "num_semana": {week_num},
  "tema": "{tema}",
  "titulo": "Título motivador máximo 8 palabras",
  "descripcion": "Por qué este tema importa, máximo 25 palabras",
  "ejercicios": [
    {{
      "id": 1,
      "herramienta": "Claude",
      "nivel": "Basico",
      "titulo": "Título máximo 6 palabras",
      "objetivo": "Qué aprenderá el usuario en 1 frase",
      "contexto": "Por qué este ejercicio es útil en el trabajo real, 2-3 frases",
      "prompt_ejemplo": "Prompt COMPLETO listo para copiar y pegar con todos los detalles. Mínimo 60 palabras. Debe incluir rol, contexto, tarea específica, restricciones y formato de salida esperado.",
      "pasos": [
        "Ve a [URL exacta]. Si no tienes cuenta, regístrate gratis haciendo clic en [botón concreto].",
        "Una vez dentro, haz clic en [elemento exacto de la interfaz]. Verás [descripción de lo que aparece].",
        "Copia el prompt de ejemplo que aparece arriba en esta lección.",
        "Pégalo en el campo de texto [descripción de dónde está el campo]. Antes de enviarlo, sustituye [parte X] por [instrucción de cómo adaptarlo a tu caso real].",
        "Haz clic en el botón Enviar o pulsa Ctrl+Enter. Espera entre 5 y 15 segundos a que aparezca la respuesta.",
        "Lee la respuesta y evalúa: [criterio concreto para saber si la respuesta es buena]. Si no cumple, prueba añadir al final del prompt: [sugerencia específica de refinamiento].",
        "Guarda la respuesta que más te guste copiándola a un documento o nota para referencia futura."
      ],
      "criterio_exito": "Resultado concreto y verificable que indica que el ejercicio salió bien. Debe ser específico, no genérico.",
      "tiempo_estimado": "15 min",
      "consejo_pro": "Truco avanzado específico y accionable para sacar más partido a este ejercicio"
    }}
  ]
}}"""


def call_groq(prompt: str, api_key: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    for intento in range(3):
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload, headers=headers, timeout=90
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[DEBUG] Groq intento {intento+1}: '{raw[:120]}'")
        if not raw:
            time.sleep(10)
            continue
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        start = raw.find('{')
        if start > 0:
            raw = raw[start:]
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"[WARN] JSON inválido intento {intento+1}: {e}")
            time.sleep(10)
    raise ValueError("Groq no devolvió JSON válido tras 3 intentos")


def main():
    print("[START] Generando reto semanal")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está definida")

    today      = datetime.date.today()
    monday     = today - datetime.timedelta(days=today.weekday())
    semana_str = monday.isoformat()

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("semana") == semana_str:
            print(f"[INFO] Reto de {semana_str} ya existe, saltando")
            return

    tema = get_week_topic()
    print(f"[INFO] Tema: {tema}")

    reto = call_groq(build_prompt(tema, semana_str), api_key)
    if not reto.get("ejercicios"):
        raise ValueError("No se generaron ejercicios")

    print(f"[INFO] {len(reto['ejercicios'])} ejercicios generados")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(reto, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Reto guardado en {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
        raise
