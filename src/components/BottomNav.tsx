import React from 'react';
import { KeyRound, Sliders, PhoneCall, Video, Radio } from 'lucide-react';

export type ActiveToolTab = 'doors' | 'config' | 'sip' | 'cameras' | 'credentials';

interface BottomNavProps {
  activeTab: ActiveToolTab;
  onChangeTab: (tab: ActiveToolTab) => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ activeTab, onChangeTab }) => {
  const tabs = [
    {
      id: 'doors' as ActiveToolTab,
      label: 'Puertas',
      icon: KeyRound,
    },
    {
      id: 'config' as ActiveToolTab,
      label: 'Config MIP',
      icon: Sliders,
    },
    {
      id: 'sip' as ActiveToolTab,
      label: 'SIP & PBX',
      icon: PhoneCall,
    },
    {
      id: 'cameras' as ActiveToolTab,
      label: 'Cámaras',
      icon: Video,
    },
    {
      id: 'credentials' as ActiveToolTab,
      label: 'RFID / RF',
      icon: Radio,
    },
  ];

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 bg-slate-900/95 backdrop-blur-md border-t border-slate-800 shadow-2xl"
      aria-label="Navegación de herramientas de campo"
    >
      <div className="max-w-md mx-auto grid grid-cols-5 items-center h-16 px-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => onChangeTab(tab.id)}
              className={`relative flex flex-col items-center justify-center h-full min-h-[44px] transition-colors ${
                isActive ? 'text-blue-400' : 'text-slate-400 hover:text-slate-200'
              }`}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="relative">
                <Icon className={`w-5 h-5 transition-transform ${isActive ? 'scale-110' : ''}`} />
              </div>
              <span className={`text-[10px] mt-1 font-medium tracking-tight whitespace-nowrap ${isActive ? 'font-bold' : ''}`}>
                {tab.label}
              </span>
              {isActive && (
                <span className="absolute bottom-1 w-4 h-0.5 bg-blue-500 rounded-full" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
