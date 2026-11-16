import React, { useState, useEffect } from 'react';
import { AlertTriangle, Beer, MapPin, RefreshCw } from 'lucide-react';

interface ReservationItem {
  id: number;
  booking_code: string;
  date: string;
  time: string;
  guests: number;
  seat_type: string;
  course_name: string;
  customer_name: string;
  phone_number: string;
  allergies: string[];
  pre_orders: Array<{ name: string; quantity: number }>;
  special_requests?: string | null;
  status: string;
  created_at: string;
}

export const BookingCalendar: React.FC = () => {
  const [reservations, setReservations] = useState<ReservationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeView, setActiveView] = useState<'kitchen' | 'list'>('kitchen');

  const fetchReservations = () => {
    setLoading(true);
    fetch('/api/reservations')
      .then((res) => res.json())
      .then((data) => {
        setReservations(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchReservations();
  }, []);

  return (
    <div className="flex flex-col gap-6 max-w-6xl mx-auto">
      {/* 管理ヘッダー */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-xl">
        <div>
          <span className="text-[10px] uppercase font-bold text-orange-400 tracking-wider">
            店舗バックヤード・予約台帳
          </span>
          <h2 className="text-xl font-black text-slate-100 flex items-center gap-2">
            予約台帳 ＆ 厨房・ホール即応伝票
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            音声予約ボットから直接届いた最新の予約一覧。アレルギーと事前注文を最優先表示します。
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* ビュー切り替え */}
          <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setActiveView('kitchen')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                activeView === 'kitchen' ? 'bg-orange-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              🍳 厨房・ホール伝票ビュー
            </button>
            <button
              onClick={() => setActiveView('list')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                activeView === 'list' ? 'bg-orange-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📋 一覧テーブル
            </button>
          </div>

          <button
            onClick={fetchReservations}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="更新"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 将来のGoogle Maps連携ステータスバナー */}
      <div className="bg-slate-900/60 rounded-xl border border-slate-800/80 p-4 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>
            Google マップ連携準備: <span className="text-slate-200 font-mono">Place ID: ChIJ_wom9f2LGGAR79K1XqQ</span>
          </span>
        </div>
        <span className="text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 font-semibold">
          ● Reserve with Google 連携準備完了
        </span>
      </div>

      {/* 1. 厨房・ホール伝票ビュー */}
      {activeView === 'kitchen' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reservations.length === 0 ? (
            <div className="col-span-full py-16 text-center text-slate-500 text-sm">
              現在確定した予約はありません。音声予約ボットから予約を行ってください。
            </div>
          ) : (
            reservations.map((r) => (
              <div
                key={r.id}
                className="bg-slate-900/90 rounded-xl border border-slate-800 p-5 shadow-lg flex flex-col justify-between gap-4"
              >
                <div>
                  {/* ヘッダー: 日時と人数 */}
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                    <div className="flex items-center gap-1.5 text-orange-400 font-black text-base font-mono">
                      <span>{r.date}</span>
                      <span>{r.time}</span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-800 text-slate-200 border border-slate-700">
                      {r.guests} 名様
                    </span>
                  </div>

                  {/* 顧客情報 */}
                  <div className="text-sm font-bold text-slate-100 mb-1">
                    {r.customer_name} 様
                    <span className="text-xs text-slate-400 font-normal ml-2 font-mono">{r.phone_number}</span>
                  </div>
                  <div className="text-xs text-slate-400 mb-3 truncate">
                    プラン: <span className="text-slate-300 font-semibold">{r.course_name}</span>
                  </div>

                  {/* ★ アレルギー警告（超重要） */}
                  {r.allergies && r.allergies.length > 0 && (
                    <div className="mb-2.5 p-2 bg-red-950/40 rounded-lg border border-red-500/30">
                      <div className="text-[11px] font-bold text-red-400 flex items-center gap-1 mb-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> アレルギー配慮！
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {r.allergies.map((a, i) => (
                          <span key={i} className="text-xs font-bold text-red-200 bg-red-900/40 px-2 py-0.5 rounded">
                            {a}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* ★ 特記事項（お子様連れ・ベビーカー・記念日など） */}
                  {r.special_requests && (
                    <div className="mb-2.5 p-2 bg-blue-950/40 rounded-lg border border-blue-500/30">
                      <div className="text-[11px] font-bold text-blue-400 flex items-center gap-1 mb-0.5">
                        <span>👶 店内・席配慮（特記事項）</span>
                      </div>
                      <div className="text-xs font-semibold text-blue-200">
                        {r.special_requests}
                      </div>
                    </div>
                  )}

                  {/* ★ 事前オーダー（来店即出しドリンク・料理） */}
                  {r.pre_orders && r.pre_orders.length > 0 && (
                    <div className="p-2.5 bg-orange-950/30 rounded-lg border border-orange-500/30">
                      <div className="text-[11px] font-bold text-orange-400 flex items-center gap-1 mb-1">
                        <Beer className="w-3.5 h-3.5" /> ファーストオーダー（来店即出し）
                      </div>
                      <div className="space-y-1">
                        {r.pre_orders.map((item, i) => (
                          <div key={i} className="flex justify-between text-xs font-bold text-orange-200">
                            <span>{item.name}</span>
                            <span>× {item.quantity}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* フッター */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-[11px] text-slate-500 font-mono">
                  <span>番号: {r.booking_code}</span>
                  <span className="text-emerald-400 font-bold uppercase">{r.status}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* 2. 一覧テーブル */}
      {activeView === 'list' && (
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-800/60 text-slate-400 text-[11px] uppercase border-b border-slate-700">
              <tr>
                <th className="py-3 px-3">受付番号</th>
                <th className="py-3 px-3">来店日時</th>
                <th className="py-3 px-3 text-center">人数</th>
                <th className="py-3 px-3">お名前</th>
                <th className="py-3 px-3">お電話</th>
                <th className="py-3 px-3">コース</th>
                <th className="py-3 px-3">アレルギー</th>
                <th className="py-3 px-3">事前注文</th>
                <th className="py-3 px-3">特記事項・配慮</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {reservations.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/30">
                  <td className="py-3 px-3 font-mono font-bold text-orange-400">{r.booking_code}</td>
                  <td className="py-3 px-3 font-mono">{r.date} {r.time}</td>
                  <td className="py-3 px-3 text-center font-bold">{r.guests}名</td>
                  <td className="py-3 px-3 font-semibold">{r.customer_name}</td>
                  <td className="py-3 px-3 font-mono text-slate-400">{r.phone_number}</td>
                  <td className="py-3 px-3 max-w-[150px] truncate">{r.course_name}</td>
                  <td className="py-3 px-3 text-red-400 font-bold">
                    {r.allergies?.join(', ') || '-'}
                  </td>
                  <td className="py-3 px-3 text-orange-300">
                    {r.pre_orders?.map((p) => `${p.name}x${p.quantity}`).join(', ') || '-'}
                  </td>
                  <td className="py-3 px-3 text-blue-300">
                    {r.special_requests || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
