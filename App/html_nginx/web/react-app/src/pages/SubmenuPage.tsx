import React from "react";
import type { SubmenuPageContent } from "./submenuPageContent";

type SubmenuPageProps = {
  parentTitle: string;
  submenuTitle: string;
  description: string;
  content: SubmenuPageContent;
};

export default function SubmenuPage({
  parentTitle,
  submenuTitle,
  description,
  content
}: SubmenuPageProps) {
  return (
    <section className="submenu-page" aria-labelledby="submenu-page-title">
      <div className="submenu-page-header">
        <span className="submenu-page-parent">Menu: {parentTitle}</span>
        <h2 id="submenu-page-title">Submenu: {submenuTitle}</h2>
        <p>{description}</p>
      </div>

      <article className="submenu-page-body">
        <h3>Objetivo de la subpagina</h3>
        <p>{content.intro}</p>

        <h3>Checklist operativo</h3>
        <ul>
          {content.checklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </article>
    </section>
  );
}
