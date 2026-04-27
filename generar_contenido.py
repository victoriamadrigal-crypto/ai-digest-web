import os
import json
import datetime
import time
import requests

GROQ_MODEL      = "llama-3.3-70b-versatile"
OUTPUT_FILE     = "contenido-semanal.json"
HISTORICO_FILE  = "historico-lecciones.json"

TEMAS = [
    "prompting avanzado: few-shot, chain-of-thought y self-consistency",
    "agentes IA: cuándo delegar decisiones a la IA",
    "RAG y gestión de conocimiento con IA",
    "evaluación y benchmarking de modelos para casos de uso reales",
    "IA multimodal: combinar texto, imagen y audio",
    "fine-tuning vs prompting: cuándo usar cada enfoque",
    "seguridad y privacidad al usar IA en entornos empresariales",
    "IA para análisis de sentimiento y voz del cliente",
    "automatización avanzada: MCP y herramientas externas",
    "construcción de pipelines de IA para producción",
    "IA para generación y validación de hipótesis de negocio",
    "prompt engineering para modelos de razonamiento (o1, R1)",
    "IA para síntesis de investigación académica y técnica",
    "sistemas multi-agente: coordinación y paralelización",
    "IA para detección de sesgos y fairness",
    "LLMs para análisis de código legacy y refactorización",
    "IA para generación de datos sintéticos de entrenamiento",
    "optimización de costes en pipelines de IA",
    "IA conversacional: diseño de flujos y manejo de contexto",
    "evaluación de outputs: métricas y feedback loops",
    "IA para aceleración de ciclos de investigación y desarrollo",
    "integración de IA en herramientas existentes via API",
    "IA para toma de decisiones bajo incertidumbre",
    "memoria y personalización en sistemas de IA",
    "tendencias emergentes: modelos pequeños y IA en el edge",
]

HERRAMIENTAS = ["Claude", "Gemini", "Kiro"]


def get_week_topic() -> str:
    week_num = datetime.date.today().isocalendar()[1]
    year     = datetime.date.today().year
    return TEMAS[(week_num + year + 7) % len(TEMAS)]  # +7 para no coincidir con reto


def build_tip_prompt(tema: str, semana_str: str) -> str:
    return f"""Eres un experto en IA con experiencia práctica en entornos empresariales.

Genera un TIP DE LA SEMANA sobre: {tema}

El tip debe:
- Ser una técnica concreta, accionable y poco conocida
- Explicar EXACTAMENTE cómo aplicarla con un ejemplo real
- Incluir el prompt o comando concreto si aplica
- Ser útil para profesionales con nivel intermedio-avanzado
- No ser genérico ni obvio

Devuelve ÚNICAMENTE JSON sin texto adicional:
{{
  "semana": "{semana_str}",
  "tema": "{tema}",
  "emoji": "emoji relevante",
  "titulo": "Título del tip máximo 8 palabras",
  "resumen": "Una frase que resume el tip (máximo 20 palabras)",
  "explicacion": "Explicación detallada de la técnica, por qué funciona y cuándo usarla. 3-4 frases.",
  "ejemplo_prompt": "Prompt o ejemplo concreto y completo listo para usar. Mínimo 40 palabras.",
  "cuando_usarlo": "2-3 situaciones concretas del trabajo real donde aplicar este tip",
  "herramienta": "Claude o Gemini o Kiro o Todas"
}}"""


