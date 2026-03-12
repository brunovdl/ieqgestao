import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Home from './pages/Home';
import Cells from './pages/Cells';
import Gallery from './pages/Gallery';
import Visitors from './pages/Visitors';
import Carpool from './pages/Carpool';
import Users from './pages/Users';
import Profile from './pages/Profile';

function App() {
    return (
        <Router>
            <div className="app-container">
                <Sidebar />
                <div className="main-content">
                    <Header />
                    <main className="page-content">
                        <Routes>
                            <Route path="/" element={<Home />} />
                            <Route path="/celulas" element={<Cells />} />
                            <Route path="/galeria" element={<Gallery />} />
                            <Route path="/visitantes" element={<Visitors />} />
                            <Route path="/carona" element={<Carpool />} />
                            <Route path="/usuarios" element={<Users />} />
                            <Route path="/perfil" element={<Profile />} />
                        </Routes>
                    </main>
                </div>
            </div>
        </Router>
    );
}

export default App;
