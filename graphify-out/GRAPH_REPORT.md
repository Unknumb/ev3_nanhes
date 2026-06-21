# Graph Report - .  (2026-06-21)

## Corpus Check
- 89 files · ~100,242 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 462 nodes · 607 edges · 48 communities (29 shown, 19 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_FastAPI Prediction Service|FastAPI Prediction Service]]
- [[_COMMUNITY_Architecture & Design|Architecture & Design]]
- [[_COMMUNITY_Custom SAS Data Loaders|Custom SAS Data Loaders]]
- [[_COMMUNITY_Pipeline Registry & 2017|Pipeline Registry & 2017]]
- [[_COMMUNITY_Streamlit Dashboard UI|Streamlit Dashboard UI]]
- [[_COMMUNITY_NHANES 2013 Pipeline|NHANES 2013 Pipeline]]
- [[_COMMUNITY_NHANES 2015 Pipeline|NHANES 2015 Pipeline]]
- [[_COMMUNITY_Next.js Web Dependencies|Next.js Web Dependencies]]
- [[_COMMUNITY_Executive Dashboard Page|Executive Dashboard Page]]
- [[_COMMUNITY_TypeScript Configuration|TypeScript Configuration]]
- [[_COMMUNITY_Database Persistence Layer|Database Persistence Layer]]
- [[_COMMUNITY_API Test Suite|API Test Suite]]
- [[_COMMUNITY_Kedro Catalog Models|Kedro Catalog Models]]
- [[_COMMUNITY_Serving Pipeline|Serving Pipeline]]
- [[_COMMUNITY_PCA & Clustering Analysis|PCA & Clustering Analysis]]
- [[_COMMUNITY_DB Loading Pipeline|DB Loading Pipeline]]
- [[_COMMUNITY_Classification Evaluation|Classification Evaluation]]
- [[_COMMUNITY_NHANES 2013 Parameters|NHANES 2013 Parameters]]
- [[_COMMUNITY_Regression Evaluation|Regression Evaluation]]
- [[_COMMUNITY_App Layout & Navigation|App Layout & Navigation]]
- [[_COMMUNITY_Catalog Data Layers|Catalog Data Layers]]
- [[_COMMUNITY_Sphinx Doc Config|Sphinx Doc Config]]
- [[_COMMUNITY_Kedro CLI Entry Point|Kedro CLI Entry Point]]
- [[_COMMUNITY_Pipeline Registration Tests|Pipeline Registration Tests]]
- [[_COMMUNITY_Python Requirements|Python Requirements]]
- [[_COMMUNITY_NHANES 2017 Catalog|NHANES 2017 Catalog]]
- [[_COMMUNITY_Kedro Settings|Kedro Settings]]
- [[_COMMUNITY_Pipeline Unit Test|Pipeline Unit Test]]
- [[_COMMUNITY_Next.js Config|Next.js Config]]
- [[_COMMUNITY_Tailwind Config|Tailwind Config]]
- [[_COMMUNITY_Kedro Base Catalog|Kedro Base Catalog]]
- [[_COMMUNITY_Classification Model 2017|Classification Model 2017]]
- [[_COMMUNITY_Regression Model 2017|Regression Model 2017]]
- [[_COMMUNITY_Mortality Dataset Loader|Mortality Dataset Loader]]
- [[_COMMUNITY_NHANES 2017 Merged|NHANES 2017 Merged]]
- [[_COMMUNITY_Serving Metadata|Serving Metadata]]
- [[_COMMUNITY_Logging Config|Logging Config]]
- [[_COMMUNITY_NHANES 2015 Params|NHANES 2015 Params]]
- [[_COMMUNITY_Age Feature Exclusion|Age Feature Exclusion]]
- [[_COMMUNITY_Project README|Project README]]
- [[_COMMUNITY_Sphinx Index|Sphinx Index]]