def build_lecciones_prompt(tema: str, semana_str: str) -> str:
    week_num = datetime.date.today().isocalendar()[1]
    return f"""Eres el director académico de un programa avanzado de formación en IA para profesionales con nivel intermedio-avanzado.

Esta semana (semana {week_num}) el tema es: {tema}

Genera exactamente 4 lecciones extra de nivel avanzado. Cada lección debe:
- Cubrir un aspecto diferente del tema
- Ser más técnica y profunda que las lecciones base del curso
- Incluir teoría + ejemplo práctico + ejercicio para practicar
- El prompt_practica debe ser un prompt COMPLETO listo para copiar (mínimo 80 palabras)
- Los pasos_practica deben ser detallados como si el usuario no supiera nada
- Variar herramientas: usa Claude, Gemini y Kiro
- Duración: 20-30 minutos cada una

Devuelve ÚNICAMENTE JSON sin texto adicional:
{{
  "semana": "{semana_str}",
  "num_semana": {week_num},
  "tema": "{tema}",
  "lecciones": [
    {{
      "id": "extra-{week_num}-1",
      "semana": "{semana_str}",
      "herramienta": "Claude",
      "nivel": "Avanzado",
      "titulo": "Título de la lección máximo 7 palabras",
      "subtitulo": "Descripción en 1 frase de qué aprenderá",
      "duracion": "25 min",
      "teoria": {{
        "concepto": "Nombre del concepto o técnica principal",
        "explicacion": "Explicación clara y detallada del concepto. 3-4 párrafos. Incluye por qué es importante, cómo funciona y cuándo usarlo.",
        "analogia": "Una analogía del mundo real que ayude a entender el concepto",
        "cuando_usarlo": "Lista de 3-4 situaciones concretas donde aplicar esta técnica"
      }},
      "ejemplo": {{
        "caso": "Descripción de un caso de uso real y concreto",
        "prompt_malo": "Ejemplo de cómo NO hacerlo (prompt incorrecto o subóptimo)",
        "prompt_bueno": "Ejemplo de cómo SÍ hacerlo correctamente. Prompt COMPLETO mínimo 60 palabras.",
        "por_que_mejor": "Explicación de por qué el prompt bueno es mejor"
      }},
      "practica": {{
        "titulo": "Título del ejercicio práctico",
        "objetivo": "Qué conseguirá el usuario al completarlo",
        "prompt_practica": "Prompt COMPLETO listo para copiar y pegar. Mínimo 80 palabras. Incluye rol, contexto detallado, tarea, restricciones y formato de salida.",
        "pasos": [
          "Paso 1 muy detallado: URL exacta, qué hacer, qué esperar ver",
          "Paso 2 muy detallado",
          "Paso 3 muy detallado",
          "Paso 4: cómo evaluar el resultado y refinarlo",
          "Paso 5: cómo guardar y aplicar lo aprendido"
        ],
        "criterio_exito": "Resultado específico y verificable que indica éxito"
      }},
      "recursos": [
        "Recurso o técnica adicional relacionada para profundizar"
      ]
    }}
  ]
}}"""


def call_groq(prompt: str, api_key: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    for intento in range(3):
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload, headers=headers, timeout=120
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()
        print(f"[DEBUG] Groq intento {intento+1}: '{raw[:120]}'")
        if not raw:
            time.sleep(15)
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
            time.sleep(15)
    raise ValueError("Groq no devolvió JSON válido tras 3 intentos")


def load_historico() -> list:
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_historico(historico: list):
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def main():
    print("[START] Generando contenido semanal (tip + lecciones extra)")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está definida")

    today      = datetime.date.today()
    monday     = today - datetime.timedelta(days=today.weekday())
    semana_str = monday.isoformat()

    # Comprobar si ya existe el contenido de esta semana
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("semana") == semana_str:
            print(f"[INFO] Contenido de {semana_str} ya existe, saltando")
            return

    tema = get_week_topic()
    print(f"[INFO] Tema semanal: {tema}")

    # Generar tip de la semana
    print("[INFO] Generando tip de la semana...")
    tip = call_groq(build_tip_prompt(tema, semana_str), api_key)
    print(f"[INFO] Tip generado: {tip.get('titulo', '?')}")

    # Pausa entre llamadas
    time.sleep(5)

    # Generar lecciones extra
    print("[INFO] Generando 4 lecciones extra...")
    lecciones_data = call_groq(build_lecciones_prompt(tema, semana_str), api_key)
    lecciones = lecciones_data.get("lecciones", [])
    print(f"[INFO] {len(lecciones)} lecciones generadas")

    # Guardar contenido semanal actual
    contenido = {
        "semana": semana_str,
        "tema": tema,
        "tip": tip,
        "lecciones": lecciones,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Contenido guardado en {OUTPUT_FILE}")

    # Actualizar histórico de lecciones
    historico = load_historico()

    # Evitar duplicados de la misma semana
    historico = [e for e in historico if e.get("semana") != semana_str]

    # Añadir las lecciones de esta semana al histórico
    for leccion in lecciones:
        historico.append({
            "semana":      semana_str,
            "tema":        tema,
            "id":          leccion.get("id"),
            "herramienta": leccion.get("herramienta"),
            "nivel":       leccion.get("nivel"),
            "titulo":      leccion.get("titulo"),
            "subtitulo":   leccion.get("subtitulo"),
            "duracion":    leccion.get("duracion"),
        })

    # Guardar histórico completo (máximo 200 entradas)
    historico = historico[-200:]
    save_historico(historico)
    print(f"[INFO] Histórico actualizado: {len(historico)} lecciones totales")
    print("[DONE] Contenido semanal generado correctamente")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
        raise
