import React from 'react';
import { Calendar, Clock, Users, Utensils, User, Phone, CheckCircle2, AlertTriangle, Beer } from 'lucide-react';

export interface SlotState {
  date?: string | null;
  time?: string | null;
  guests?: number | null;
  seat_type?: string | null;
  course_name?: string | null;
  customer_name?: string | null;
  phone_number?: string | null;
  allergies?: string[];
  pre_orders?: Array<{ name: string; quantity: number }>;
  special_requests?: string | null;
}

interface LiveReservationCardProps {
  slots: SlotState;
  stage: string;
  bookingCode?: string | null;
  shopName?: string;
}

export const LiveReservationCard: React.FC<LiveReservationCardProps> = ({
  slots,
  stage,
  bookingCode,
  shopName = '炭火焼鳥 鳥神 渋谷本店',
}) => {
  const isConfirmed = stage === 'confirmed' || stage === 'additional_inquiry' || stage === 'completed';
  const isCompleted = stage === 'completed';

  return (
    <div className="flex flex-col bg-slate-900/90 rounded-2xl border border-slate-800 p-6 shadow-2xl backdrop-blur-md w-full">
      {/* ヘッダー */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
        <div>
          <span className="text-[10px] uppercase font-bold text-orange-400 tracking-wider">
            {shopName}
          </span>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            リアルタイム予約プレビュー
          </h2>
        </div>

        {/* ステータスバッジ */}
        <div>
          {isCompleted ? (
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" /> 全予約手続き完了
            </span>
          ) : isConfirmed ? (
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> 基本予約確定済
            </span>
          ) : (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse">
              ● 音声ヒアリング中
            </span>
          )}
        </div>
      </div>

      {/* 予約番号バナー（確定時） */}
      {bookingCode && (
        <div className="mb-5 p-3.5 bg-gradient-to-r from-orange-950/60 via-slate-900 to-orange-950/60 rounded-xl border border-orange-500/30 flex items-center justify-between">
          <span className="text-xs text-slate-400">ご予約受付番号:</span>
          <span className="text-base font-black font-mono text-orange-400 tracking-wider">
            {bookingCode}
          </span>
        </div>
      )}

      {/* スロット項目一覧（話すたびに埋まる！） */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        {/* 来店日 */}
        <div className={`p-3 rounded-xl border transition-all ${
          slots.date ? 'bg-slate-800/80 border-slate-700 shadow-md' : 'bg-slate-950/50 border-slate-800/60 opacity-60'
        }`}>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Calendar className="w-3.5 h-3.5 text-orange-400" />
            <span>ご来店日</span>
          </div>
          <div className="text-sm font-bold text-slate-100 font-mono">
            {slots.date || 'お伺い中...'}
          </div>
        </div>

        {/* 時間 */}
        <div className={`p-3 rounded-xl border transition-all ${
          slots.time ? 'bg-slate-800/80 border-slate-700 shadow-md' : 'bg-slate-950/50 border-slate-800/60 opacity-60'
        }`}>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Clock className="w-3.5 h-3.5 text-orange-400" />
            <span>ご来店時間</span>
          </div>
          <div className="text-sm font-bold text-slate-100 font-mono">
            {slots.time ? `${slots.time} 〜` : 'お伺い中...'}
          </div>
        </div>

        {/* 人数 */}
        <div className={`p-3 rounded-xl border transition-all ${
          slots.guests ? 'bg-slate-800/80 border-slate-700 shadow-md' : 'bg-slate-950/50 border-slate-800/60 opacity-60'
        }`}>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Users className="w-3.5 h-3.5 text-orange-400" />
            <span>ご利用人数</span>
          </div>
          <div className="text-sm font-bold text-slate-100">
            {slots.guests ? `${slots.guests} 名様` : 'お伺い中...'}
          </div>
        </div>

        {/* コース */}
        <div className={`p-3 rounded-xl border transition-all ${
          slots.course_name ? 'bg-slate-800/80 border-slate-700 shadow-md' : 'bg-slate-950/50 border-slate-800/60 opacity-60'
        }`}>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Utensils className="w-3.5 h-3.5 text-orange-400" />
            <span>ご予約プラン / コース</span>
          </div>
          <div className="text-xs font-bold text-slate-100 truncate" title={slots.course_name || ''}>
            {slots.course_name || 'お席のみ / コース選択'}
          </div>
        </div>

        {/* お名前 */}
        <div className={`p-3 rounded-xl border transition-all ${
          slots.customer_name ? 'bg-slate-800/80 border-slate-700 shadow-md' : 'bg-slate-950/50 border-slate-800/60 opacity-60'
        }`}>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <User className="w-3.5 h-3.5 text-orange-400" />
            <span>代表者様のお名前</span>
          </div>
          <div className="text-sm font-bold text-slate-100">
            {slots.customer_name ? `${slots.customer_name} 様` : 'お伺い中...'}
          </div>
        </div>

        {/* 電話番号 */}
        <div className={`p-3 rounded-xl border transition-all ${
          slots.phone_number ? 'bg-slate-800/80 border-slate-700 shadow-md' : 'bg-slate-950/50 border-slate-800/60 opacity-60'
        }`}>
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Phone className="w-3.5 h-3.5 text-orange-400" />
            <span>お電話番号</span>
          </div>
          <div className="text-sm font-bold text-slate-100 font-mono">
            {slots.phone_number || 'お伺い中...'}
          </div>
        </div>
      </div>

      {/* ★ アディショナルセクション（基本予約確定後にスルッと展開！） */}
      {isConfirmed && (
        <div className="mt-5 pt-5 border-t border-slate-800 flex flex-col gap-3.5 animate-fadeIn">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
              ✨ 事前ヒアリング（アレルギー・事前注文）
            </span>
            <span className="text-[11px] text-slate-400">通話中に口頭で追加可能</span>
          </div>

          {/* アレルギー・配慮事項 */}
          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 mb-1.5 flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              アレルギー・苦手な食材:
            </div>
            {slots.allergies && slots.allergies.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {slots.allergies.map((allergy, i) => (
                  <span key={i} className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    ⚠️ {allergy}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">なし（「〇〇アレルギーがある」と話すと反映されます）</span>
            )}
          </div>

          {/* ファーストドリンク・事前注文料理 */}
          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 mb-1.5 flex items-center gap-1">
              <Beer className="w-3.5 h-3.5 text-orange-400" />
              事前オーダー（来店時すぐにお出しする料理・ドリンク）:
            </div>
            {slots.pre_orders && slots.pre_orders.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {slots.pre_orders.map((item, i) => (
                  <span key={i} className="px-2.5 py-0.5 rounded-lg text-xs font-bold bg-orange-500/20 text-orange-300 border border-orange-500/30">
                    🍺 {item.name} × {item.quantity}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">なし（「生ビール〇杯」「つくね〇本」と話すと反映されます）</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
