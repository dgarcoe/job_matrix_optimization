import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense } from "react";
import "./i18n";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Skills from "./pages/Skills";
import Workers from "./pages/Workers";
import Shifts from "./pages/Shifts";
import ProductionLines from "./pages/ProductionLines";
import Optimize from "./pages/Optimize";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<div>Loading...</div>}>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/skills" element={<Skills />} />
              <Route path="/workers" element={<Workers />} />
              <Route path="/shifts" element={<Shifts />} />
              <Route path="/lines" element={<ProductionLines />} />
              <Route path="/optimize" element={<Optimize />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </Suspense>
    </QueryClientProvider>
  );
}
