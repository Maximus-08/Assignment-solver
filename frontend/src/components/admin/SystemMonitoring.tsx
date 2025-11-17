/**
 * System monitoring dashboard component
 * Displays health metrics and system status
 */
'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Clock } from 'lucide-react'

interface HealthCheck {
  status: string
  timestamp: string
  service: string
  version: string
  environment: string
  checks?: {
    database?: {
      status: string
      response_time_ms?: number
    }
    system?: {
      cpu_percent?: number
      memory_percent?: number
      memory_available_mb?: number
      disk_percent?: number
      disk_free_gb?: number
    }
    backend?: {
      status: string
      response_time_ms?: number
    }
  }
}

interface SystemMetrics {
  frontend: HealthCheck | null
  backend: HealthCheck | null
  lastUpdated: string
  isLoading: boolean
  error: string | null
}

export default function SystemMonitoring() {
  const [metrics, setMetrics] = useState<SystemMetrics>({
    frontend: null,
    backend: null,
    lastUpdated: '',
    isLoading: true,
    error: null,
  })

  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchHealthMetrics = async () => {
    setMetrics(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      // Fetch frontend health
      const frontendResponse = await fetch('/api/health')
      const frontendData = await frontendResponse.json()

      // Fetch backend health
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000'
      const backendResponse = await fetch(`${backendUrl}/api/v1/health/detailed`)
      const backendData = await backendResponse.json()

      setMetrics({
        frontend: frontendData,
        backend: backendData,
        lastUpdated: new Date().toISOString(),
        isLoading: false,
        error: null,
      })
    } catch (error) {
      console.error('Failed to fetch health metrics:', error)
      setMetrics(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch metrics',
      }))
    }
  }

  useEffect(() => {
    fetchHealthMetrics()

    if (autoRefresh) {
      const interval = setInterval(fetchHealthMetrics, 30000) // Refresh every 30 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'ready':
      case 'alive':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'degraded':
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'unhealthy':
      case 'error':
      case 'unreachable':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variant: 'default' | 'secondary' | 'destructive' = 
      status.toLowerCase() === 'healthy' ? 'default' : 
      status.toLowerCase() === 'degraded' ? 'secondary' : 'destructive'
    
    return (
      <Badge variant={variant} className="flex items-center gap-1">
        {getStatusIcon(status)}
        {status.toUpperCase()}
      </Badge>
    )
  }

  const formatResponseTime = (ms: number | null | undefined) => {
    if (ms === null || ms === undefined) return 'N/A'
    return `${ms}ms`
  }

  const formatBytes = (bytes: number | null | undefined) => {
    if (bytes === null || bytes === undefined) return 'N/A'
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatPercentage = (percent: number | null | undefined) => {
    if (percent === null || percent === undefined) return 'N/A'
    return `${percent.toFixed(1)}%`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">System Monitoring</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Disable Auto-refresh' : 'Enable Auto-refresh'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHealthMetrics}
            disabled={metrics.isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${metrics.isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {metrics.error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-700">
              <XCircle className="h-4 w-4" />
              <span>Error: {metrics.error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Frontend Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Frontend Service
              {metrics.frontend && getStatusBadge(metrics.frontend.status)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {metrics.frontend ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Version:</span> {metrics.frontend.version}
                  </div>
                  <div>
                    <span className="font-medium">Environment:</span> {metrics.frontend.environment}
                  </div>
                </div>
                
                {metrics.frontend.checks?.backend && (
                  <div className="border-t pt-3">
                    <h4 className="font-medium mb-2">Backend Connectivity</h4>
                    <div className="flex items-center justify-between">
                      {getStatusBadge(metrics.frontend.checks.backend.status)}
                      <span className="text-sm text-gray-600">
                        {formatResponseTime(metrics.frontend.checks.backend.response_time_ms)}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">Loading...</div>
            )}
          </CardContent>
        </Card>

        {/* Backend Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Backend Service
              {metrics.backend && getStatusBadge(metrics.backend.status)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {metrics.backend ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Version:</span> {metrics.backend.version}
                  </div>
                  <div>
                    <span className="font-medium">Environment:</span> {metrics.backend.environment}
                  </div>
                </div>

                {metrics.backend.checks?.database && (
                  <div className="border-t pt-3">
                    <h4 className="font-medium mb-2">Database</h4>
                    <div className="flex items-center justify-between">
                      {getStatusBadge(metrics.backend.checks.database.status)}
                      <span className="text-sm text-gray-600">
                        {formatResponseTime(metrics.backend.checks.database.response_time_ms)}
                      </span>
                    </div>
                  </div>
                )}

                {metrics.backend.checks?.system && (
                  <div className="border-t pt-3">
                    <h4 className="font-medium mb-2">System Resources</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>CPU: {formatPercentage(metrics.backend.checks.system.cpu_percent)}</div>
                      <div>Memory: {formatPercentage(metrics.backend.checks.system.memory_percent)}</div>
                      <div>Available: {formatBytes((metrics.backend.checks.system.memory_available_mb || 0) * 1024 * 1024)}</div>
                      <div>Disk: {formatPercentage(metrics.backend.checks.system.disk_percent)}</div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">Loading...</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Last Updated */}
      {metrics.lastUpdated && (
        <div className="text-sm text-gray-500 text-center">
          Last updated: {new Date(metrics.lastUpdated).toLocaleString()}
        </div>
      )}
    </div>
  )
}