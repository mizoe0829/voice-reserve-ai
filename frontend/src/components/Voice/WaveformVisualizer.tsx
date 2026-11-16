import React from 'react';

interface WaveformVisualizerProps {
  isActive: boolean;
  color?: string;
}

export const WaveformVisualizer: React.FC<WaveformVisualizerProps> = ({
  isActive,
  color = 'bg-orange-500',
}) => {
  return (
    <div className="flex items-center justify-center gap-1.5 h-12 py-2">
      {[40, 75, 90, 60, 100, 80, 50, 95, 70, 45].map((height, i) => (
        <div
          key={i}
          className={`w-1 rounded-full transition-all duration-300 ${color} ${
            isActive ? 'animate-pulse' : 'opacity-20'
          }`}
          style={{
            height: isActive ? `${Math.max(15, (height * (0.6 + Math.random() * 0.4)))}%` : '15%',
            animationDelay: `${i * 80}ms`,
          }}
        />
      ))}
    </div>
  );
};
