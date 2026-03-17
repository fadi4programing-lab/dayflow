import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, CheckSquare, Clock,
  Target, StickyNote, Calendar, LogOut,
  Zap, X
} from 'lucide-react';

const NAV = [
  { name:'Dashboard', path:'/',         icon: LayoutDashboard },
  { name:'Tasks',     path:'/tasks',    icon: CheckSquare     },
  { name:'Schedule',  path:'/schedule', icon: Clock           },
  { name:'Goals',     path:'/goals',    icon: Target          },
  { name:'Notes',     path:'/notes',    icon: StickyNote      },
  { name:'Calendar',  path:'/calendar', icon: Calendar        },
  { name:'Profile',   path:'/profile',  icon: Clock           },
];

export default function Sidebar({ open, setOpen }) {
  const navigate = useNavigate();
  const location = useLocation();
  const user     = JSON.parse(localStorage.getItem('user') || '{}');

  const handleNav = (path) => {
    navigate(path);
    setOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed top-0 left-0 h-full z-40
        w-[210px] bg-sidebar border-r border-border
        flex flex-col gap-1 px-3 py-6
        transition-transform duration-300 ease-in-out
        lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 lg:z-auto
        ${open ? 'translate-x-0' : '-translate-x-full'}
      `}>

        {/* Logo */}
        <div className="px-3 mb-7 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Zap size={16} className="text-white" />
            </div>
            <div>
              <div className="text-base font-extrabold text-soft leading-none">
                day<span className="text-primary">flow</span>
              </div>
              <div className="text-[9px] text-muted tracking-widest">DAILY OS</div>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="lg:hidden w-7 h-7 rounded-lg hover:bg-base
              flex items-center justify-center"
          >
            <X size={16} className="text-muted" />
          </button>
        </div>

        {/* Menu label */}
        <div className="text-[10px] text-muted tracking-widest px-3 mb-1 font-semibold">
          MENU
        </div>

        {/* Nav */}
        {NAV.map(n => {
          const active = location.pathname === n.path;
          const Icon   = n.icon;
          return (
            <div
              key={n.name}
              onClick={() => handleNav(n.path)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer
                text-sm font-medium transition-all duration-200
                ${active
                  ? 'bg-surface text-soft border-l-2 border-primary'
                  : 'text-muted hover:text-soft hover:bg-surface border-l-2 border-transparent'
                }`}
            >
              <Icon size={16} />
              {n.name}
            </div>
          );
        })}

        {/* User + Logout */}
        <div className="mt-auto flex flex-col gap-2 px-1">
          <div className="flex items-center gap-3 px-3 py-3 rounded-xl
            bg-surface border border-border">
            <div className="w-8 h-8 rounded-lg bg-primary/20
              flex items-center justify-center flex-shrink-0">
              <span className="text-primary text-sm font-bold">
                {user.username?.[0]?.toUpperCase() || 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-soft truncate">
                {user.username}
              </div>
              <div className="text-[10px] text-muted truncate">{user.email}</div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2
              btn-ghost rounded-xl py-2.5 text-sm"
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>
      </div>
    </>
  );
}