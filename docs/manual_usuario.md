# Manual de usuario — Dashboard

El dashboard (Streamlit) permite estimar la **probabilidad de longevidad** y la
**edad biológica** a partir de biomarcadores, y explorar los resultados según tu
rol. Se organiza en **tres vistas por audiencia**.

> ⚠️ **Aviso.** Proyecto académico/educativo. Las estimaciones provienen de un
> modelo entrenado sobre datos poblacionales NHANES y **no constituyen consejo
> médico** ni diagnóstico.

## Acceso
- **URL local:** `http://localhost:8501`
- Requiere que el backend esté corriendo (`http://localhost:8000`). Si el dashboard
  muestra "modelos no disponibles", ver la [guía de despliegue](despliegue.md).

## Vista Operativa — Predictor
Pensada para el uso directo (un profesional ingresando datos de una persona).

1. **Completá el formulario.** Los campos se generan desde el contrato del modelo:
   - **Requeridos (~11):** sexo, etnia, peso, talla, IMC, cintura, presión
     sistólica/diastólica, pulso, colesterol total, glucosa.
   - **Opcionales:** educación, estado civil, tamaño del hogar, índice de pobreza,
     medidas antropométricas extra. Si los dejás vacíos, el modelo los **imputa**.
2. **Edad cronológica (opcional).** No influye en la predicción; solo se usa para
   mostrar la diferencia con la edad biológica estimada.
3. **Resultados:**
   - **¿Es longevo?** y **probabilidad** (clasificación `IS_LONGEVO`, edad ≥ 70).
   - **Edad biológica estimada** y, si ingresaste tu edad, el **gap**
     (`biológica − cronológica`): negativo = "envejecés mejor que tu edad".
   - **Waterfall SHAP:** qué biomarcadores empujaron el resultado y en qué dirección.

## Vista Técnica
Para perfiles de datos/ML. Muestra:
- **Métricas del modelo** (accuracy / matriz de confusión de clasificación; MAE de
  regresión) desde `/metrics`.
- **Importancia de features** y **explicabilidad SHAP** del caso evaluado.
- Detalle del contrato y el preprocesamiento.

## Vista Ejecutiva
Para audiencia de negocio/gestión. Resume el uso agregado (desde `/aggregates`):
- **KPIs:** total de evaluaciones, % clasificado como longevo, edad biológica
  promedio, gap promedio.
- **Distribución de edad biológica** de la población evaluada.
- Lenguaje orientado a valor de negocio, sin jerga técnica.

## Interpretación rápida
| Resultado | Lectura |
|---|---|
| Probabilidad alta de longevidad | El perfil se asemeja al de personas ≥ 70 sanas del dataset |
| Gap negativo | Edad biológica menor que la cronológica |
| Gap positivo | Edad biológica mayor que la cronológica |
| Feature con SHAP positivo | Empuja hacia "longevo" |

## Problemas comunes
| Síntoma | Causa probable | Solución |
|---|---|---|
| "Modelos no disponibles" | No se bendijo el modelo | `kedro run --pipeline serving` |
| Error 422 al predecir | Falta un requerido o valor fuera de rango | Revisar el mensaje `detail` |
| Vista ejecutiva vacía | Aún no hay predicciones / BD caída | Hacer alguna predicción; revisar `DATABASE_URL` |
