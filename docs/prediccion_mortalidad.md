# Predicción de supervivencia ("¿vivirás más de 70 años?") — Diseño

Documento de diseño para agregar un modelo que estime el **riesgo de mortalidad /
supervivencia**, distinto del modelo actual.

> ✅ **MVP implementado** (Opción A — mortalidad a 10 años binaria) en la rama
> `feature/mortality-mvp` (pipeline `nhanes_mortality`). Resultados en test:
> **Accuracy 0.894 · ROC-AUC 0.938 · Recall 0.69** sobre 16.382 filas usables
> (22.7% murieron en 10 años; 25.640 censuradas descartadas). El gate de ≥80% de
> precisión se cumple con margen y el AUC 0.94 confirma valor real. La **Opción B**
> (supervivencia / Cox, C-index) sigue pendiente. Correr: `kedro run --pipeline nhanes_mortality`.

---

## 1. Por qué es un modelo DISTINTO al actual

| | Modelo actual (`IS_LONGEVO`) | Modelo de supervivencia (nuevo) |
|---|---|---|
| Pregunta | ¿Tu perfil **se parece** al de alguien ≥70? | ¿**Sobrevivirás** / cuál es tu riesgo de morir? |
| Target | Edad actual ≥ 70 (`RIDAGEYR`) | Mortalidad en el seguimiento (`MORTSTAT`, `FUTIME`) |
| Datos clave | Biomarcadores del momento | Biomarcadores **+ seguimiento de mortalidad** (quién murió y cuándo) |
| `RIDAGEYR` (edad) | Es el target → **se excluye** de features | Es **feature legítima** (la edad predice mortalidad) |

El modelo actual nunca predijo supervivencia: predecía si el cuerpo *aparenta* 70+.
Predecir "vivir más de 70" requiere **datos de seguimiento de mortalidad**.

---

## 2. Lo que YA existe en el repo (gran ventaja de partida)

No hay que construir desde cero — la infraestructura de mortalidad ya está:

- **Loader `MortalityDataset`** (`src/ev3_nhanes/loaders/sas_loader.py`): descarga y
  parsea el archivo enlazado de mortalidad de la CDC (formato **fixed-width**),
  extrayendo `SEQN`, `ELIGSTAT`, `MORTSTAT`, `FUTIME`. Ya valida que `MORTSTAT ∈ {0,1,NaN}`.
- **Dataset en catálogo** (`conf/base/catalog.yml`): `raw_nhanes_2017_mortality` apunta a
  `.../linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat`.
- **Pipeline 2017-2018** (`nhanes_2017_2018`): ya **descarga y une** `MORTSTAT`/`FUTIME`
  por `SEQN`, pero **a propósito no los usa como target** (su reporte lo dice:
  *"MORTSTAT is not used as target or predictor"*).

→ Falta: descargar mortalidad de **los demás ciclos**, derivar un **target de
supervivencia** y **entrenar** un modelo nuevo.

---

## 3. Datos: NHANES Linked Mortality Files (LMF)

- **Qué son:** La CDC enlaza a cada participante de NHANES con el National Death Index
  (NDI). Archivos públicos enlazados hasta **2019-12-31**.
- **Dónde:** `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/`
  con un archivo por ciclo: `NHANES_{AAAA_AAAA}_MORT_2019_PUBLIC.dat`
  (p. ej. `NHANES_2015_2016_...`, `NHANES_2013_2014_...`, etc., hasta 1999-2000).
- **Variables clave** (las que ya extrae el loader, más otras disponibles en el `.dat`):
  - `MORTSTAT` — 0 = vivo al cierre, 1 = fallecido.
  - `FUTIME` / `PERMTH_EXM` — **meses de seguimiento** desde el examen MEC (censura).
  - `ELIGSTAT` — elegibilidad para el enlace (filtrar a elegibles).
  - `UCOD_LEADING` — causa de muerte (opcional; para análisis por causa).
- **Por ciclo:** hay que añadir un dataset de mortalidad **por cada ciclo** que usemos
  (2005-06 … 2017-18), replicando la entrada `raw_nhanes_2017_mortality` con su URL.

---

## 4. Definición del TARGET (la decisión más importante)

Hay tres formas, de más simple a más correcta. **La censura es el problema central**:
mucha gente sigue **viva** al final del seguimiento → no sabemos si vivirá hasta 70.

### Opción A — Mortalidad a N años (clasificación binaria) · *recomendada para MVP*
- Target: `murió_en_N_años = 1` si `MORTSTAT==1` y `FUTIME ≤ N*12` meses, si no 0.
- **Manejo de censura:** excluir a los **vivos con seguimiento < N años** (no se sabe
  su desenlace). Quedarse con quienes tienen el desenlace observable a N años.
- Pros: simple, reusa `XGBClassifier` (igual que el modelo actual). Métrica: **AUC**.
- N típico: **5 o 10 años**.

### Opción B — Análisis de supervivencia (time-to-event) · *v2, lo correcto*
- Modela el **tiempo hasta la muerte** con censura, sin tirar datos.
- Modelos: **Cox PH** (`scikit-survival` / `lifelines`), **Random Survival Forest**, o
  **XGBoost** con `objective="survival:cox"` / `"survival:aft"`.
