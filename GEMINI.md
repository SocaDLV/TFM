# Reglas Globales del Proyecto TFM (Co-Simulador LLMSimulator + BookSim2)

1. **Fuente Única de Verdad (Documentación Maestra):**
   - El archivo `docs/TFM_Technical_Bible.md` (y su espejo en Word `docs/TFM_Technical_Bible.docx`) contiene toda la arquitectura, flujo de ejecución, fórmulas matemáticas y decisiones de diseño de `LLMSimulator-orig`, `booksim2` y nuestro entorno de co-simulación `LLMSimulator`.
   - **Lectura obligatoria:** Antes de responder preguntas arquitectónicas complejas o modificar el motor C++, consulta `docs/TFM_Technical_Bible.md`.
   - **Actualización continua:** Siempre que realices un nuevo hallazgo de código o modifiques el comportamiento del co-simulador o de los scripts de análisis, actualiza `docs/TFM_Technical_Bible.md` y regenera inmediatamente el documento Word ejecutando:
     `pandoc docs/TFM_Technical_Bible.md -o docs/TFM_Technical_Bible.docx`
     `gio mount "google-drive://ivan.planero@gmail.com" 2>/dev/null || true; GDRIVE_DIR=$(ls -d /run/user/$(id -u)/gvfs/google-drive* | head -n 1) && gio copy docs/TFM_Technical_Bible.md "$GDRIVE_DIR/0ADfvG_TWEGIrUk9PVA/TFM_Docs/" && gio copy docs/TFM_Technical_Bible.docx "$GDRIVE_DIR/0ADfvG_TWEGIrUk9PVA/TFM_Docs/"`