## God Nodes (most connected - your core abstractions)
1. `Pipeline` - 21 edges
2. `compilerOptions` - 16 edges
3. `SASDataset` - 11 edges
4. `MortalityDataset` - 11 edges
5. `Architecture Documentation` - 11 edges
6. `DataFrame` - 8 edges
7. `train_nhanes_2017_xgb_classifier()` - 8 edges
8. `main.py (FastAPI App + Endpoints)` - 8 edges
9. `_to_frame()` - 7 edges
10. `PredictRequest` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Path` --uses--> `Pipeline`  [INFERRED]
  tests/test_api.py → src/ev3_nhanes/pipelines/load_db/pipeline.py
- `API README - NHANES Longevity Serving v1` --semantically_similar_to--> `API REST Reference`  [INFERRED] [semantically similar]
  api/README.md → docs/api.md
- `Root Requirements - Kedro/ML Dependencies` --semantically_similar_to--> `API Requirements - FastAPI/SQLAlchemy Dependencies`  [INFERRED] [semantically similar]
  requirements.txt → api/requirements.txt
- `ColumnTransformer` --uses--> `Pipeline`  [INFERRED]
  src/ev3_nhanes/pipelines/nhanes_2013/nodes.py → src/ev3_nhanes/pipelines/load_db/pipeline.py
- `Pipeline` --uses--> `Pipeline`  [INFERRED]
  src/ev3_nhanes/pipelines/nhanes_2013/pipeline.py → src/ev3_nhanes/pipelines/load_db/pipeline.py

## Import Cycles
- 1-file cycle: `api/main.py -> api/main.py`

## Hyperedges (group relationships)
- **ETL to Training to Serving Pipeline Flow** — pipeline_nhanes_2015, pipeline_serving, pipeline_load_db, concept_autocontained_pickles [EXTRACTED 1.00]
- **Prediction Request Lifecycle (Validate-Predict-Persist)** — endpoint_predict, component_model_registry, component_schema, component_db, table_predictions [EXTRACTED 1.00]
- **Docker Compose Service Orchestration Stack** — service_postgres, service_api, ev3_nanhes_docker_compose, concept_database_url_config [EXTRACTED 1.00]
- **NHANES 2013 Pipeline Data Flow (raw -> preprocessed -> models -> reports)** — base_catalog_nhanes_2013_raw_nhanes_2013, base_catalog_nhanes_2013_preprocessed_nhanes_2013, base_catalog_nhanes_2013_modelo_clasificacion_nhanes_2013, base_catalog_nhanes_2013_modelo_regresion_nhanes_2013, base_catalog_nhanes_2013_reporte_clasificacion_nhanes_2013, base_catalog_nhanes_2013_reporte_regresion_nhanes_2013 [EXTRACTED 1.00]
- **NHANES 2015 Pipeline Data Flow (raw -> preprocessed -> models -> reports)** — base_catalog_2015_raw_nhanes_2015, base_catalog_2015_preprocessed_nhanes_2015, base_catalog_2015_modelo_clasificacion_nhanes_2015, base_catalog_2015_modelo_regresion_nhanes_2015, base_catalog_2015_reporte_clasificacion_nhanes_2015, base_catalog_2015_reporte_regresion_nhanes_2015 [EXTRACTED 1.00]
- **Production Serving Layer (stable-path models + metadata)** — base_catalog_serving_modelo_serving_clasificacion, base_catalog_serving_modelo_serving_regresion, base_catalog_serving_serving_metadata [EXTRACTED 1.00]
- **Unsupervised Exploration Pipeline (PCA + K-Means + Profiling)** — 08_reporting_03_pca_scree_plot, 08_reporting_03_elbow_silhouette, 08_reporting_03_pca_clusters, 08_reporting_03_cluster_boxplots [INFERRED 0.95]
- **Cluster Selection Methodology (Elbow + Silhouette + Visual Validation)** — concept_elbow_method, concept_silhouette_score, concept_kmeans_clustering [INFERRED 0.85]
- **PCA Visualization Suite (Scree + Cluster + Age + Longevity Views)** — 08_reporting_03_pca_scree_plot, 08_reporting_03_pca_clusters, concept_pca_dimensionality_reduction [INFERRED 0.85]
- **Longevity Classification Model Comparison (DT vs RF vs XGBoost)** — concept_decision_tree_classifier, concept_random_forest_classifier, concept_xgboost_classifier, 08_reporting_04_confusion_matrices [EXTRACTED 1.00]
- **XGBoost Threshold Optimization Workflow (curve + tuned CM)** — 08_reporting_04_threshold_tuning_curve, 08_reporting_04_threshold_tuning_cm, concept_optimal_threshold, concept_xgboost_classifier [INFERRED 0.95]
- **Classification Reporting Suite (04 notebook outputs)** — 08_reporting_04_confusion_matrices, 08_reporting_04_feature_importance, 08_reporting_04_threshold_tuning_cm, 08_reporting_04_threshold_tuning_curve [INFERRED 0.85]
- **XGBoost Regression Diagnostic Visualization Suite** — 08_reporting_05_edad_real_vs_predicha, 08_reporting_05_feature_importance_regresion, 08_reporting_05_residuos, concept_xgboost_regression_evaluation [INFERRED 0.95]

## Communities (48 total, 19 thin omitted)

### Community 0 - "FastAPI Prediction Service"
Cohesion: 0.09
Nodes (35): API FastAPI de NHANES Longevity (capa de serving del modelo 2015)., aggregates(), explain(), lifespan(), metrics(), predict(), API FastAPI: sirve el modelo de longevidad 2015 (clasificacion + regresion).  En, Agregados del historial de predicciones (los consume el dashboard ejecutivo). (+27 more)

### Community 1 - "Architecture & Design"
Cohesion: 0.07
Nodes (40): API README - NHANES Longevity Serving v1, db.py (save_prediction + get_aggregates), main.py (FastAPI App + Endpoints), model_registry.py (Load/Predict/Explain), schema.py (Pydantic Models + Validation), Autocontained Sklearn Pipeline Pickles, Best-Effort DB Persistence for Predictions, Biological Age Regression (RIDAGEYR as Target) (+32 more)

### Community 2 - "Custom SAS Data Loaders"
Cohesion: 0.06
Nodes (21): AbstractDataset, Custom loaders for Kedro datasets., MortalityDataset, Custom loaders for SAS and mortality data files from URLs using pyreadstat., Custom Kedro dataset for loading SAS transport files (.xpt) from URLs., Save is not supported for this dataset., Check if the remote file exists., Return None as versioning is not supported. (+13 more)

### Community 3 - "Pipeline Registry & 2017"
Cohesion: 0.11
Nodes (33): Register the project's pipelines.      Returns:         A mapping from pipeline, register_pipelines(), ndarray, NHANES 2017-2018 pipeline., build_nhanes_2017_feature_expanded(), _build_preprocessor(), _check_columns(), _format_confusion_matrix() (+25 more)

### Community 4 - "Streamlit Dashboard UI"
Cohesion: 0.09
Nodes (20): buildPredictPayload(), ExplainContribution, ExplainResult, ExplainState, FeatureSchema, formatGap(), formatYears(), getGapLabel() (+12 more)

### Community 5 - "NHANES 2013 Pipeline"
Cohesion: 0.13
Nodes (22): This is a boilerplate pipeline 'nhanes_2013' generated using Kedro 1.4.0, _construir_preprocesador(), _descargar_ciclo(), descargar_y_unir_2013(), entrenar_modelo_clasificacion(), entrenar_modelo_regresion(), _generar_url(), _limpiar_missing_sas() (+14 more)

### Community 6 - "NHANES 2015 Pipeline"
Cohesion: 0.13
Nodes (22): This is a boilerplate pipeline 'nhanes_2015' generated using Kedro 1.4.0, _construir_preprocesador(), _descargar_ciclo(), descargar_y_unir_2015(), entrenar_modelo_clasificacion(), entrenar_modelo_regresion(), _generar_url(), _limpiar_missing_sas() (+14 more)

### Community 7 - "Next.js Web Dependencies"
Cohesion: 0.09
Nodes (21): dependencies, next, react, react-dom, recharts, devDependencies, autoprefixer, postcss (+13 more)

### Community 8 - "Executive Dashboard Page"
Cohesion: 0.13
Nodes (11): AggregatesResponse, AggregatesState, DistributionBin, ExecutivePage(), formatNumber(), RecentPrediction, fetchWithTimeout(), getFetchErrorMessage() (+3 more)

### Community 9 - "TypeScript Configuration"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 10 - "Database Persistence Layer"
Cohesion: 0.16
Nodes (18): Base, db_ready(), _ensure_tables(), get_aggregates(), get_engine(), init_db(), Prediction, Any (+10 more)

### Community 11 - "API Test Suite"
Cohesion: 0.12
Nodes (5): _build_synthetic_models(), client(), Path, Tests de la API de serving.  Construyen un modelo SINTETICO (mismo Pipeline skle, Entrena modelos diminutos con el preprocesador real y los persiste.

### Community 12 - "Kedro Catalog Models"
Cohesion: 0.15
Nodes (15): NHANES 2015 Classification Model (Versioned Pickle), NHANES 2015 Regression Model (Versioned Pickle), NHANES 2015 Classification Report (Text), NHANES 2015 Regression Report (Text), NHANES 2013 Classification Model (Versioned Pickle), NHANES 2013 Regression Model (Versioned Pickle), NHANES 2013 Classification Report (Text), NHANES 2013 Regression Report (Text) (+7 more)

### Community 13 - "Serving Pipeline"
Cohesion: 0.20
Nodes (9): Pipeline 'serving': bendice el modelo de producción (2015) a una ruta estable qu, bendecir_modelos_serving(), Nodos del pipeline de serving.  El modelo de producción de la v1 es el del ciclo, Persiste los modelos 2015 a la ruta de serving y genera su metadata.      Args:, create_pipeline(), Definición del pipeline 'serving'., Bendice el modelo de producción (2015) a data/09_serving/.      Consume los mode, Any (+1 more)

### Community 14 - "PCA & Clustering Analysis"
Cohesion: 0.27
Nodes (11): Cluster Boxplots (RIDAGEYR, BMXBMI, BPXSY1, BPXPLS), Elbow Method and Silhouette Score for K-Means (Best K=2), PCA Scatter Plots Colored by Cluster, Age, and IS_LONGEVO, PCA Scree Plot - Variance Explained (80% at ~8 Components), Cluster Profiling by Biomarker Features, Elbow Method (WCSS Inertia), K-Means Clustering Analysis, PCA Dimensionality Reduction (+3 more)

### Community 15 - "DB Loading Pipeline"
Cohesion: 0.27
Nodes (8): cargar_dataset_postgres(), _database_url(), preparar_tabla_nhanes(), Copia el dataframe procesado y normaliza nombres de columnas para SQL., Escribe el dataframe procesado en Postgres usando SQLAlchemy., create_pipeline(), Any, DataFrame

### Community 16 - "Classification Evaluation"
Cohesion: 0.36
Nodes (10): Confusion Matrices Comparison (Decision Tree, Random Forest, XGBoost), XGBoost Feature Importance (Importancia de Variables), XGBoost Confusion Matrix at Optimal Threshold 0.48, Decision Threshold Optimization Curve (F1 vs Umbral), Decision Tree Classifier (F1=0.829, AUC=0.898), IS_LONGEVO Binary Target (Longevo vs No Longevo), Optimal Decision Threshold 0.48 (F1 Clase 1 = 0.873), Random Forest Classifier (F1=0.856, AUC=0.934) (+2 more)

### Community 17 - "NHANES 2013 Parameters"
Cohesion: 0.25
Nodes (8): NHANES 2013 Pipeline Parameters, Data Augmentation for Longevity Class Balance, KNN Imputer Config (k=5, uniform), PCA + K-Means Unsupervised Config (2013), RandomizedSearchCV Config (n_iter=30, f1, cv=5), SAS Missing Value Threshold (1e-70), Longevity Threshold (Age >= 70), XGBoost Hyperparameter Search Space (2013)

### Community 18 - "Regression Evaluation"
Cohesion: 0.43
Nodes (7): Actual vs Predicted Age Scatter Plot (Random Forest & XGBoost), Feature Importance for Age Prediction (XGBoost Regression), Residual Distribution and Residuals vs Actual Age (XGBoost), Regression Metrics (R2=0.681, MAE=8.3, RMSE=10.4 for XGBoost), Residual Analysis (mean=0.2, near-normal distribution, heteroscedasticity at extremes), Top Regression Features (DMDMARTL_2, DMDMARTL_5, DMDMARTL_6, DMDHHSIZ, BPXSY1), XGBoost Regression Model Evaluation

### Community 19 - "App Layout & Navigation"
Cohesion: 0.40
Nodes (3): metadata, AppNav(), navItems

### Community 20 - "Catalog Data Layers"
Cohesion: 0.33
Nodes (6): Preprocessed NHANES 2015 Parquet Dataset, Raw NHANES 2015 Master CSV Dataset, Kedro Data Layer Convention (raw/intermediate/models/reporting), Preprocessed NHANES 2013 Parquet Dataset, Raw NHANES 2013 Master CSV Dataset, Load DB Parameters (table nhanes_processed)

### Community 22 - "Kedro CLI Entry Point"
Cohesion: 0.50
Nodes (3): main(), ev3_nhanes file for ensuring the package is executable as `ev3-nhanes` and `pyth, Any

