"use client";

import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Send, Upload, Sparkles, AlertTriangle, CheckCircle2, ShieldCheck, Wallet, Activity, CalendarDays, Lock } from 'lucide-react';

export default function Dashboard() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);

  const [messages, setMessages] = useState([
    { role: 'system', content: 'Welcome to FinTech Guru. Tell me what you want to buy (e.g. "Can I afford a $1500 laptop?"). I will verify your safety constraint across the next 90 days.' }
  ]);
  const [input, setInput] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [decision, setDecision] = useState<any>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [balance, setBalance] = useState(10000.0);
  const [safetyBoundary, setSafetyBoundary] = useState(1500.0);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) setToken(savedToken);
  }, []);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    const endpoint = isLogin ? '/api/v1/auth/login' : '/api/v1/auth/register';
    try {
      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': isLogin ? 'application/x-www-form-urlencoded' : 'application/json' },
        body: isLogin 
          ? new URLSearchParams({ username, password }) 
          : JSON.stringify({ username, password })
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
        fetchProfile(data.access_token);
      } else {
        alert("Auth failed");
      }
    } catch (err) {
      alert("Network error");
    }
  };

  const fetchProfile = async (currentToken: string) => {
    const res = await fetch(`${apiUrl}/api/v1/auth/me`, {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (res.ok) {
      const me = await res.json();
      const profRes = await fetch(`${apiUrl}/api/v1/profile/${me.user_id}`, {
        headers: { 'Authorization': `Bearer ${currentToken}` }
      });
      if (profRes.ok) {
        const prof = await profRes.json();
        setBalance(prof.current_available_balance);
        setSafetyBoundary(prof.minimum_balance_to_keep);
      }
    }
  };

  useEffect(() => {
    if (token) fetchProfile(token);
  }, [token]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !token) return;

    const userMsg = input;
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setIsAnalyzing(true);

    try {
      const res = await fetch(`${apiUrl}/api/v1/assistant/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: userMsg })
      });

      if (!res.ok) {
        throw new Error(`API returned ${res.status}`);
      }

      const data = await res.json();
      
      if (data.decision) {
        setDecision(data.decision);
        
        const mockForecast = Array.from({ length: 90 }).map((_, i) => {
          const d = new Date();
          d.setDate(d.getDate() + i);
          let b = balance;
          
          if (data.decision.plans && data.decision.plans.length > 0) {
            const plan = data.decision.plans[0];
            plan.schedule.forEach((pmt: any) => {
              const pmtDate = new Date(pmt.date);
              if (d >= pmtDate) b -= pmt.amount;
            });
          }
          
          return {
            date: d.toISOString().split('T')[0],
            balance: b,
            minRequired: safetyBoundary
          };
        });
        
        setChartData(mockForecast);
      } else {
        // Clear decision board for conversational intents
        setDecision(null);
        setChartData([]);
      }

      if (data.intent === "PROFILE_UPDATE") {
        fetchProfile(token);
      }
      
      setMessages(prev => [...prev, { role: 'system', content: data.reply }]);

    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'system', content: `Error: ${err.message}` }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (!token) {
    return (
      <div className="flex h-screen bg-zinc-950 items-center justify-center">
        <form onSubmit={handleAuth} className="bg-zinc-900 p-8 rounded-2xl border border-zinc-800 shadow-2xl flex flex-col gap-4 w-96">
          <div className="flex items-center gap-3 mb-4 justify-center">
            <Lock className="w-6 h-6 text-indigo-500" />
            <h2 className="text-xl font-bold text-white">FinTech Guru Auth</h2>
          </div>
          <input 
            type="text" 
            placeholder="Username" 
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-white focus:ring-2 focus:ring-indigo-500 outline-none"
            value={username} onChange={e => setUsername(e.target.value)}
          />
          <input 
            type="password" 
            placeholder="Password" 
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-white focus:ring-2 focus:ring-indigo-500 outline-none"
            value={password} onChange={e => setPassword(e.target.value)}
          />
          <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-500 text-white p-3 rounded-lg font-medium transition-colors">
            {isLogin ? "Login" : "Register"}
          </button>
          <button type="button" onClick={() => setIsLogin(!isLogin)} className="text-zinc-500 text-sm mt-2 hover:text-white">
            {isLogin ? "Need an account? Register" : "Have an account? Login"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-300 font-sans overflow-hidden">
      
      {/* Left Sidebar - Chat Interface */}
      <div className="w-[400px] border-r border-zinc-800 bg-zinc-900/50 flex flex-col backdrop-blur-xl z-10">
        <div className="p-6 border-b border-zinc-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-zinc-100 tracking-tight text-lg">FinTech Guru</h1>
            <p className="text-xs text-zinc-500">Deterministic Financial AI</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
                m.role === 'user' 
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/20 rounded-tr-sm' 
                  : 'bg-zinc-800/80 text-zinc-300 border border-zinc-700/50 rounded-tl-sm'
              }`}>
                {m.content}
              </div>
            </div>
          ))}
          {isAnalyzing && (
            <div className="flex justify-start">
              <div className="bg-zinc-800/80 border border-zinc-700/50 rounded-2xl rounded-tl-sm p-4 flex gap-2 items-center">
                <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-zinc-800 bg-zinc-900/80">
          <form onSubmit={handleSend} className="relative">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. Can I afford a $1500 laptop?" 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-full py-4 pl-5 pr-24 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-zinc-100"
            />
            <div className="absolute right-2 top-2 flex items-center gap-1">
              <button type="submit" disabled={!input.trim() || isAnalyzing} className="p-2 bg-indigo-600 text-white rounded-full hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:hover:bg-indigo-600 shadow-md shadow-indigo-900/50">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Main Dashboard Area */}
      <div className="flex-1 flex flex-col relative overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-zinc-900 via-zinc-950 to-zinc-950">
        <div className="h-24 border-b border-zinc-800/50 flex items-center px-10 gap-12 z-10 bg-zinc-950/40 backdrop-blur-md">
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold mb-1">Current Balance</p>
            <h2 className="text-3xl font-light text-zinc-100">${balance.toLocaleString()}</h2>
          </div>
          <div className="h-10 w-px bg-zinc-800"></div>
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold mb-1">Safety Boundary</p>
            <h2 className="text-3xl font-light text-emerald-400">${safetyBoundary.toLocaleString()}</h2>
          </div>
          <div className="h-10 w-px bg-zinc-800"></div>
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold mb-1">Status</p>
            <div className="flex items-center gap-2 mt-1">
              <ShieldCheck className="w-6 h-6 text-emerald-500" />
              <span className="text-lg text-zinc-200">{decision ? decision.status.replace(/_/g, ' ') : "Protected"}</span>
            </div>
          </div>
          <div className="ml-auto">
            <button onClick={() => { setToken(null); localStorage.removeItem('token'); }} className="text-zinc-500 hover:text-white text-sm">
              Logout
            </button>
          </div>
        </div>

        <div className="flex-1 p-10 overflow-y-auto z-10 flex flex-col gap-8">
          
          {!decision && (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 gap-4 opacity-50">
              <Sparkles className="w-16 h-16 text-indigo-500/50" />
              <h2 className="text-xl">I am FinTech Guru.</h2>
              <p className="max-w-md text-center">Set up your profile or ask me if you can afford a purchase. I evaluate all decisions securely against a deterministic financial engine.</p>
            </div>
          )}

          {decision && (
            <div className={`rounded-2xl border p-6 flex flex-col gap-4 animate-in slide-in-from-bottom-4 fade-in duration-500 ${
              decision.status === 'not_affordable' 
                ? 'bg-red-950/20 border-red-900/50 shadow-lg shadow-red-900/10' 
                : 'bg-emerald-950/20 border-emerald-900/50 shadow-lg shadow-emerald-900/10'
            }`}>
              <div className="flex items-start gap-4">
                {decision.status === 'not_affordable' ? (
                  <AlertTriangle className="w-8 h-8 text-red-500 shrink-0 mt-1" />
                ) : (
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 shrink-0 mt-1" />
                )}
                <div className="w-full">
                  <h3 className={`text-xl font-medium mb-2 uppercase ${decision.status === 'not_affordable' ? 'text-red-400' : 'text-emerald-400'}`}>
                    Decision: {decision.status.replace(/_/g, ' ')}
                  </h3>
                  <p className="text-zinc-300 leading-relaxed max-w-3xl">
                    {decision.explanation.summary}
                  </p>
                  
                  <div className="grid grid-cols-3 gap-6 mt-6">
                    <div className="bg-zinc-950/50 rounded-xl p-4 border border-zinc-800/50">
                      <div className="text-xs text-zinc-500 mb-1 flex items-center gap-2"><Activity className="w-3 h-3"/> Lowest Projected</div>
                      <div className="text-lg text-zinc-200">${decision.explanation.lowest_projected_balance}</div>
                    </div>
                    <div className="bg-zinc-950/50 rounded-xl p-4 border border-zinc-800/50">
                      <div className="text-xs text-zinc-500 mb-1 flex items-center gap-2"><CalendarDays className="w-3 h-3"/> Limiting Date</div>
                      <div className="text-lg text-zinc-200">{decision.explanation.limiting_date}</div>
                    </div>
                    <div className="bg-zinc-950/50 rounded-xl p-4 border border-zinc-800/50">
                      <div className="text-xs text-zinc-500 mb-1 flex items-center gap-2"><Wallet className="w-3 h-3"/> Safety Margin</div>
                      <div className={`text-lg ${decision.explanation.safety_margin < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                        ${decision.explanation.safety_margin}
                      </div>
                    </div>
                  </div>
                  
                  {decision.plans && decision.plans.length > 0 && (
                    <div className="mt-6 p-4 bg-zinc-900/80 rounded-xl border border-zinc-800">
                      <h4 className="text-sm font-semibold text-zinc-400 mb-3 uppercase tracking-wider">Recommended Plan ({decision.plans[0].method})</h4>
                      <div className="flex gap-4">
                        {decision.plans[0].schedule.map((pmt: any, idx: number) => (
                          <div key={idx} className="bg-zinc-950 px-4 py-2 rounded-lg border border-zinc-800 flex flex-col items-center">
                            <span className="text-xs text-zinc-500">{pmt.date}</span>
                            <span className="font-medium text-emerald-400">${pmt.amount}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {chartData.length > 0 && (
            <div className="flex flex-col gap-6">
              <h3 className="text-xl font-medium text-zinc-100 flex items-center gap-2">
                90-Day Cashflow Forecast
              </h3>
              <div className="h-[400px] w-full bg-zinc-900/30 border border-zinc-800/50 rounded-3xl p-6 shadow-2xl backdrop-blur-sm">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#52525b" 
                      tick={{ fill: '#71717a', fontSize: 12 }}
                      tickFormatter={(val) => val.substring(5)}
                      axisLine={false}
                      tickLine={false}
                      minTickGap={30}
                    />
                    <YAxis 
                      stroke="#52525b"
                      tick={{ fill: '#71717a', fontSize: 12 }}
                      tickFormatter={(val) => `$${val/1000}k`}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
                      itemStyle={{ color: '#e4e4e7' }}
                    />
                    <ReferenceLine y={safetyBoundary} stroke="#ef4444" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Safety Boundary', fill: '#ef4444', fontSize: 12 }} />
                    <Area 
                      type="monotone" 
                      dataKey="balance" 
                      stroke="#818cf8" 
                      strokeWidth={3}
                      fillOpacity={1} 
                      fill="url(#colorBalance)" 
                      activeDot={{ r: 6, stroke: '#18181b', strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
          
        </div>
      </div>
    </div>
  );
}
