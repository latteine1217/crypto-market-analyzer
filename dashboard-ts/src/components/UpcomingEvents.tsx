'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchUpcomingEvents } from '@/lib/api-client';
import type { Event } from '@/types/market';
import { useState } from 'react';

export function UpcomingEvents() {
  const [selectedSources, setSelectedSources] = useState<string[]>(['fred_calendar', 'coinmarketcal']);
  const [days, setDays] = useState(7);

  const { data, isLoading } = useQuery({
    queryKey: ['upcoming-events', days, selectedSources.join(',')],
    queryFn: () => fetchUpcomingEvents(days),
    refetchInterval: 300000, // 每 5 分鐘刷新
  });

  const toggleSource = (source: string) => {
    if (selectedSources.includes(source)) {
      if (selectedSources.length > 1) {
        setSelectedSources(selectedSources.filter(s => s !== source));
      }
    } else {
      setSelectedSources([...selectedSources, source]);
    }
  };

  const filteredEvents = data?.eventsByDate 
    ? Object.fromEntries(
        Object.entries(data.eventsByDate).map(([date, events]) => [
          date,
          events.filter(e => selectedSources.includes(e.source))
        ])
      )
    : {};

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'text-red-500';
      case 'medium': return 'text-yellow-500';
      case 'low': return 'text-gray-500';
      default: return 'text-gray-400';
    }
  };

  const getImpactDot = (impact: string) => {
    switch (impact) {
      case 'high': return 'bg-red-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-gray-500';
      default: return 'bg-gray-400';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const dateOnly = date.toDateString();
    const todayOnly = today.toDateString();
    const tomorrowOnly = tomorrow.toDateString();

    if (dateOnly === todayOnly) {
      return { label: 'Today', date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) };
    } else if (dateOnly === tomorrowOnly) {
      return { label: 'Tomorrow', date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) };
    } else {
      return { 
        label: date.toLocaleDateString('en-US', { weekday: 'long' }), 
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) 
      };
    }
  };

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
  };

  const activeCount = Object.values(filteredEvents).reduce((sum, events) => sum + events.length, 0);

  if (isLoading) {
    return (
      <div className="card p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-1/3"></div>
          <div className="h-32 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-indigo-400">Upcoming Events</h2>
        
        {/* Calendar Filter */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-indigo-400 font-semibold">{activeCount} Event{activeCount !== 1 ? 's' : ''}</span>
          <button
            onClick={() => setSelectedSources(prev => 
              prev.length === 2 ? [] : ['fred_calendar', 'coinmarketcal']
            )}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-900/30 border border-indigo-700/50 hover:bg-indigo-900/50 transition-colors"
          >
            <div className="flex gap-1">
              <div 
                className={`w-3 h-3 rounded-full transition-opacity ${
                  selectedSources.includes('fred_calendar') ? 'bg-blue-500' : 'bg-gray-600'
                }`}
              />
              <div 
                className={`w-3 h-3 rounded-full transition-opacity ${
                  selectedSources.includes('coinmarketcal') ? 'bg-orange-500' : 'bg-gray-600'
                }`}
              />
            </div>
            <span className="text-xs text-gray-400 font-medium">2 Calendars</span>
          </button>
        </div>
      </div>

      {/* Events List */}
      <div className="space-y-6">
        {Object.entries(filteredEvents).length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <svg className="w-16 h-16 mx-auto mb-4 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-lg">No upcoming events</p>
            <p className="text-sm mt-2">Check back later for updates</p>
          </div>
        ) : (
          Object.entries(filteredEvents)
            .slice(0, 5)  // 只顯示前 5 天
            .map(([date, events]) => {
              const { label, date: dateStr } = formatDate(date);
              
              if (events.length === 0) return null;

              return (
                <div key={date} className="flex gap-4">
                  {/* Date Column */}
                  <div className="flex flex-col items-end min-w-[100px]">
                    <div className="text-sm text-indigo-400 font-medium">{label}</div>
                    <div className="text-lg font-bold text-gray-300">{dateStr}</div>
                  </div>

                  {/* Divider */}
                  <div className="w-px bg-gray-800"></div>

                  {/* Events Column */}
                  <div className="flex-1 space-y-3">
                    {events.length === 0 ? (
                      <div className="text-gray-500 italic py-2">No Upcoming Events</div>
                    ) : (
                      events.slice(0, 5).map((event) => (
                        <div
                          key={event.id}
                          className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-900/30 transition-colors group"
                        >
                          {/* Impact Indicator */}
                          <div className="flex-shrink-0 mt-1">
                            <div className={`w-2 h-2 rounded-full ${getImpactDot(event.impact)}`}></div>
                          </div>

                          {/* Event Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1">
                                <h4 className="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">
                                  {event.title}
                                </h4>
                                {event.description && (
                                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                                    {event.description}
                                  </p>
                                )}
                                <div className="flex items-center gap-3 mt-2 text-xs">
                                  <span className="text-gray-600">{formatTime(event.event_date)}</span>
                                  <span className={`${getImpactColor(event.impact)} capitalize`}>
                                    {event.impact}
                                  </span>
                                  {event.country && (
                                    <span className="text-gray-600">{event.country}</span>
                                  )}
                                  {event.source === 'fred_calendar' && (
                                    <span className="px-2 py-0.5 rounded bg-blue-900/30 text-blue-400 text-[10px] font-medium">
                                      Economic
                                    </span>
                                  )}
                                  {event.source === 'coinmarketcal' && (
                                    <span className="px-2 py-0.5 rounded bg-orange-900/30 text-orange-400 text-[10px] font-medium">
                                      Crypto
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })
        )}
      </div>

      {/* Footer - View More */}
      {Object.entries(filteredEvents).length > 5 && (
        <div className="mt-6 pt-4 border-t border-gray-800">
          <button className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
            View all {activeCount} events →
          </button>
        </div>
      )}
    </div>
  );
}
