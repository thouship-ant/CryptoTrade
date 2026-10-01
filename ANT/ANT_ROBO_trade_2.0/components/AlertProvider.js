'use client';

import { createContext, useContext, useState } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

const AlertContext = createContext();

export const useAlert = () => {
  const context = useContext(AlertContext);
  if (!context) {
    throw new Error('useAlert must be used within AlertProvider');
  }
  return context;
};

export function AlertProvider({ children }) {
  const [alerts, setAlerts] = useState([]);

  const showAlert = (message, type = 'info', duration = 5000) => {
    const id = Date.now();
    const newAlert = { id, message, type };
    
    setAlerts(prev => [...prev, newAlert]);

    if (duration > 0) {
      setTimeout(() => {
        removeAlert(id);
      }, duration);
    }
  };

  const removeAlert = (id) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id));
  };

  const success = (message, duration) => showAlert(message, 'success', duration);
  const error = (message, duration) => showAlert(message, 'error', duration);
  const warning = (message, duration) => showAlert(message, 'warning', duration);
  const info = (message, duration) => showAlert(message, 'info', duration);

  return (
    <AlertContext.Provider value={{ showAlert, success, error, warning, info }}>
      {children}
      <AlertContainer alerts={alerts} onRemove={removeAlert} />
    </AlertContext.Provider>
  );
}

function AlertContainer({ alerts, onRemove }) {
  return (
    <div className="fixed top-4 right-4 z-[9999] space-y-3 max-w-md">
      {alerts.map(alert => (
        <AlertMessage
          key={alert.id}
          alert={alert}
          onClose={() => onRemove(alert.id)}
        />
      ))}
    </div>
  );
}

function AlertMessage({ alert, onClose }) {
  const { type, message } = alert;

  const config = {
    success: {
      bg: 'bg-green-50',
      border: 'border-green-500',
      text: 'text-green-800',
      icon: CheckCircle,
      iconColor: 'text-green-500'
    },
    error: {
      bg: 'bg-red-50',
      border: 'border-red-500',
      text: 'text-red-800',
      icon: AlertCircle,
      iconColor: 'text-red-500'
    },
    warning: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-500',
      text: 'text-yellow-800',
      icon: AlertTriangle,
      iconColor: 'text-yellow-500'
    },
    info: {
      bg: 'bg-amber-50',
      border: 'border-amber-500',
      text: 'text-amber-800',
      icon: Info,
      iconColor: 'text-amber-500'
    }
  };

  const { bg, border, text, icon: Icon, iconColor } = config[type] || config.info;

  return (
    <div
      className={`${bg} ${text} border-l-4 ${border} p-4 rounded-lg shadow-lg animate-in slide-in-from-right duration-300 min-w-[320px]`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <Icon className={`h-5 w-5 ${iconColor} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">
            {message}
          </p>
        </div>
        <button
          onClick={onClose}
          className={`${iconColor} hover:opacity-70 transition-opacity flex-shrink-0`}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
