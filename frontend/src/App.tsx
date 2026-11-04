import { Navigate, Route, Routes } from "react-router-dom";
import { readToken } from "./auth";
import { LibraryPage } from "./pages/LibraryPage";
import { LoginPage } from "./pages/LoginPage";
import { ReaderPage } from "./pages/ReaderPage";
import { Shell } from "./Shell";

function Home(): JSX.Element {
  return <Navigate to={readToken() ? "/library" : "/login"} replace />;
}

export function App(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Shell />}>
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/reader" element={<ReaderPage />} />
      </Route>
    </Routes>
  );
}
