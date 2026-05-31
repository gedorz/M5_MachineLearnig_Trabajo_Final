import React, { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import ImportarDatosPage from "./pages/importarDatos";
import PrevisualizarLotePage from "./pages/Previsualizarlote";
import ProcesamientoBalanceoPage from "./pages/procesamientoBalanceo";
import SubmenuPageFeatures from "./pages/submenuPageFeatures";
import SubmenuPageAutoML from "./pages/submenuPageAutoML";
import { SubmenuPage, submenuPageContent } from "./pages";

type SubmenuItem = {
  id: string;
  label: string;
  description: string;
};

type MenuSection = {
  id: string;
  title: string;
  accent: string;
  summary: string;
  submenu: SubmenuItem[];
};

type ActiveDataset = {
  datasetId: number;
  versionId: number;
  versionNumber: number;
  filename: string;
};

const ACTIVE_DATASET_STORAGE_KEY = "m5_active_dataset";

const menuSections: MenuSection[] = [
  {
    id: "cargar-data",
    title: "Cargar data",
    accent: "var(--coral)",
    summary: "Sube datos limpios o crudos para preparar el pipeline.",
    submenu: [
      {
        id: "importar-csv-excel",
        label: "Importar CSV/Excel",
        description: "Adjunta datasets y valida columnas requeridas."
      },
      {
        id: "conectar-data-lake",
        label: "Conectar Data Lake",
        description: "Sincroniza datos desde almacenamiento externo."
      },
      {
        id: "previsualizar-lote",
        label: "Previsualizar lote",
        description: "Muestra muestra estadística antes de entrenar."
      },
      {
        id: "preprocesamiento-balanceo",
        label: "Preprocesamiento y balanceo",
        description: "Configura limpieza, codificacion y estrategia de clases."
      }
    ]
  },
  {
    id: "entrenar-modelo",
    title: "Entrenar modelo",
    accent: "var(--mint)",
    summary: "Configura experimentos, hiperparámetros y ejecución.",
    submenu: [
      {
        id: "definir-features",
        label: "Definir features",
        description: "Selecciona variables de entrada y objetivo."
      },
      {
        id: "lanzar-automl",
        label: "Lanzar AutoML",
        description: "Corre varias arquitecturas de forma paralela."
      },
      {
        id: "comparar-metricas",
        label: "Comparar métricas",
        description: "Ranking por AUC, F1, recall y precisión."
      },
      {
        id: "matriz-confusion-roc",
        label: "Matriz de confusion y curva ROC",
        description: "Visualiza rendimiento por clase y discriminacion del modelo."
      },
      {
        id: "seleccion-mejor-modelo",
        label: "Seleccion del mejor modelo",
        description: "Aplica un criterio metodologico coherente para el modelo final."
      }      
    ]
  },
  {
    id: "mostrar-predicciones",
    title: "Mostrar predicciones",
    accent: "var(--gold)",
    summary: "Explora salidas del modelo con trazabilidad y alertas.",
    submenu: [
      {
        id: "prediccion-linea",
        label: "Predicción en línea",
        description: "Evalúa una muestra individual en tiempo real."
      },
      {
        id: "prediccion-masiva",
        label: "Predicción masiva",
        description: "Ejecuta inferencia por lotes y genera reporte."
      },
      {
        id: "tabla-comparativa",
        label: "Tabla comparativa por modelo",
        description: "Muestra Accuracy, F1-score y ROC-AUC en una vista unificada."
      },   
      {
        id: "modelos-obligatorios",
        label: "Modelos obligatorios",
        description: "Regresion logistica, arbol, random forest, boosting y red neuronal."
      },         
      {
        id: "graficas-rendimiento",
        label: "Graficas de rendimiento",
        description: "Publica curvas y graficos para comparar resultados entre modelos."
      },
      {
        id: "prediccion-7-15-30",
        label: "Prediccion 7, 15 y 30 dias",
        description: "Consulta probabilidad de cancelacion en horizontes temporales definidos."
      },
      {
        id: "exportar-resultados",
        label: "Exportar resultados",
        description: "Descarga JSON/CSV con probabilidades y etiquetas."
      }
    ]
  }
];

export default function App() {
  const firstSection = menuSections[0];
  const firstSubmenu = firstSection.submenu[0];

  const [expandedSections, setExpandedSections] = useState<string[]>([firstSection.id]);
  const [activeSubmenuId, setActiveSubmenuId] = useState(firstSubmenu.id);
  const [activeDataset, setActiveDataset] = useState<ActiveDataset | null>(() => {
  const storedDataset = localStorage.getItem(ACTIVE_DATASET_STORAGE_KEY);
  if (!storedDataset) {
    return null;
  }

  try {
    return JSON.parse(storedDataset) as ActiveDataset;
  } catch {
    return null;
  }
  });

  useEffect(() => {
  if (!activeDataset) {
    localStorage.removeItem(ACTIVE_DATASET_STORAGE_KEY);
    return;
  }

  localStorage.setItem(ACTIVE_DATASET_STORAGE_KEY, JSON.stringify(activeDataset));
  }, [activeDataset]);

  const activeContext = useMemo(() => {
    for (const section of menuSections) {
      const foundSubmenu = section.submenu.find((item) => item.id === activeSubmenuId);
      if (foundSubmenu) {
        return { section, submenu: foundSubmenu };
      }
    }

    return { section: firstSection, submenu: firstSubmenu };
  }, [activeSubmenuId, firstSection, firstSubmenu]);

  const selectedPageContent = submenuPageContent[activeContext.submenu.id] ?? {
    intro: "Esta sección no tiene contenido adicional aún.",
    checklist: ["Define el alcance de esta subpágina."]
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections((currentSections) =>
      currentSections.includes(sectionId)
        ? currentSections.filter((id) => id !== sectionId)
        : [...currentSections, sectionId]
    );
  };

  const handleSubmenuClick = (sectionId: string, submenuId: string) => {
    setActiveSubmenuId(submenuId);
    if (!expandedSections.includes(sectionId)) {
      setExpandedSections((currentSections) => [...currentSections, sectionId]);
    }
  };

  const handleDatasetLoaded = (dataset: ActiveDataset) => {
    setActiveDataset(dataset);
  };

  const handleDatasetVersionChange = (datasetId: number, versionId: number, versionNumber: number) => {
    setActiveDataset((currentDataset) => {
      if (!currentDataset || currentDataset.datasetId !== datasetId) {
        return currentDataset;
      }

      return {
        ...currentDataset,
        versionId,
        versionNumber
      };
    });
  };

  return (
    <div className="page-shell">
      <aside className="sidebar" aria-label="Menú lateral">
        <p className="eyebrow">Machine Learning Workbench</p>
        <h2 className="sidebar-title">Panel operativo</h2>

        <nav className="menu-vertical" aria-label="Menú principal">
          {menuSections.map((section) => {
            const isExpanded = expandedSections.includes(section.id);
            const hasActiveSubmenu = section.submenu.some((item) => item.id === activeSubmenuId);

            return (
              <div key={section.id} className="menu-group" style={{ "--accent": section.accent } as CSSProperties}>
                <button
                  type="button"
                  className={`menu-parent ${hasActiveSubmenu ? "is-active" : ""}`}
                  onClick={() => toggleSection(section.id)}
                  aria-expanded={isExpanded}
                  aria-controls={`submenu-${section.id}`}
                >
                  <span>
                    <strong>{section.title}</strong>
                    <small>{section.summary}</small>
                  </span>
                  <span className={`caret ${isExpanded ? "is-open" : ""}`}>▾</span>
                </button>

                {isExpanded && (
                  <ul id={`submenu-${section.id}`} className="submenu-list">
                    {section.submenu.map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          className={`submenu-link ${activeSubmenuId === item.id ? "is-selected" : ""}`}
                          onClick={() => handleSubmenuClick(section.id, item.id)}
                        >
                          <span>{item.label}</span>
                          <small>{item.description}</small>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </nav>
      </aside>

      <main className="content-panel" aria-live="polite">
        <header className="header-panel">
          <h1>Panel operativo de modelos</h1>
          <p className="subtitle">
            Vista de trabajo para datos, entrenamiento y predicciones con navegación por subpáginas.
          </p>
        </header>

        {activeContext.submenu.id === "importar-csv-excel" ? (
          <ImportarDatosPage onDatasetLoaded={handleDatasetLoaded} />
        ) : activeContext.submenu.id === "previsualizar-lote" ? (
          <PrevisualizarLotePage
            activeDataset={activeDataset}
            onDatasetVersionChange={handleDatasetVersionChange}
          />
        ) : activeContext.submenu.id === "preprocesamiento-balanceo" ? (
          <ProcesamientoBalanceoPage
            activeDataset={activeDataset}
            onDatasetVersionChange={handleDatasetVersionChange}
          />
        ) : activeContext.submenu.id === "definir-features" ? (
          <SubmenuPageFeatures
            activeDataset={activeDataset}
            onDatasetVersionChange={handleDatasetVersionChange}
          />
        ) : activeContext.submenu.id === "lanzar-automl" ? (
          <SubmenuPageAutoML
            activeDataset={activeDataset}
            onDatasetVersionChange={handleDatasetVersionChange}
          />
        ) : (
          <SubmenuPage
            parentTitle={activeContext.section.title}
            submenuTitle={activeContext.submenu.label}
            description={activeContext.submenu.description}
            content={selectedPageContent}
          />
        )}
      </main>
    </div>
  );
}
