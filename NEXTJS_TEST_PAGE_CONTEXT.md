# StoreDesk AI - NextJS Test Page Implementation Context

## 🎯 **PURPOSE**

NextJS Test Page provides a comprehensive testing interface for StoreDesk AI service with real-time debugging, scenario testing, and performance monitoring capabilities.

---

## 📋 **ARCHITECTURE OVERVIEW**

### **Component Structure**
```
NextJS Test Page (/storedesk-test)
├── Main Dashboard Layout
├── Request Panel (Input & Configuration)
├── Response Panel (Results & Analysis)
├── Debug Panel (Logs & State)
├── Scenario Switcher (Pre-built test cases)
└── Performance Monitor (Timing & Metrics)
```

### **Technology Stack**
- **Frontend**: Next.js 14 with App Router
- **UI Components**: Tailwind CSS + Shadcn/ui
- **State Management**: React Context + Zustand
- **Real-time**: WebSocket connections for live updates
- **Charts**: Recharts for performance visualization
- **HTTP Client**: Axios for API requests

---

## 🏗️ **PROJECT STRUCTURE**

### **File Organization**
```
storedesk-test/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── storedesk-test/
│       ├── layout.tsx
│       └── page.tsx
├── components/
│   ├── ui/
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── textarea.tsx
│   │   ├── card.tsx
│   │   ├── tabs.tsx
│   │   └── badge.tsx
│   ├── RequestPanel.tsx
│   ├── ResponsePanel.tsx
│   ├── DebugPanel.tsx
│   ├── ScenarioSwitcher.tsx
│   └── PerformanceMonitor.tsx
├── lib/
│   ├── api.ts
│   ├── scenarios.ts
│   └── utils.ts
├── hooks/
│   ├── useWebSocket.ts
│   ├── useStoreDeskAI.ts
│   └── usePerformanceMonitor.ts
├── store/
│   └── testStore.ts
└── types/
    └── test.ts
```

---

## 🛠️ **CORE IMPLEMENTATION**

### **1. Package Configuration**
```json
// package.json
{
  "name": "storedesk-test",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "recharts": "^2.8.0",
    "lucide-react": "^0.294.0",
    "tailwindcss": "^3.3.0",
    "@radix-ui/react-tabs": "^1.0.4",
    "@radix-ui/react-button": "^1.0.4",
    "@radix-ui/react-textarea": "^1.0.4",
    "@radix-ui/react-input": "^1.0.4",
    "@radix-ui/react-card": "^1.0.4",
    "@radix-ui/react-badge": "^1.0.4",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.8.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "14.0.0",
    "postcss": "^8.4.0",
    "typescript": "^5.2.0"
  }
}
```

