import { Link, Route, Routes } from "react-router-dom";
import { LibraryPage } from "./pages/LibraryPage";
import { ReaderPage } from "./pages/ReaderPage";

export function App(): JSX.Element {
  return (
    <>
      <h1>文献引路</h1>
      <nav>
        <Link to="/library">文献库</Link>
        <br />
        <Link to="/reader">阅读助手</Link>
      </nav>
      <Routes>
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/reader" element={<ReaderPage />} />
      </Routes>
    </>
  );
}
