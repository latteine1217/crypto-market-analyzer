'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAlerts, createAlert, deleteAlert } from '@/lib/api-client'
import { formatPrice } from '@/lib/utils'
import type { Alert } from '@/types/market'

interface Props {
  currentSymbol: string
  currentPrice?: number
}

export function AlertsManager({ currentSymbol, currentPrice }: Props) {
  const [targetPrice, setTargetPrice] = useState('')
  const [condition, setCondition] = useState<'above' | 'below'>('above')
  const [isExpanded, setIsExpanded] = useState(false)
  
  const queryClient = useQueryClient()

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
    refetchInterval: 5000, 
  })

  const createMutation = useMutation({
    mutationFn: (data: { symbol: string, condition: 'above' | 'below', target_price: number }) => 
      createAlert(data.symbol, data.condition, data.target_price),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      setTargetPrice('')
    }
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    }
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!targetPrice || isNaN(Number(targetPrice))) return
    
    createMutation.mutate({
      symbol: currentSymbol,
      condition,
      target_price: Number(targetPrice)
    })
  }

  const symbolAlerts = alerts?.filter(a => a.symbol === currentSymbol) || []
  const otherAlerts = alerts?.filter(a => a.symbol !== currentSymbol) || []

  return (
    <div className="card">
      <div className="card-header flex justify-between items-center cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
        <h2 className="font-semibold">Price Alerts</h2>
        <span className="text-sm text-gray-400">
          {symbolAlerts.filter(a => a.is_active).length} Active
        </span>
      </div>

      <div className={`p-4 ${isExpanded ? '' : 'hidden'}`}>
        {/* Create Form */}
        <form onSubmit={handleCreate} className="mb-6 space-y-3">
          <div className="flex gap-2 items-center">
            <span className="text-gray-400 text-sm">Notify when {currentSymbol} is</span>
            <select 
              value={condition}
              onChange={(e) => setCondition(e.target.value as 'above' | 'below')}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
            >
              <option value="above">Above</option>
              <option value="below">Below</option>
            </select>
          </div>
          
          <div className="flex gap-2">
            <input
              type="number"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
              placeholder={currentPrice ? `${currentPrice}` : "Target Price"}
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              step="0.00000001"
            />
            <button 
              type="submit" 
              disabled={createMutation.isPending}
              className="btn-primary px-4 py-1.5 text-sm whitespace-nowrap"
            >
              {createMutation.isPending ? 'Adding...' : 'Add Alert'}
            </button>
          </div>
        </form>

        {/* Alerts List */}
        <div className="space-y-4">
          {symbolAlerts.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Current Symbol ({currentSymbol})</h3>
              <ul className="space-y-2">
                {symbolAlerts.map(alert => (
                  <AlertItem key={alert.id} alert={alert} onDelete={() => deleteMutation.mutate(alert.id)} />
                ))}
              </ul>
            </div>
          )}

          {otherAlerts.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Other Alerts</h3>
              <ul className="space-y-2">
                {otherAlerts.map(alert => (
                  <AlertItem key={alert.id} alert={alert} onDelete={() => deleteMutation.mutate(alert.id)} />
                ))}
              </ul>
            </div>
          )}

          {(!alerts || alerts.length === 0) && (
            <p className="text-sm text-gray-500 text-center py-2">No alerts set</p>
          )}
        </div>
      </div>
    </div>
  )
}

function AlertItem({ alert, onDelete }: { alert: Alert, onDelete: () => void }) {
  return (
    <li className={`flex justify-between items-center p-2 rounded border ${
      alert.is_triggered 
        ? 'bg-red-900/20 border-red-900/50' 
        : 'bg-gray-800/50 border-gray-700'
    }`}>
      <div className="flex flex-col">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sm">{alert.symbol}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            alert.condition === 'above' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
          }`}>
            {alert.condition === 'above' ? '>' : '<'}
          </span>
          <span className="font-mono text-sm">${formatPrice(alert.target_price)}</span>
        </div>
        {alert.is_triggered && (
          <span className="text-xs text-red-400 mt-1">
            Triggered: {new Date(alert.triggered_at!).toLocaleString()}
          </span>
        )}
      </div>
      <button 
        onClick={onDelete}
        className="text-gray-500 hover:text-red-500 p-1"
        title="Delete Alert"
      >
        ✕
      </button>
    </li>
  )
}