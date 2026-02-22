import { Link, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const navItems = [
  { path: "/", key: "dashboard" },
  { path: "/skills", key: "skills" },
  { path: "/workers", key: "workers" },
  { path: "/shifts", key: "shifts" },
  { path: "/lines", key: "lines" },
  { path: "/flow-editor", key: "flow_editor" },
  { path: "/optimize", key: "optimize" },
];

export default function Layout() {
  const { t, i18n } = useTranslation();
  const location = useLocation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <div className="language-switcher">
          <button
            className={i18n.language === "en" ? "active" : ""}
            onClick={() => changeLanguage("en")}
          >
            EN
          </button>
          <button
            className={i18n.language === "es" ? "active" : ""}
            onClick={() => changeLanguage("es")}
          >
            ES
          </button>
        </div>
      </header>
      <div className="app-body">
        <nav className="app-nav">
          {navItems.map((item) => (
            <Link
              key={item.key}
              to={item.path}
              className={location.pathname === item.path ? "active" : ""}
            >
              {t(`app.nav.${item.key}`)}
            </Link>
          ))}
        </nav>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