## Ambiguous Edges - Review These
- `Cluster Boxplots (RIDAGEYR, BMXBMI, BPXSY1, BPXPLS)` → `4 Clusters Used in Boxplots Despite Silhouette Suggesting K=2`  [AMBIGUOUS]
  data/08_reporting/03_cluster_boxplots.png · relation: rationale_for
- `Elbow Method and Silhouette Score for K-Means (Best K=2)` → `4 Clusters Used in Boxplots Despite Silhouette Suggesting K=2`  [AMBIGUOUS]
  data/08_reporting/03_elbow_silhouette.png · relation: references

## Knowledge Gaps
- **95 isolated node(s):** `Any`, `DataFrame`, `Any`, `Any`, `Any` (+90 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Cluster Boxplots (RIDAGEYR, BMXBMI, BPXSY1, BPXPLS)` and `4 Clusters Used in Boxplots Despite Silhouette Suggesting K=2`?**
  _Edge tagged AMBIGUOUS (relation: rationale_for) - confidence is low._
- **What is the exact relationship between `Elbow Method and Silhouette Score for K-Means (Best K=2)` and `4 Clusters Used in Boxplots Despite Silhouette Suggesting K=2`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Pipeline` connect `Pipeline Registry & 2017` to `NHANES 2013 Pipeline`, `NHANES 2015 Pipeline`, `API Test Suite`, `Serving Pipeline`, `DB Loading Pipeline`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `Path` connect `API Test Suite` to `Pipeline Registry & 2017`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `Pipeline` (e.g. with `ndarray` and `OneHotEncoder`) actually correct?**
  _`Pipeline` has 19 INFERRED edges - model-reasoned connections that need verification._
- **What connects `API FastAPI de NHANES Longevity (capa de serving del modelo 2015).`, `Any`, `Capa de persistencia: historial de predicciones en SQL.  Tercera fuente de datos` to the rest of the system?**
  _177 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FastAPI Prediction Service` be split into smaller, more focused modules?**
  _Cohesion score 0.08826945412311266 - nodes in this community are weakly interconnected._