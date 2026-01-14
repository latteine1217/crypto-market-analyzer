'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchNews } from '@/lib/api-client';
import { formatDistanceToNow } from 'date-fns';

export const NewsList: React.FC = () => {
  const { data: news, isLoading, error } = useQuery({
    queryKey: ['news'],
    queryFn: () => fetchNews(),
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) return <div className="p-4 text-gray-400">Loading news...</div>;
  if (error) return <div className="p-4 text-red-400">Failed to load news</div>;

  return (
    <div className="card overflow-hidden">
      <h3 className="card-header flex justify-between items-center">
        <span>Latest Crypto News</span>
        <span className="text-xs font-normal text-gray-400">Source: CryptoPanic</span>
      </h3>
      <div className="divide-y divide-gray-800 max-h-[600px] overflow-y-auto">
        {news?.map((item) => (
          <div key={item.id} className="p-4 hover:bg-gray-800/50 transition-colors">
            <div className="flex justify-between items-start gap-4 mb-1">
              <a 
                href={item.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-sm font-medium hover:text-primary transition-colors line-clamp-2"
              >
                {item.title}
              </a>
              <span className="text-[10px] text-gray-500 whitespace-nowrap">
                {formatDistanceToNow(new Date(item.published_at), { addSuffix: true })}
              </span>
            </div>
            
            <div className="flex items-center gap-3 mt-2">
              <span className="text-[10px] bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">
                {item.source_domain}
              </span>
              
              <div className="flex items-center gap-2">
                {item.votes_positive > 0 && (
                  <span className="text-[10px] text-green-400">
                    👍 {item.votes_positive}
                  </span>
                )}
                {item.votes_important > 0 && (
                  <span className="text-[10px] text-yellow-400">
                    🔥 {item.votes_important}
                  </span>
                )}
              </div>

              <div className="flex gap-1">
                {item.currencies?.slice(0, 3).map(curr => (
                  <span key={curr.code} className="text-[10px] text-primary">
                    #{curr.code}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
