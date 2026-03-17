import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import PrivateRoute from './components/PrivateRoute';
import Sidebar from './components/Sidebar';
import { Menu, Zap } from 'lucide-react';

import Login     from './pages/Login';
import Register  from './pages/Register';
import Dashboard from './pages/Dashboard';
import Tasks     from './pages/Tasks';
import Goals     from './pages/Goals';
import Notes     from './pages/Notes';
import Schedule  from './pages/Schedule';
import Calendar  from './pages/Calendar';
import Profile   from './pages/Profile';

function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-base text-soft font-sans">

      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />

      <div className="flex-1 flex flex-col min-w-0">

        {/* Mobile top bar */}
        <div className="lg:hidden sticky top-0 z-20 flex items-center gap-3
          px-4 py-3 bg-sidebar border-b border-border">
          <button
            onClick={() => setSidebarOpen(true)}
            className="w-9 h-9 rounded-xl bg-surface border border-border
              flex items-center justify-center"
          >
            <Menu size={18} className="text-soft" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
              <Zap size={13} className="text-white" />
            </div>
            <div className="text-base font-extrabold text-soft">
              day<span className="text-primary">flow</span>
            </div>
          </div>
        </div>

        {/* Page content */}
        <div className="flex-1 p-4 md:p-6 lg:p-8 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />

        {[
          { path:'/',         Page: Dashboard },
          { path:'/tasks',    Page: Tasks     },
          { path:'/goals',    Page: Goals     },
          { path:'/notes',    Page: Notes     },
          { path:'/schedule', Page: Schedule  },
          { path:'/calendar', Page: Calendar  },
          { path:'/profile',  Page: Profile   },
        ].map(({ path, Page: PageComponent }) => (
          <Route key={path} path={path} element={
            <PrivateRoute>
              <Layout><PageComponent /></Layout>
            </PrivateRoute>
          } />
        ))}
      </Routes>
    </BrowserRouter>
  );
}