- Métrica: **C-index** (concordancia), Brier score dependiente del tiempo.

### Opción C — "Vivir más de 70" exacto · *complejo*
- Objetivo condicional: para alguien de edad E, ¿sobrevive hasta 70? Combina edad +
  supervivencia y solo es estimable bien con un modelo de supervivencia (Opción B) del
  que se deriva `P(sobrevivir hasta 70 | edad actual, biomarcadores)`.

> **Recomendación:** empezar con **A** (mortalidad a 10 años, binaria) por simplicidad y
> reutilización de la infra; evolucionar a **B** (Cox/survival) para hacerlo bien.

---

## 5. Features (y el rol de la edad)

- **Reusar el contrato de 36 features** del modelo combinado (antropometría, presión,
  panel PhenoAge, cuestionario).
- **AÑADIR `RIDAGEYR` (edad) como feature.** Aquí es legítimo y necesario: la edad es el
  predictor #1 de mortalidad. (En el modelo actual se excluye porque ahí es el target.)
- **Clave de honestidad/valor:** un modelo de mortalidad que solo use la edad es trivial.
  El valor está en cuánto **añaden los biomarcadores por encima de la edad** → siempre
  comparar contra un baseline "solo edad".

---

## 6. Cambios en el pipeline (Kedro)

Nuevo pipeline `nhanes_mortality` (o extender `nhanes_combined`):

1. **Catálogo:** añadir `raw_nhanes_{ciclo}_mortality` (MortalityDataset) para cada ciclo
   2005-06 … 2017-18 (replicar la entrada 2017 con su URL).
2. **Descarga de features:** reusar `descargar_y_unir_combinado` (ya trae todas las edades
   de los 7 ciclos).
3. **Unir mortalidad:** `left join` por `SEQN` de cada ciclo con su archivo de mortalidad
   (cuidado: `SEQN` se repite entre ciclos → unir **por ciclo**, usando `CICLO_ORIGEN`).
4. **Derivar target:** `murió_en_N_años` con manejo de censura (Opción A) o `(tiempo,
   evento)` para supervivencia (Opción B). Filtrar `ELIGSTAT` a elegibles.
5. **Entrenar:** `XGBClassifier` (binario) o modelo de supervivencia; con
   `RandomizedSearchCV` como los demás.
6. **serving + load_db:** bendecir el modelo nuevo; opcional cargar a la BD.

---

## 7. Modelado y métricas

- **Binario (A):** `XGBClassifier(objective="binary:logistic")` + `scale_pos_weight`
  (los fallecidos en seguimiento corto son minoría). Métricas: **AUC-ROC**, precisión/
  recall, **calibración** (no solo accuracy).
- **Supervivencia (B):** `scikit-survival` (Cox PH, RSF) o XGBoost `survival:cox`.
  Métrica: **C-index**, Brier dependiente del tiempo.
- **Validación específica:** comparar siempre contra **baseline solo-edad**; reportar la
  mejora marginal de los biomarcadores. Split temporal/estratificado.

---

## 8. API / serving / web

- **serving:** bendecir el modelo de mortalidad a `data/09_serving/` (junto a los actuales).
- **API:** nuevo endpoint `POST /predict-mortality` (o extender `/predict` con un segundo
  bloque). Devuelve, p. ej., `riesgo_mortalidad_10y` (prob.) o `prob_supervivencia`.
- **feature_schema:** este modelo **pide la edad como input** (no solo de referencia).
- **web:** una tarjeta nueva *"Riesgo estimado a 10 años"* con explicación honesta y
  separada de la "edad biológica" actual.

---

## 9. Caveats éticos y de honestidad (imprescindibles)

- Predecir mortalidad es **sensible**: disclaimers fuertes, lenguaje cuidadoso, nunca
  presentarlo como certeza ni como diagnóstico.
- Es una estimación **poblacional**, no individual.
- Sesgos de NHANES: población de EE. UU., seguimiento hasta 2019, censura.
- Considerar **no** mostrar un "número de años de vida" crudo, sino un riesgo relativo
  con contexto.

---

## 10. Dependencias nuevas

- **Supervivencia (Opción B):** `scikit-survival` o `lifelines` (Cox, C-index). XGBoost
  ya está instalado y soporta `survival:cox`/`aft` sin librería extra.
- **Opción A (binaria):** **ninguna** dependencia nueva (XGBoost ya está).

---

## 11. Plan por fases (esfuerzo)

| Fase | Alcance | Esfuerzo |
|---|---|---|
| **1 — MVP** | Mortalidad a 10 años (binaria), ciclos con mortalidad disponible, `XGBClassifier`, edad como feature, AUC + baseline-edad | Bajo-medio (la infra de mortalidad ya existe) |
| **2 — Survival** | Cox / scikit-survival multi-ciclo, C-index, calibración, "P(vivir hasta 70)" | Medio |
| **3 — Producto** | endpoint API, serving, tarjeta web con disclaimers | Medio |

**Resumen:** el repo ya descarga y parsea mortalidad NHANES; falta extender el catálogo a
todos los ciclos, derivar el target con manejo de censura, añadir la edad como feature, y
entrenar un modelo (binario para el MVP, supervivencia para hacerlo bien).