### **2. Main Test Page Layout**
```tsx
// app/storedesk-test/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RequestPanel } from '@/components/RequestPanel';
import { ResponsePanel } from '@/components/ResponsePanel';
import { DebugPanel } from '@/components/DebugPanel';
import { ScenarioSwitcher } from '@/components/ScenarioSwitcher';
import { PerformanceMonitor } from '@/components/PerformanceMonitor';
import { useTestStore } from '@/store/testStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function StoreDeskTestPage() {
  const { 
    isTestRunning, 
    currentTest, 
    performanceMetrics,
    resetTest 
  } = useTestStore();

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">StoreDesk AI Test Dashboard</h1>
            <p className="text-gray-600 mt-2">
              Comprehensive testing interface for StoreDesk AI service
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              isTestRunning 
                ? 'bg-yellow-100 text-yellow-800' 
                : 'bg-green-100 text-green-800'
            }`}>
              {isTestRunning ? 'Testing' : 'Ready'}
            </div>
            <button
              onClick={resetTest}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Reset Test
            </button>
          </div>
        </div>

        {/* Scenario Switcher */}
        <ScenarioSwitcher />

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            <RequestPanel />
            <DebugPanel />
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            <ResponsePanel />
            <PerformanceMonitor />
          </div>
        </div>

        {/* Performance Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Test Performance Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {performanceMetrics.totalRequests}
                </div>
                <div className="text-sm text-gray-600">Total Requests</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {performanceMetrics.successfulRequests}
                </div>
                <div className="text-sm text-gray-600">Successful</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {performanceMetrics.averageResponseTime.toFixed(0)}ms
                </div>
                <div className="text-sm text-gray-600">Avg Response Time</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {performanceMetrics.errorRate.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600">Error Rate</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

### **3. Request Panel Component**
```tsx
// components/RequestPanel.tsx
'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useTestStore } from '@/store/testStore';
import { TestScenario } from '@/lib/scenarios';

export function RequestPanel() {
  const { 
    currentRequest, 
    setCurrentRequest, 
    sendRequest, 
    isTestRunning 
  } = useTestStore();

  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([
    '7626ff3a-1234-5678-9abc-123456789abc'
  ]);

  const handleSendRequest = async () => {
    if (!currentRequest.message.trim()) {
      alert('Please enter a message to test');
      return;
    }

    await sendRequest({
      ...currentRequest,
      selectedProductIds
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Request Configuration
          <Badge variant="outline">
            {currentRequest.inputType}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Session Configuration */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Session ID
            </label>
            <Input
              value={currentRequest.sessionId}
              onChange={(e) => setCurrentRequest({
                ...currentRequest,
                sessionId: e.target.value
              })}
              placeholder="test-session-123"
              disabled={isTestRunning}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Input Type
            </label>
            <select
              value={currentRequest.inputType}
              onChange={(e) => setCurrentRequest({
                ...currentRequest,
                inputType: e.target.value
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isTestRunning}
            >
              <option value="text">Text</option>
              <option value="audio">Audio</option>
            </select>
          </div>
        </div>

        {/* User Message */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            User Message
          </label>
          <Textarea
            value={currentRequest.message}
            onChange={(e) => setCurrentRequest({
              ...currentRequest,
              message: e.target.value
            })}
            placeholder="Enter your test message here..."
            rows={4}
            disabled={isTestRunning}
          />
        </div>

        {/* User Context */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            User Context
          </label>
          <Textarea
            value={JSON.stringify(currentRequest.context, null, 2)}
            onChange={(e) => {
              try {
                const context = JSON.parse(e.target.value);
                setCurrentRequest({
                  ...currentRequest,
                  context
                });
              } catch (error) {
                // Invalid JSON, ignore
              }
            }}
            rows={6}
            className="font-mono text-sm"
            disabled={isTestRunning}
          />
        </div>

        {/* Selected Product IDs */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Selected Product IDs
          </label>
          <div className="space-y-2">
            {selectedProductIds.map((productId, index) => (
              <div key={index} className="flex items-center space-x-2">
                <Input
                  value={productId}
                  onChange={(e) => {
                    const newIds = [...selectedProductIds];
                    newIds[index] = e.target.value;
                    setSelectedProductIds(newIds);
                  }}
                  placeholder="product-id"
                  disabled={isTestRunning}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const newIds = selectedProductIds.filter((_, i) => i !== index);
                    setSelectedProductIds(newIds);
                  }}
                  disabled={isTestRunning}
                >
                  Remove
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              onClick={() => setSelectedProductIds([...selectedProductIds, ''])}
              disabled={isTestRunning}
            >
              Add Product ID
            </Button>
          </div>
        </div>

        {/* Send Button */}
        <div className="flex justify-end">
          <Button
            onClick={handleSendRequest}
            disabled={isTestRunning || !currentRequest.message.trim()}
            className="w-full"
          >
            {isTestRunning ? 'Sending...' : 'Send Request'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### **4. Response Panel Component**
```tsx
// components/ResponsePanel.tsx
'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useTestStore } from '@/store/testStore';

export function ResponsePanel() {
  const { currentResponse, currentTest } = useTestStore();
  const [activeTab, setActiveTab] = useState<'raw' | 'formatted' | 'actions'>('formatted');

  if (!currentResponse) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Response</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-500 py-8">
            No response yet. Send a request to see results.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Response
          <Badge variant={currentResponse.success ? 'default' : 'destructive'}>
            {currentResponse.success ? 'Success' : 'Error'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Response Tabs */}
        <div className="flex space-x-2 mb-4">
          {(['formatted', 'raw', 'actions'] as const).map((tab) => (
            <Button
              key={tab}
              variant={activeTab === tab ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </Button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'formatted' && (
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Message</h4>
              <div className="p-3 bg-gray-50 rounded-lg">
                {currentResponse.data?.message || 'No message'}
              </div>
            </div>

            {currentResponse.data?.actionsExecuted && 
             currentResponse.data.actionsExecuted.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Actions Executed</h4>
                <div className="space-y-2">
                  {currentResponse.data.actionsExecuted.map((action, index) => (
                    <div key={index} className="p-3 bg-blue-50 rounded-lg">
                      <div className="font-medium text-blue-900">
                        {action.type}
                      </div>
                      <div className="text-sm text-blue-700 mt-1">
                        {JSON.stringify(action.details, null, 2)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'raw' && (
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Raw Response</h4>
            <pre className="p-3 bg-gray-50 rounded-lg text-sm overflow-auto max-h-96">
              {JSON.stringify(currentResponse, null, 2)}
            </pre>
          </div>
        )}

        {activeTab === 'actions' && (
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Action Analysis</h4>
            <div className="space-y-3">
              {currentTest?.logs?.map((log, index) => (
                <div key={index} className="p-3 bg-yellow-50 rounded-lg">
                  <div className="font-medium text-yellow-900">
                    {log.component} - {log.level}
                  </div>
                  <div className="text-sm text-yellow-700 mt-1">
                    {log.message}
                  </div>
                  <div className="text-xs text-yellow-600 mt-1">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### **5. Debug Panel Component**
```tsx
// components/DebugPanel.tsx
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useTestStore } from '@/store/testStore';

export function DebugPanel() {
  const { currentTest, debugLogs, clearDebugLogs } = useTestStore();
  const [filter, setFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all');

  const filteredLogs = debugLogs.filter(log => 
    filter === 'all' || log.level.toLowerCase() === filter
  );

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
    const logsContainer = document.getElementById('debug-logs');
    if (logsContainer) {
      logsContainer.scrollTop = logsContainer.scrollHeight;
    }
  }, [debugLogs]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Debug Logs
          <div className="flex items-center space-x-2">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="px-2 py-1 text-sm border border-gray-300 rounded"
            >
              <option value="all">All</option>
              <option value="error">Errors</option>
              <option value="warning">Warnings</option>
              <option value="info">Info</option>
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={clearDebugLogs}
            >
              Clear
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div 
          id="debug-logs"
          className="h-96 overflow-y-auto space-y-2 font-mono text-sm"
        >
          {filteredLogs.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No debug logs available
            </div>
          ) : (
            filteredLogs.map((log, index) => (
              <div
                key={index}
                className={`p-2 rounded border-l-4 ${
                  log.level === 'ERROR' ? 'bg-red-50 border-red-500 text-red-900' :
                  log.level === 'WARNING' ? 'bg-yellow-50 border-yellow-500 text-yellow-900' :
                  log.level === 'INFO' ? 'bg-blue-50 border-blue-500 text-blue-900' :
                  'bg-gray-50 border-gray-500 text-gray-900'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="text-xs">
                        {log.component}
                      </Badge>
                      <span className="font-medium">
                        {log.level}
                      </span>
                      <span className="text-gray-500">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="mt-1 text-xs">
                      {log.message}
                    </div>
                    {log.data && (
                      <details className="mt-1">
                        <summary className="cursor-pointer text-xs underline">
                          Details
                        </summary>
                        <pre className="mt-1 text-xs bg-white p-2 rounded border">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

### **6. Scenario Switcher Component**
```tsx
// components/ScenarioSwitcher.tsx
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTestStore } from '@/store/testStore';
import { TestScenario, testScenarios } from '@/lib/scenarios';

export function ScenarioSwitcher() {
  const { 
    currentScenario, 
    setCurrentScenario, 
    loadScenario,
    runScenario 
  } = useTestStore();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Test Scenarios</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {testScenarios.map((scenario) => (
            <div
              key={scenario.id}
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                currentScenario?.id === scenario.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => setCurrentScenario(scenario)}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-medium text-gray-900">
                  {scenario.name}
                </h3>
                <Badge variant="outline" className="text-xs">
                  {scenario.category}
                </Badge>
              </div>
              
              <p className="text-sm text-gray-600 mb-3">
                {scenario.description}
              </p>
              
              <div className="space-y-2">
                <div className="text-xs text-gray-500">
                  <strong>Expected:</strong> {scenario.expectedResult}
                </div>
                
                {scenario.preconditions && (
                  <div className="text-xs text-gray-500">
                    <strong>Preconditions:</strong> {scenario.preconditions}
                  </div>
                )}
              </div>
              
              <div className="flex space-x-2 mt-3">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => loadScenario(scenario)}
                  disabled={currentScenario?.id === scenario.id}
                >
                  Load
                </Button>
                <Button
                  size="sm"
                  onClick={() => runScenario(scenario)}
                >
                  Run
                </Button>
              </div>
            </div>
          ))}
        </div>
        
        {/* Custom Scenario */}
        <div className="mt-6 p-4 border-2 border-dashed border-gray-300 rounded-lg">
          <h3 className="font-medium text-gray-900 mb-2">
            Custom Test
          </h3>
          <p className="text-sm text-gray-600 mb-3">
            Create your own test scenario with custom parameters
          </p>
          <Button
            variant="outline"
            onClick={() => {
              // Reset to custom scenario
              setCurrentScenario(null);
            }}
          >
            Create Custom Test
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### **7. Test Scenarios Configuration**
```typescript
// lib/scenarios.ts
export interface TestScenario {
  id: string;
  name: string;
  description: string;
  category: 'stock' | 'price' | 'status' | 'confirmation' | 'error';
  expectedRequest: {
    message: string;
    inputType: 'text' | 'audio';
    context: Record<string, any>;
    selectedProductIds: string[];
  };
  expectedResult: string;
  preconditions?: string;
  timeout?: number;
}

export const testScenarios: TestScenario[] = [
  {
    id: 'stock-monitoring-all',
    name: 'Stock Monitoring - All Products',
    description: 'Enable stock monitoring for all products with threshold 5',
    category: 'stock',
    expectedRequest: {
      message: 'Enable quantity monitoring for all products with threshold 5',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: []
      },
      selectedProductIds: []
    },
    expectedResult: 'Confirmation request for bulk operation on all products',
    preconditions: 'Products exist in the system'
  },
  {
    id: 'stock-monitoring-selected',
    name: 'Stock Monitoring - Selected Products',
    description: 'Enable stock monitoring for specific products with threshold 3',
    category: 'stock',
    expectedRequest: {
      message: 'Enable quantity monitoring for selected products with threshold 3',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: ['7626ff3a-1234-5678-9abc-123456789abc']
      },
      selectedProductIds: ['7626ff3a-1234-5678-9abc-123456789abc']
    },
    expectedResult: 'Stock monitoring enabled for specific products',
    preconditions: 'Selected products exist in the system'
  },
  {
    id: 'price-monitoring-all',
    name: 'Price Monitoring - All Products',
    description: 'Enable price monitoring for all products with 15% margin',
    category: 'price',
    expectedRequest: {
      message: 'Enable price monitoring for all products with margin 15%',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: []
      },
      selectedProductIds: []
    },
    expectedResult: 'Confirmation request for bulk price monitoring',
    preconditions: 'Products exist in the system'
  },
  {
    id: 'product-status',
    name: 'Product Status Query',
    description: 'Get current status of products',
    category: 'status',
    expectedRequest: {
      message: 'What is the status of my products?',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: ['7626ff3a-1234-5678-9abc-123456789abc']
      },
      selectedProductIds: ['7626ff3a-1234-5678-9abc-123456789abc']
    },
    expectedResult: 'Product status information returned',
    preconditions: 'Products exist in the system'
  },
  {
    id: 'confirmation-yes',
    name: 'Confirmation - Yes Response',
    description: 'Test confirmation flow with positive response',
    category: 'confirmation',
    expectedRequest: {
      message: 'Yes, please proceed with the stock monitoring',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: []
      },
      selectedProductIds: []
    },
    expectedResult: 'Bulk stock monitoring executed',
    preconditions: 'Pending confirmation exists in session'
  },
  {
    id: 'confirmation-no',
    name: 'Confirmation - No Response',
    description: 'Test confirmation flow with negative response',
    category: 'confirmation',
    expectedRequest: {
      message: 'No, cancel that operation',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: []
      },
      selectedProductIds: []
    },
    expectedResult: 'Operation cancelled',
    preconditions: 'Pending confirmation exists in session'
  },
  {
    id: 'error-invalid-product',
    name: 'Error - Invalid Product',
    description: 'Test error handling with invalid product ID',
    category: 'error',
    expectedRequest: {
      message: 'Enable monitoring for invalid-product-123',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: ['invalid-product-123']
      },
      selectedProductIds: ['invalid-product-123']
    },
    expectedResult: 'Product not found error',
    preconditions: 'Invalid product ID provided'
  },
  {
    id: 'error-empty-message',
    name: 'Error - Empty Message',
    description: 'Test error handling with empty message',
    category: 'error',
    expectedRequest: {
      message: '',
      inputType: 'text',
      context: {
        user_id: 'test-user-123',
        tenant_id: 'test-tenant-456',
        connector_id: 'test-connector-123',
        selected_product_ids: []
      },
      selectedProductIds: []
    },
    expectedResult: 'Empty message validation error',
    preconditions: 'Empty user message'
  }
];
```

### **8. State Management Store**
```typescript
// store/testStore.ts
import { create } from 'zustand';
import { TestScenario } from '@/lib/scenarios';

interface TestRequest {
  sessionId: string;
  inputType: 'text' | 'audio';
  message: string;
  context: Record<string, any>;
  selectedProductIds: string[];
}

interface TestResponse {
  success: boolean;
  data?: any;
  error?: string;
  timestamp: number;
  responseTime: number;
}

interface PerformanceMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  errorRate: number;
}

interface DebugLog {
  timestamp: number;
  level: 'INFO' | 'WARNING' | 'ERROR';
  component: string;
  message: string;
  data?: any;
}

interface TestState {
  // Current test state
  isTestRunning: boolean;
  currentRequest: TestRequest;
  currentResponse: TestResponse | null;
  currentScenario: TestScenario | null;
  currentTest: {
    id: string;
    startTime: number;
    logs: DebugLog[];
  } | null;

  // Performance metrics
  performanceMetrics: PerformanceMetrics;

  // Debug logs
  debugLogs: DebugLog[];

  // Actions
  setCurrentRequest: (request: TestRequest) => void;
  setCurrentResponse: (response: TestResponse | null) => void;
  setCurrentScenario: (scenario: TestScenario | null) => void;
  sendRequest: (request?: TestRequest) => Promise<void>;
  loadScenario: (scenario: TestScenario) => void;
  runScenario: (scenario: TestScenario) => Promise<void>;
  resetTest: () => void;
  clearDebugLogs: () => void;
  addDebugLog: (log: DebugLog) => void;
  updatePerformanceMetrics: (response: TestResponse) => void;
}

export const useTestStore = create<TestState>((set, get) => ({
  // Initial state
  isTestRunning: false,
  currentRequest: {
    sessionId: 'test-session-123',
    inputType: 'text',
    message: '',
    context: {
      user_id: 'test-user-123',
      tenant_id: 'test-tenant-456',
      connector_id: 'test-connector-123',
      selected_product_ids: []
    },
    selectedProductIds: []
  },
  currentResponse: null,
  currentScenario: null,
  currentTest: null,
  performanceMetrics: {
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    averageResponseTime: 0,
    errorRate: 0
  },
  debugLogs: [],

  // Actions
  setCurrentRequest: (request) => set({ currentRequest: request }),
  
  setCurrentResponse: (response) => set({ currentResponse: response }),
  
  setCurrentScenario: (scenario) => set({ currentScenario: scenario }),

  sendRequest: async (request) => {
    const state = get();
    const testRequest = request || state.currentRequest;
    
    set({ isTestRunning: true });
    
    const startTime = Date.now();
    const testId = `test-${startTime}`;
    
    set({
      currentTest: {
        id: testId,
        startTime,
        logs: []
      }
    });

    try {
      // Add debug log
      state.addDebugLog({
        timestamp: Date.now(),
        level: 'INFO',
        component: 'CLIENT',
        message: `Sending request: ${testRequest.message}`,
        data: testRequest
      });

      // Make API call
      const response = await fetch('/api/storedesk/assist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': testRequest.sessionId
        },
        body: JSON.stringify({
          sessionId: testRequest.sessionId,
          inputType: testRequest.inputType,
          message: testRequest.message,
          context: testRequest.context
        })
      });

      const responseData = await response.json();
      const endTime = Date.now();
      const responseTime = endTime - startTime;

      const testResponse: TestResponse = {
        success: response.ok,
        data: responseData,
        timestamp: endTime,
        responseTime
      };

      // Update state
      set({
        currentResponse: testResponse,
        isTestRunning: false
      });

      // Update performance metrics
      state.updatePerformanceMetrics(testResponse);

      // Add debug log
      state.addDebugLog({
        timestamp: endTime,
        level: response.ok ? 'INFO' : 'ERROR',
        component: 'CLIENT',
        message: `Response received: ${response.ok ? 'Success' : 'Failed'} (${responseTime}ms)`,
        data: testResponse
      });

    } catch (error) {
      const endTime = Date.now();
      const responseTime = endTime - startTime;

      const testResponse: TestResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: endTime,
        responseTime
      };

      set({
        currentResponse: testResponse,
        isTestRunning: false
      });

      state.updatePerformanceMetrics(testResponse);

      state.addDebugLog({
        timestamp: endTime,
        level: 'ERROR',
        component: 'CLIENT',
        message: `Request failed: ${testResponse.error}`,
        data: testResponse
      });
    }
  },

  loadScenario: (scenario) => {
    set({
      currentRequest: scenario.expectedRequest,
      currentScenario: scenario
    });
  },

  runScenario: async (scenario) => {
    const state = get();
    await state.loadScenario(scenario);
    await state.sendRequest();
  },

  resetTest: () => set({
    isTestRunning: false,
    currentResponse: null,
    currentTest: null,
    debugLogs: []
  }),

  clearDebugLogs: () => set({ debugLogs: [] }),

  addDebugLog: (log) => set((state) => ({
    debugLogs: [...state.debugLogs, log]
  })),

  updatePerformanceMetrics: (response) => set((state) => {
    const newMetrics = {
      totalRequests: state.performanceMetrics.totalRequests + 1,
      successfulRequests: state.performanceMetrics.successfulRequests + (response.success ? 1 : 0),
      failedRequests: state.performanceMetrics.failedRequests + (response.success ? 0 : 1),
      averageResponseTime: 0,
      errorRate: 0
    };

    // Calculate new average
    const totalTime = state.performanceMetrics.averageResponseTime * state.performanceMetrics.totalRequests + response.responseTime;
    newMetrics.averageResponseTime = totalTime / newMetrics.totalRequests;

    // Calculate error rate
    newMetrics.errorRate = (newMetrics.failedRequests / newMetrics.totalRequests) * 100;

    return {
      performanceMetrics: newMetrics
    };
  })
}));
```

---

## 🚀 **DEPLOYMENT & CONFIGURATION**

### **Next.js Configuration**
```typescript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/storedesk/assist',
        destination: 'http://localhost:8000/api/storedesk/assist',
      },
      {
        source: '/api/debug/session/:sessionId',
        destination: 'http://localhost:8000/api/debug/session/:sessionId',
      },
      {
        source: '/api/debug/providers',
        destination: 'http://localhost:8000/api/debug/providers',
      }
    ];
  },
};

module.exports = nextConfig;
```

### **Tailwind Configuration**
```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

---

## 📊 **FEATURES & CAPABILITIES**

### **✅ Implemented Features**
1. **Comprehensive Testing Interface**
   - Request configuration with all parameters
   - Response analysis with multiple views
   - Real-time debug logging

2. **Scenario Testing**
   - Pre-built test scenarios
   - Custom test creation
   - One-click scenario execution

3. **Performance Monitoring**
   - Response time tracking
   - Success/error rate metrics
   - Visual performance dashboard

4. **Debug Capabilities**
   - Component-level logging
   - Request/response inspection
   - Error analysis

5. **User Experience**
   - Responsive design
   - Interactive components
   - Real-time updates

### **🔧 Technical Features**
- **Next.js 14 with App Router**
- **TypeScript for type safety**
- **Tailwind CSS for styling**
- **Zustand for state management**
- **Component-based architecture**
- **API proxy configuration**

---

## 🎯 **USAGE INSTRUCTIONS**

### **Development Setup**
```bash
# Install dependencies
cd storedesk-test
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### **Testing Workflow**
1. **Select Scenario**: Choose from pre-built scenarios or create custom
2. **Configure Request**: Adjust parameters as needed
3. **Send Request**: Click send to execute test
4. **Analyze Response**: Review results in multiple views
5. **Monitor Performance**: Track metrics over time
6. **Debug Issues**: Use debug logs for troubleshooting

---

## 📝 **DEVELOPMENT GUIDELINES**

### **Adding New Scenarios**
```typescript
// Add to lib/scenarios.ts
const newScenario: TestScenario = {
  id: 'custom-test',
  name: 'Custom Test',
  description: 'Description of test',
  category: 'stock',
  expectedRequest: { /* request data */ },
  expectedResult: 'Expected outcome'
};
```

### **Adding New Debug Components**
```typescript
// Create new component in components/
// Add to main page layout
// Use useTestStore for state management
```

---

**🎉 NextJS Test Page provides comprehensive testing interface for StoreDesk AI service with real-time debugging, scenario testing, and performance monitoring!**
