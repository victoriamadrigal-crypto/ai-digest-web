# 🤖 AI Digest Web

Resumen diario automático de noticias de IA publicado como página web en GitHub Pages.
Se actualiza solo cada mañana de lunes a viernes.

## URL pública
```
https://TU_USUARIO.github.io/TU_REPO
```

## Configuración

### 1. Activar GitHub Pages
Settings → Pages → Source → **GitHub Actions** → Guardar

### 2. Añadir el secret de Groq
- Obtén una API key gratuita en [console.groq.com](https://console.groq.com)
- En GitHub: Settings → Secrets → Actions → **New secret**
  - Nombre: `GROQ_API_KEY`
  - Valor: tu key de Groq

### 3. Primer test
Actions → AI Digest Web → **Run workflow**

## Fuentes incluidas
| Fuente | Idioma |
|---|---|
| Arxiv cs.AI + cs.LG | Inglés |
| The Batch (DeepLearning.AI) | Inglés |
| VentureBeat AI | Inglés |
| MIT Technology Review | Inglés |
| MIT Technology Review España | Español |
| Xataka IA | Español |
| Hipertextual | Español |
| El País Tecnología | Español |

## Estructura
```
.
├── digest.py                       # Script principal
├── requirements.txt                # feedparser + requests
├── seen_urls.json                  # Cache anti-duplicados (auto-actualizado)
├── index.html                      # Página generada (auto-generada)
└── .github/workflows/
    └── ai-digest-web.yml          # GitHub Actions
```
