const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

export async function api(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {'Content-Type':'application/json', ...(options.headers || {})};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, {...options, headers});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.message || 'Request failed');
  return data;
}
export async function login(username,password){
  return api('/auth/login',{method:'POST',body:JSON.stringify({username,password})});
}
