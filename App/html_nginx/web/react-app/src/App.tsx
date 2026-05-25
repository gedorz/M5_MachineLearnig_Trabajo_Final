import { useMemo, useState } from "react";

type SubmenuItem = {
  label: string;
  description: string;
};

type MenuSection = {
  title: string;
  accent: string;
  summary: string;
  submenu: SubmenuItem[];
};

const menuSections: MenuSection[] = [
  {
    title: "Cargar data",
    accent: "var(--coral)",
    summary: "Sube datos limpios o crudos para preparar el pipeline.",
    submenu: [
      {
        label: "Importar CSV/Excel",
        description: "Adjunta datasets y valida columnas requeridas."
      },
      {
        label: "Conectar Data Lake",
        description: "Sincroniza datos desde almacenamiento externo."
      },
      {
        label: "Previsualizar lote",
        description: "Muestra muestra estadística antes de entrenar."
      }
    ]
  },
  {
    title: "Entrenar modelo",
    accent: "var(--mint)",
    summary: "Configura experimentos, hiperparámetros y ejecución.",
    submenu: [
      {
        label: "Definir features",
        description: "Selecciona variables de entrada y objetivo."
      },
      {
        label: "Lanzar AutoML",
        description: "Corre varias arquitecturas de forma paralela."
      },
      {
        label: "Comparar métricas",
        description: "Ranking por AUC, F1, recall y precisión."
      }
    ]
  },
  {
    title: "Mostrar predicciones",
    accent: "var(--gold)",
    summary: "Explora salidas del modelo con trazabilidad y alertas.",
    submenu: [
      {
        label: "Predicción en línea",
        description: "Evalúa una muestra individual en tiempo real."
      },
      {
        label: "Predicción masiva",
        description: "Ejecuta inferencia por lotes y genera reporte."
      },
      {
        label: "Exportar resultados",
        description: "Descarga JSON/CSV con probabilidades y etiquetas."
      }
    ]
  }
];

export default function App() {
  const [activeMenu, setActiveMenu] = useState(menuSections[0].title);

  const selectedMenu = useMemo(
    () => menuSections.find((section) => section.title === activeMenu) ?? menuSections[0],
    [activeMenu]
  );

  return (
    <div className="page-shell">
      <header className="header-panel">
        <p className="eyebrow">Machine Learning Workbench</p>
        <h1>Panel operativo de modelos</h1>
        <p className="subtitle">
          Menú principal con submenús para datos, entrenamiento y predicciones.
        </p>
      </header>

      <nav className="main-menu" aria-label="Menú principal">
        {menuSections.map((section) => (
          <button
            type="button"
            key={section.title}
            className={`menu-card ${activeMenu === section.title ? "is-active" : ""}`}
            onMouseEnter={() => setActiveMenu(section.title)}
            onFocus={() => setActiveMenu(section.title)}
            onClick={() => setActiveMenu(section.title)}
            style={{ "--accent": section.accent } as React.CSSProperties}
          >
            <span className="menu-title">{section.title}</span>
            <span className="menu-summary">{section.summary}</span>
          </button>
        ))}
      </nav>

      <section className="submenu-panel" aria-live="polite">
        <div className="submenu-header">
          <h2>{selectedMenu.title}</h2>
          <span className="submenu-badge">Submenús</span>
        </div>

        <ul className="submenu-grid">
          {selectedMenu.submenu.map((item, index) => (
            <li key={item.label} className="submenu-item" style={{ animationDelay: `${index * 120}ms` }}>
              <h3>{item.label}</h3>
              <p>{item.description}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
