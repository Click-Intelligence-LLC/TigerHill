import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import SessionSelector from '@/components/SessionSelector';
import { Session } from '@/types';

export default function SessionIndex() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selected, setSelected] = useState('');

  useEffect(() => {
    apiClient.getSessionsV3({ limit: 100, offset: 0 }).then(res => {
      setSessions(res.sessions);
    });
  }, []);

  const handleChange = (id: string) => {
    setSelected(id);
    if (id) navigate(`/session/${id}`);
  };

  return (
    <div className="max-w-3xl mx-auto py-10 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">对话流程</h1>
      <SessionSelector
        label="选择会话"
        sessions={sessions}
        selectedSessionId={selected}
        onSessionChange={handleChange}
      />
      <div className="pt-4">
        <Link
          to="/"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          返回会话总览
        </Link>
      </div>
    </div>
  );
}